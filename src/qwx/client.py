"""同步与异步的基础客户端。

Client 与 AsyncClient 共享配置、URL 拼装、缓存读写与 TTL 解析，只有传输
层不同：端点族的方法体只写一份，结果类型与 Go 版一一对应。

同步客户端拿到模型，异步客户端拿到协程 —— 调用方 await 即可。
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError

from qwx.auth import Auth
from qwx.cache import Cache
from qwx.errors import (
    InvalidConfigError,
    InvalidResponseError,
    UpstreamUnavailableError,
    upstream_error,
)
from qwx.logger import (
    LOG_FIELD_ATTEMPT,
    LOG_FIELD_CACHE_KEY,
    LOG_FIELD_DURATION_MS,
    LOG_FIELD_ENDPOINT,
    LOG_FIELD_ERROR,
    LOG_FIELD_METHOD,
    LOG_FIELD_PATH,
    LOG_FIELD_STATUS,
    LOG_FIELD_UPSTREAM_CODE,
    LOG_FIELD_UPSTREAM_TITLE,
    Logger,
    sanitize_error_text,
)
from qwx.request import Request
from qwx.ttl import TTLPolicy, current_ttl_override, override_ttl

__all__ = [
    "DEFAULT_TIMEOUT",
    "MAX_RETRY",
    "MAX_RETRY_DELAY",
    "AsyncClient",
    "Client",
    "next_retry_delay",
    "normalize_api_host",
    "parse_retry_after",
]

DEFAULT_TIMEOUT = 30.0
"""HTTP 请求的默认超时（秒）。"""

MAX_RETRY = 3
"""最大重试次数：首次请求之外最多再试 3 次。"""

MAX_RETRY_DELAY = 30.0
"""单次重试等待的上限（秒）。

上游的 Retry-After 可能给出很大的值。客户端不是队列服务，不该在一次
请求里睡一小时：超过上限就按上限等，重试次数本身也有上限。
"""

_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")


def normalize_api_host(raw: str) -> str:
    """规整控制台分配的 API Host。

    只给 host 时补 https://，带 scheme 时原样保留 scheme，去掉尾部斜杠、
    查询串与片段。Host 本身不校验是不是 qweatherapi.com —— 网关、自建
    代理、测试用假上游都要能用。
    """
    text = raw.strip()
    if not text:
        raise InvalidConfigError("qwx: api host is required (控制台设置页的专属 API Host)")
    if "://" not in text:
        text = "https://" + text
    scheme, _, rest = text.partition("://")
    if not scheme or not _SCHEME_RE.match(scheme):
        raise InvalidConfigError(f"qwx: invalid api host {raw!r}: bad scheme")
    rest = rest.split("#", 1)[0].split("?", 1)[0]
    if not rest or any(ch.isspace() for ch in rest):
        raise InvalidConfigError(f"qwx: invalid api host {raw!r}: missing host")
    host, _, path = rest.partition("/")
    path = path.rstrip("/")
    if path:
        return f"{scheme}://{host}/{path}"
    return f"{scheme}://{host}"


def parse_retry_after(value: str, now: datetime) -> float | None:
    """解析 Retry-After 头，返回要等的秒数。

    格式一：秒数。格式二：HTTP 日期。解析不出来或为负数时返回 None。
    """
    text = value.strip()
    if not text:
        return None
    try:
        seconds = int(text)
    except ValueError:
        pass
    else:
        if seconds < 0:
            return None
        return float(seconds)
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = (when - now).total_seconds()
    if delta < 0:
        # 时间已过，可以立即重试。
        delta = 0.0
    return delta


def next_retry_delay(attempt: int, retry_after: str, now: datetime) -> float:
    """下一次重试要等多久（秒）。

    退避是 attempt 秒；上游给了 Retry-After 且更大就听上游的。等待不超过
    MAX_RETRY_DELAY。
    """
    delay = float(attempt)
    parsed = parse_retry_after(retry_after, now)
    if parsed is not None and parsed > delay:
        delay = parsed
    if delay > MAX_RETRY_DELAY:
        delay = MAX_RETRY_DELAY
    return delay


class _ClientBase:
    """Client 与 AsyncClient 共享的配置与逻辑。"""

    def __init__(
        self,
        auth: Auth | None,
        api_host: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        cache: Cache | None = None,
        ttl_policy: TTLPolicy | None = None,
        logger: logging.Logger | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if auth is None:
            raise InvalidConfigError("qwx: auth is required")
        self._auth = auth
        self._api_host = normalize_api_host(api_host)
        self._timeout = timeout
        self._cache = cache
        self._ttl_policy = ttl_policy
        self._logger = Logger(logger)
        self._clock = clock if clock is not None else (lambda: datetime.now(timezone.utc))

    @property
    def api_host(self) -> str:
        """规整后的 API Host。"""
        return self._api_host

    def override_ttl(self, ttl: timedelta) -> AbstractContextManager[None]:
        """单次缓存时长覆盖，作用于 with 块内的所有请求。

        覆盖优先级高于 TTLPolicy 与端点内置的默认时长。ttl <= 0 表示这一次
        不读也不写缓存。

            with client.override_ttl(timedelta(seconds=30)):
                weather.current(loc)
        """
        return override_ttl(ttl)

    def _resolve_ttl(self, request: Request) -> timedelta:
        """决定本次请求的缓存时长。

        优先级：单次覆盖 > TTLPolicy > 端点内置的默认时长。返回值 <= 0 表示
        本次不缓存。endpoint 为空表示该请求不参与策略匹配，策略不会被调用。
        """
        override = current_ttl_override()
        if override is not None:
            return override
        if self._ttl_policy is None or not request.endpoint:
            return request.ttl
        return self._ttl_policy.ttl(request.endpoint, request.ttl)

    def _build_url(self, request: Request) -> str:
        """拼出完整 URL。查询参数按键排序，与 Go 版 url.Values.Encode 一致。"""
        url = self._api_host + request.path
        if request.query:
            url += "?" + urlencode(sorted(request.query.items()))
        return url

    def _base_fields(self, request: Request) -> dict[str, Any]:
        """每条日志都带的公共字段。"""
        fields: dict[str, Any] = {}
        if request.endpoint:
            fields[LOG_FIELD_ENDPOINT] = str(request.endpoint)
        if request.path:
            fields[LOG_FIELD_PATH] = request.path
        return fields

    def _decode(self, request: Request, payload: bytes) -> Any:
        """把响应体解析到 request.out 指定的模型。out 为空时返回原始字节。"""
        out = request.out
        if out is None:
            return payload
        try:
            return out.model_validate_json(payload)
        except ValidationError as exc:
            self._logger.log(
                logging.ERROR,
                "decode response failed",
                {**self._base_fields(request), LOG_FIELD_ERROR: sanitize_error_text(exc)},
            )
            raise InvalidResponseError(f"qwx: decode response: {exc}") from exc


class Client(_ClientBase):
    """和风天气 API 的同步基础客户端。

    负责认证、请求发送、缓存读写与错误归类，不含具体接口。无状态，可并发
    共享。

    接口族在各自的子包里，用同一个 Client 构造服务客户端。
    """

    def __init__(
        self,
        auth: Auth | None,
        api_host: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        cache: Cache | None = None,
        ttl_policy: TTLPolicy | None = None,
        logger: logging.Logger | None = None,
        http_client: httpx.Client | None = None,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """构造 Client。

        auth 与 api_host 必填：api_host 是控制台「设置」页分配的专属 API
        Host，没有默认值。

        cache 可为 None。注入的 http_client 不会被改超时，如需超时请自行
        设置。sleep 是退避等待的注入点，供测试断言重试行为。
        """
        super().__init__(
            auth,
            api_host,
            timeout=timeout,
            cache=cache,
            ttl_policy=ttl_policy,
            logger=logger,
            clock=clock,
        )
        self._http = http_client if http_client is not None else httpx.Client(timeout=timeout)
        self._sleep = sleep if sleep is not None else time.sleep

    def close(self) -> None:
        """关闭底层 HTTP 连接。"""
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def do(self, request: Request) -> Any:
        """发送一次上游请求并把响应解析到 request.out 指定的模型。

        命中缓存时直接返回缓存内容，不打上游。上游返回非 2xx 时，按状态码
        归类到具体的异常，并尽可能解析出上游的错误细节。
        """
        ttl = self._resolve_ttl(request)
        cache = self._cache
        use_cache = cache is not None and bool(request.cache_key) and ttl > timedelta(0)
        if use_cache and cache is not None:
            try:
                hit = cache.get(request.cache_key)
            except Exception as exc:  # 缓存故障降级为直连上游
                self._logger.log(
                    logging.WARNING,
                    "cache read failed",
                    {
                        **self._base_fields(request),
                        LOG_FIELD_CACHE_KEY: request.cache_key,
                        LOG_FIELD_ERROR: sanitize_error_text(exc),
                    },
                )
            else:
                if hit is not None:
                    self._logger.log(
                        logging.DEBUG,
                        "cache hit",
                        {**self._base_fields(request), LOG_FIELD_CACHE_KEY: request.cache_key},
                    )
                    return self._decode(request, hit)
                self._logger.log(
                    logging.DEBUG,
                    "cache miss",
                    {**self._base_fields(request), LOG_FIELD_CACHE_KEY: request.cache_key},
                )

        payload = self._fetch(request)

        if use_cache and cache is not None:
            try:
                cache.set(request.cache_key, payload, ttl)
            except Exception as exc:  # 缓存故障不影响已拿到的响应
                self._logger.log(
                    logging.WARNING,
                    "cache write failed",
                    {
                        **self._base_fields(request),
                        LOG_FIELD_CACHE_KEY: request.cache_key,
                        LOG_FIELD_ERROR: sanitize_error_text(exc),
                    },
                )

        return self._decode(request, payload)

    def _fetch(self, request: Request) -> bytes:
        """发起一次真实的上游请求，返回原始响应体。"""
        url = self._build_url(request)
        headers: dict[str, str] = {}
        try:
            self._auth.apply(headers)
        except Exception as exc:
            self._logger.log(
                logging.ERROR,
                "sign request failed",
                {**self._base_fields(request), LOG_FIELD_ERROR: sanitize_error_text(exc)},
            )
            raise

        started = time.monotonic()
        response = self._send(request, url, headers)
        duration_ms = int((time.monotonic() - started) * 1000)
        body = response.content

        if response.status_code < 200 or response.status_code >= 300:
            error = upstream_error(response.status_code, body)
            level = logging.ERROR if response.status_code >= 500 else logging.WARNING
            fields: dict[str, Any] = {
                **self._base_fields(request),
                LOG_FIELD_METHOD: request.method or "GET",
                LOG_FIELD_STATUS: response.status_code,
                LOG_FIELD_DURATION_MS: duration_ms,
            }
            if error.code:
                fields[LOG_FIELD_UPSTREAM_CODE] = error.code
            if error.title:
                fields[LOG_FIELD_UPSTREAM_TITLE] = error.title
            self._logger.log(level, "upstream rejected", fields)
            raise error

        self._logger.log(
            logging.INFO,
            "upstream request",
            {
                **self._base_fields(request),
                LOG_FIELD_METHOD: request.method or "GET",
                LOG_FIELD_STATUS: response.status_code,
                LOG_FIELD_DURATION_MS: duration_ms,
            },
        )
        return body

    def _send(self, request: Request, url: str, headers: dict[str, str]) -> httpx.Response:
        """带退避地重试上游请求。

        重试由上游 5xx、429 或网络错误触发，每次重试前记一条日志。返回的
        响应可能是 4xx 与 5xx，状态码归类交给调用方。
        """
        method = request.method or "GET"
        response: httpx.Response | None = None
        last_error: Exception | None = None

        for attempt in range(MAX_RETRY + 1):
            try:
                response = self._http.request(method, url, headers=headers)
            except httpx.HTTPError as exc:
                last_error = exc
                response = None
            else:
                if response.status_code < 500 and response.status_code != 429:
                    return response

            if attempt == MAX_RETRY:
                break

            retry_after = response.headers.get("Retry-After", "") if response is not None else ""
            delay = next_retry_delay(attempt + 1, retry_after, self._clock())
            self._logger.log(
                logging.WARNING,
                "upstream retry",
                {
                    **self._base_fields(request),
                    LOG_FIELD_ATTEMPT: attempt + 1,
                    LOG_FIELD_STATUS: response.status_code if response is not None else 0,
                    LOG_FIELD_ERROR: sanitize_error_text(last_error),
                },
            )
            self._sleep(delay)

        if response is None:
            raise UpstreamUnavailableError(message=f"qwx: upstream unavailable: {last_error}")
        return response


class AsyncClient(_ClientBase):
    """和风天气 API 的异步基础客户端。

    与 Client 语义对等，只是传输层是异步的：do 是协程，调用方 await 后
    拿到与同步版同样的模型。
    """

    def __init__(
        self,
        auth: Auth | None,
        api_host: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        cache: Cache | None = None,
        ttl_policy: TTLPolicy | None = None,
        logger: logging.Logger | None = None,
        http_client: httpx.AsyncClient | None = None,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Any] | None = None,
    ) -> None:
        """构造 AsyncClient。参数含义与 Client 相同。"""
        super().__init__(
            auth,
            api_host,
            timeout=timeout,
            cache=cache,
            ttl_policy=ttl_policy,
            logger=logger,
            clock=clock,
        )
        self._http = http_client if http_client is not None else httpx.AsyncClient(timeout=timeout)
        self._sleep = sleep if sleep is not None else asyncio.sleep

    async def aclose(self) -> None:
        """关闭底层 HTTP 连接。"""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def do(self, request: Request) -> Any:
        """发送一次上游请求并把响应解析到 request.out 指定的模型。"""
        ttl = self._resolve_ttl(request)
        cache = self._cache
        use_cache = cache is not None and bool(request.cache_key) and ttl > timedelta(0)
        if use_cache and cache is not None:
            try:
                hit = cache.get(request.cache_key)
            except Exception as exc:  # 缓存故障降级为直连上游
                self._logger.log(
                    logging.WARNING,
                    "cache read failed",
                    {
                        **self._base_fields(request),
                        LOG_FIELD_CACHE_KEY: request.cache_key,
                        LOG_FIELD_ERROR: sanitize_error_text(exc),
                    },
                )
            else:
                if hit is not None:
                    self._logger.log(
                        logging.DEBUG,
                        "cache hit",
                        {**self._base_fields(request), LOG_FIELD_CACHE_KEY: request.cache_key},
                    )
                    return self._decode(request, hit)
                self._logger.log(
                    logging.DEBUG,
                    "cache miss",
                    {**self._base_fields(request), LOG_FIELD_CACHE_KEY: request.cache_key},
                )

        payload = await self._fetch(request)

        if use_cache and cache is not None:
            try:
                cache.set(request.cache_key, payload, ttl)
            except Exception as exc:  # 缓存故障不影响已拿到的响应
                self._logger.log(
                    logging.WARNING,
                    "cache write failed",
                    {
                        **self._base_fields(request),
                        LOG_FIELD_CACHE_KEY: request.cache_key,
                        LOG_FIELD_ERROR: sanitize_error_text(exc),
                    },
                )

        return self._decode(request, payload)

    async def _fetch(self, request: Request) -> bytes:
        """发起一次真实的上游请求，返回原始响应体。"""
        url = self._build_url(request)
        headers: dict[str, str] = {}
        try:
            self._auth.apply(headers)
        except Exception as exc:
            self._logger.log(
                logging.ERROR,
                "sign request failed",
                {**self._base_fields(request), LOG_FIELD_ERROR: sanitize_error_text(exc)},
            )
            raise

        started = time.monotonic()
        response = await self._send(request, url, headers)
        duration_ms = int((time.monotonic() - started) * 1000)
        body = response.content

        if response.status_code < 200 or response.status_code >= 300:
            error = upstream_error(response.status_code, body)
            level = logging.ERROR if response.status_code >= 500 else logging.WARNING
            fields: dict[str, Any] = {
                **self._base_fields(request),
                LOG_FIELD_METHOD: request.method or "GET",
                LOG_FIELD_STATUS: response.status_code,
                LOG_FIELD_DURATION_MS: duration_ms,
            }
            if error.code:
                fields[LOG_FIELD_UPSTREAM_CODE] = error.code
            if error.title:
                fields[LOG_FIELD_UPSTREAM_TITLE] = error.title
            self._logger.log(level, "upstream rejected", fields)
            raise error

        self._logger.log(
            logging.INFO,
            "upstream request",
            {
                **self._base_fields(request),
                LOG_FIELD_METHOD: request.method or "GET",
                LOG_FIELD_STATUS: response.status_code,
                LOG_FIELD_DURATION_MS: duration_ms,
            },
        )
        return body

    async def _send(self, request: Request, url: str, headers: dict[str, str]) -> httpx.Response:
        """带退避地重试上游请求，语义与同步版一致。"""
        method = request.method or "GET"
        response: httpx.Response | None = None
        last_error: Exception | None = None

        for attempt in range(MAX_RETRY + 1):
            try:
                response = await self._http.request(method, url, headers=headers)
            except httpx.HTTPError as exc:
                last_error = exc
                response = None
            else:
                if response.status_code < 500 and response.status_code != 429:
                    return response

            if attempt == MAX_RETRY:
                break

            retry_after = response.headers.get("Retry-After", "") if response is not None else ""
            delay = next_retry_delay(attempt + 1, retry_after, self._clock())
            self._logger.log(
                logging.WARNING,
                "upstream retry",
                {
                    **self._base_fields(request),
                    LOG_FIELD_ATTEMPT: attempt + 1,
                    LOG_FIELD_STATUS: response.status_code if response is not None else 0,
                    LOG_FIELD_ERROR: sanitize_error_text(last_error),
                },
            )
            await self._sleep(delay)

        if response is None:
            raise UpstreamUnavailableError(message=f"qwx: upstream unavailable: {last_error}")
        return response
