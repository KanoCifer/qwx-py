"""qwx 的异常层级。

Go 版用 sentinel error 加 errors.Is 判断类别，Python 里映射成异常层级：
用 isinstance 或 except 判断类别，不去解析错误字符串。

上游错误体有两代，形态不同，都在这里解析：

- 新一代：error 是对象，含 title 与 invalidParams。
- 旧一代：error 是字符串，code 单独给。
"""

from __future__ import annotations

import json
from typing import Any

__all__ = [
    "UPSTREAM_BODY_LIMIT",
    "InvalidConfigError",
    "InvalidLocationError",
    "InvalidParameterError",
    "InvalidResponseError",
    "QuotaExceededError",
    "QwxError",
    "UnauthorizedError",
    "UpstreamError",
    "UpstreamRejectedError",
    "UpstreamUnavailableError",
    "upstream_error",
]


class QwxError(Exception):
    """所有 SDK 异常的基类。"""


class InvalidConfigError(QwxError):
    """构造参数有问题：缺认证、缺私钥、API Host 不合法。"""


class InvalidLocationError(QwxError):
    """location 参数的形态上游不认。"""


class InvalidParameterError(QwxError):
    """端点参数取值越界。"""


class InvalidResponseError(QwxError):
    """上游返回的不是合法 JSON，或结构与模型对不上。"""


UPSTREAM_BODY_LIMIT = 2048
"""记录到异常里的响应体上限（字节）。"""


class UpstreamError(QwxError):
    """上游返回错误时的具体异常。

    子类按状态码归类：4xx 是 UpstreamRejectedError，429 是
    QuotaExceededError，401 与 403 是 UnauthorizedError，5xx 是
    UpstreamUnavailableError。拿不到响应的网络错误也是
    UpstreamUnavailableError，此时 status_code 为 0。
    """

    def __init__(
        self,
        status_code: int = 0,
        code: str = "",
        title: str = "",
        invalid_params: list[str] | None = None,
        body: str = "",
        message: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.title = title
        self.invalid_params = list(invalid_params) if invalid_params else []
        self.body = body
        super().__init__(message if message is not None else self._format())

    def _format(self) -> str:
        text = "qwx: upstream error"
        if self.status_code:
            text += f" (status {self.status_code})"
        if self.title:
            text += f": {self.title}"
        if self.invalid_params:
            text += f" [invalid: {', '.join(self.invalid_params)}]"
        return text


class UpstreamRejectedError(UpstreamError):
    """上游 4xx：请求本身被判为非法，重试没有意义。"""


class QuotaExceededError(UpstreamError):
    """上游 429：配额或频率限制，稍后重试有意义。"""


class UnauthorizedError(UpstreamError):
    """上游 401 或 403：认证凭据无效或权限不足。"""


class UpstreamUnavailableError(UpstreamError):
    """上游 5xx 或网络错误：拿不到可用响应。"""


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def upstream_error(status_code: int, body: bytes) -> UpstreamError:
    """从上游响应构造异常，并按状态码归类。

    body 是上游的原始响应体：解析错误字段用完整 body，记录到异常里的
    body 截断到 2KB，避免异常消息过大。
    """
    text = body[:UPSTREAM_BODY_LIMIT].decode("utf-8", errors="replace")
    if len(body) > UPSTREAM_BODY_LIMIT:
        text += "...(truncated)"

    code = ""
    title = ""
    invalid_params: list[str] = []
    payload: Any = None
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        payload = None
    if isinstance(payload, dict):
        code = _as_text(payload.get("code"))
        error = payload.get("error")
        if isinstance(error, dict):
            title = _as_text(error.get("title"))
            raw_params = error.get("invalidParams")
            if isinstance(raw_params, list):
                invalid_params = [text for text in (_as_text(item) for item in raw_params) if text]
        elif isinstance(error, str):
            title = error
        if not title:
            title = _as_text(payload.get("title"))

    cls: type[UpstreamError]
    if status_code == 429:
        cls = QuotaExceededError
    elif status_code in (401, 403):
        cls = UnauthorizedError
    elif 400 <= status_code < 500:
        cls = UpstreamRejectedError
    else:
        cls = UpstreamUnavailableError

    return cls(
        status_code=status_code,
        code=code,
        title=title,
        invalid_params=invalid_params,
        body=text,
    )
