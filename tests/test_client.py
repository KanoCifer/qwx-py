"""同步与异步客户端。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from pydantic import Field

from qwx import APIKeyAuth, JWTAuth
from qwx._models import QwxModel
from qwx.cache import MemoryCache
from qwx.client import (
    AsyncClient,
    Client,
    next_retry_delay,
    normalize_api_host,
    parse_retry_after,
)
from qwx.errors import (
    InvalidConfigError,
    InvalidResponseError,
    QuotaExceededError,
    UnauthorizedError,
    UpstreamRejectedError,
    UpstreamUnavailableError,
)
from qwx.request import Request
from qwx.ttl import Endpoint, TTLMap


class Echo(QwxModel):
    """测试用的响应模型。"""

    code: str = ""
    locations: list[str] = Field(default_factory=list)


class RecordingCache:
    """记录读写的缓存替身。"""

    def __init__(self) -> None:
        self.gets: list[str] = []
        self.sets: list[tuple[str, bytes, timedelta]] = []
        self.data: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        self.gets.append(key)
        return self.data.get(key)

    def set(self, key: str, data: bytes, ttl: timedelta) -> None:
        self.sets.append((key, data, ttl))
        self.data[key] = data


class FailingCache:
    """总是失败的缓存替身。"""

    def get(self, key: str) -> bytes | None:
        raise RuntimeError("cache broken")

    def set(self, key: str, data: bytes, ttl: timedelta) -> None:
        raise RuntimeError("cache broken")


def make_client(handler: Any, **kwargs: Any) -> Client:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    kwargs.setdefault("sleep", lambda _delay: None)
    return Client(APIKeyAuth("k"), "https://example.test", http_client=http, **kwargs)


def make_async_client(handler: Any, **kwargs: Any) -> AsyncClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    kwargs.setdefault("sleep", lambda _delay: asyncio.sleep(0))
    return AsyncClient(APIKeyAuth("k"), "https://example.test", http_client=http, **kwargs)


def test_do_decodes_response() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"code": "200", "locations": []})

    client = make_client(handler)
    out = client.do(Request(path="/geo/v2/city/lookup", out=Echo))
    assert isinstance(out, Echo)
    assert out.code == "200"
    assert seen[0].url.path == "/geo/v2/city/lookup"


def test_do_returns_raw_bytes_without_a_model() -> None:
    client = make_client(lambda request: httpx.Response(200, json={"code": "200"}))
    payload = client.do(Request(path="/x"))
    assert isinstance(payload, bytes)
    assert json.loads(payload) == {"code": "200"}


def test_do_caches_response() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler, cache=MemoryCache())
    request = Request(
        path="/geo/v2/city/top",
        cache_key="qwx:geo:topcity",
        ttl=timedelta(minutes=1),
        out=Echo,
    )
    for _ in range(2):
        out = client.do(request)
        assert isinstance(out, Echo)
        assert out.code == "200"
    assert len(calls) == 1


def test_cache_key_isolates_results() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler, cache=MemoryCache())
    client.do(Request(path="/x", cache_key="k1", ttl=timedelta(minutes=1)))
    client.do(Request(path="/x", cache_key="k2", ttl=timedelta(minutes=1)))
    assert len(calls) == 2


def test_cache_failure_degrades_gracefully() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler, cache=FailingCache())
    out = client.do(Request(path="/x", cache_key="k", ttl=timedelta(minutes=1), out=Echo))
    assert isinstance(out, Echo)
    assert len(calls) == 1


def test_cache_is_not_used_without_ttl() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler, cache=MemoryCache())
    client.do(Request(path="/x", cache_key="k"))
    client.do(Request(path="/x", cache_key="k"))
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("status", "body", "want"),
    [
        (400, '{"error":{"status":400,"title":"Invalid Parameters"}}', UpstreamRejectedError),
        (401, '{"error":{"status":401,"title":"Unauthorized"}}', UnauthorizedError),
        (403, '{"error":{"status":403,"title":"Forbidden"}}', UnauthorizedError),
        (429, '{"error":{"status":429,"title":"Too Many Requests"}}', QuotaExceededError),
    ],
)
def test_upstream_errors_are_classified(status: int, body: str, want: type[Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body.encode())

    client = make_client(handler)
    with pytest.raises(want) as info:
        client.do(Request(path="/x"))
    assert info.value.status_code == status
    assert info.value.title


def test_invalid_json_raises_invalid_response() -> None:
    client = make_client(lambda request: httpx.Response(200, content=b"not json"))
    with pytest.raises(InvalidResponseError):
        client.do(Request(path="/x", out=Echo))


def test_retries_on_500_then_succeeds() -> None:
    calls: list[httpx.Request] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(500, content=b"{}")
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler, sleep=delays.append)
    out = client.do(Request(path="/x", out=Echo))
    assert isinstance(out, Echo)
    assert len(calls) == 3
    assert delays == [1.0, 2.0]


def test_retry_gives_up_after_the_last_attempt() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(500, content=b"{}")

    client = make_client(handler)
    with pytest.raises(UpstreamUnavailableError):
        client.do(Request(path="/x"))
    # 首次请求之外最多再试 3 次。
    assert len(calls) == 4


def test_network_error_becomes_upstream_unavailable() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("boom", request=request)

    client = make_client(handler)
    with pytest.raises(UpstreamUnavailableError):
        client.do(Request(path="/x"))
    assert len(calls) == 4


def test_retry_after_header_is_respected() -> None:
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "5"}, content=b"{}")

    client = make_client(handler, sleep=delays.append)
    with pytest.raises(QuotaExceededError):
        client.do(Request(path="/x"))
    assert delays == [5.0, 5.0, 5.0]


def test_parse_retry_after() -> None:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert parse_retry_after("120", now) == 120.0
    assert parse_retry_after("", now) is None
    assert parse_retry_after("later", now) is None
    assert parse_retry_after("-5", now) is None
    assert parse_retry_after("Thu, 02 Jan 2026 03:05:35 GMT", now) == 90.0
    # 时间已过就立即重试。
    assert parse_retry_after("Thu, 02 Jan 2026 03:03:05 GMT", now) == 0.0


def test_next_retry_delay() -> None:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert next_retry_delay(1, "", now) == 1.0
    assert next_retry_delay(3, "", now) == 3.0
    assert next_retry_delay(1, "5", now) == 5.0
    # Retry-After 不会缩短退避。
    assert next_retry_delay(3, "1", now) == 3.0
    assert next_retry_delay(1, "3600", now) == 30.0
    assert next_retry_delay(2, "soon", now) == 2.0


def test_ttl_policy_overrides_the_endpoint_default() -> None:
    cache = RecordingCache()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "200"})

    policy = TTLMap({Endpoint("weather/v1/current"): timedelta(minutes=5)})
    client = make_client(handler, cache=cache, ttl_policy=policy)
    client.do(
        Request(
            path="/weather/v1/current/39.92/116.41",
            cache_key="k",
            endpoint=Endpoint("weather/v1/current"),
            ttl=timedelta(minutes=1),
        )
    )
    assert cache.sets[0][2] == timedelta(minutes=5)


def test_endpoint_without_a_name_skips_the_policy() -> None:
    class ExplodingPolicy:
        def ttl(self, endpoint: Endpoint, fallback: timedelta) -> timedelta:
            raise AssertionError("policy must not be called")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler, ttl_policy=ExplodingPolicy())
    client.do(Request(path="/x", cache_key="k", ttl=timedelta(minutes=1)))


def test_single_call_override_wins_over_the_policy() -> None:
    cache = RecordingCache()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "200"})

    policy = TTLMap({Endpoint("weather/v1/current"): timedelta(minutes=5)})
    client = make_client(handler, cache=cache, ttl_policy=policy)
    request = Request(
        path="/weather/v1/current/39.92/116.41",
        cache_key="k",
        endpoint=Endpoint("weather/v1/current"),
        ttl=timedelta(minutes=1),
    )
    with client.override_ttl(timedelta(seconds=30)):
        client.do(request)
    assert cache.sets[0][2] == timedelta(seconds=30)


def test_query_parameters_are_sorted_and_encoded() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler)
    client.do(Request(path="/x", query={"b": "2", "a": "1", "lang": "zh"}))
    assert seen[0].url.query.decode() == "a=1&b=2&lang=zh"


def test_api_key_header_is_applied() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"code": "200"})

    client = make_client(handler)
    client.do(Request(path="/x"))
    assert seen[0].headers["X-QW-Api-Key"] == "k"


def test_jwt_header_is_applied() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"code": "200"})

    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    auth = JWTAuth(private_key_pem=pem, key_id="kid", project_id="proj", developer_id="dev")
    client = Client(auth, "https://example.test", http_client=http)
    client.do(Request(path="/x"))
    assert seen[0].headers["Authorization"].startswith("Bearer ")


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("abcxyz.qweatherapi.com", "https://abcxyz.qweatherapi.com"),
        ("https://abcxyz.qweatherapi.com", "https://abcxyz.qweatherapi.com"),
        ("https://abcxyz.qweatherapi.com/", "https://abcxyz.qweatherapi.com"),
        ("abcxyz.qweatherapi.com///", "https://abcxyz.qweatherapi.com"),
        ("  abcxyz.qweatherapi.com  ", "https://abcxyz.qweatherapi.com"),
        ("http://127.0.0.1:8080", "http://127.0.0.1:8080"),
        ("https://gateway.example.com/qwx", "https://gateway.example.com/qwx"),
        ("abcxyz.qweatherapi.com?", "https://abcxyz.qweatherapi.com"),
        ("abcxyz.qweatherapi.com?x=1", "https://abcxyz.qweatherapi.com"),
        ("abcxyz.qweatherapi.com#frag", "https://abcxyz.qweatherapi.com"),
    ],
)
def test_api_host_is_normalized(raw: str, want: str) -> None:
    assert normalize_api_host(raw) == want


@pytest.mark.parametrize("raw", ["", "   ", "https://", "://abc", "https://a b.com"])
def test_malformed_api_host_is_rejected(raw: str) -> None:
    with pytest.raises(InvalidConfigError):
        normalize_api_host(raw)


def test_client_requires_auth() -> None:
    with pytest.raises(InvalidConfigError):
        Client(None, "abcxyz.qweatherapi.com")


def test_client_requires_api_host() -> None:
    with pytest.raises(InvalidConfigError):
        Client(APIKeyAuth("k"), "")


def test_async_client_decodes_and_caches() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"code": "200"})

    client = make_async_client(handler, cache=MemoryCache())
    request = Request(path="/x", cache_key="k", ttl=timedelta(minutes=1), out=Echo)

    async def run() -> tuple[Any, Any]:
        return await client.do(request), await client.do(request)

    first, second = asyncio.run(run())
    assert isinstance(first, Echo)
    assert isinstance(second, Echo)
    assert len(calls) == 1


def test_async_client_classifies_upstream_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=b'{"error":{"status":401,"title":"Unauthorized"}}')

    client = make_async_client(handler)

    async def run() -> None:
        await client.do(Request(path="/x"))

    with pytest.raises(UnauthorizedError):
        asyncio.run(run())
