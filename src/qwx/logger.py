"""SDK 的日志。

日志走标准库 logging。不注入 logger 时不产生任何输出 —— SDK 不替用户
决定日志去向。级别由 handler 决定，SDK 不再过滤：handler 放行 DEBUG，
就会收到缓存命中这类明细。

日志里没有认证凭据（凭据在请求头上）与响应体，查询参数也不记录；但有
接口路径与缓存键，两者可能带位置坐标。SDK 不对坐标脱敏，日志的可见
范围自己把握，要脱敏就在注入时包一层自己的 handler。
"""

from __future__ import annotations

import logging
import re
from typing import Any

__all__ = [
    "LOG_FIELD_ATTEMPT",
    "LOG_FIELD_CACHE_KEY",
    "LOG_FIELD_DURATION_MS",
    "LOG_FIELD_ENDPOINT",
    "LOG_FIELD_ERROR",
    "LOG_FIELD_METHOD",
    "LOG_FIELD_PATH",
    "LOG_FIELD_STATUS",
    "LOG_FIELD_UPSTREAM_CODE",
    "LOG_FIELD_UPSTREAM_TITLE",
    "Logger",
    "sanitize_error_text",
]

# 日志字段名。集中定义，用户可以在自己的 handler 里按字段名过滤。
LOG_FIELD_ENDPOINT = "endpoint"
LOG_FIELD_METHOD = "method"
LOG_FIELD_PATH = "path"
LOG_FIELD_STATUS = "status"
LOG_FIELD_DURATION_MS = "duration_ms"
LOG_FIELD_CACHE_KEY = "cache_key"
LOG_FIELD_ATTEMPT = "attempt"
LOG_FIELD_ERROR = "error"
LOG_FIELD_UPSTREAM_CODE = "upstream_code"
LOG_FIELD_UPSTREAM_TITLE = "upstream_title"

_URL_QUERY_RE = re.compile(r"(https?://[^\s\"'<>?]+)\?[^\s\"'<>]*")


def sanitize_error_text(exc: BaseException | None) -> str:
    """去掉错误文本里的查询参数。

    传输层的错误文本里内嵌了完整 URL，含查询参数。GeoAPI 的
    location=地名 这类用户输入会跟着漏进日志，这里只留 URL 的 path 部分，
    错误原因照旧。
    """
    if exc is None:
        return ""
    return _URL_QUERY_RE.sub(r"\1", str(exc))


class Logger:
    """把 SDK 内部事件记到标准库 logging。

    默认静默：构造时没有给 logger 就挂一个 NullHandler，输出全部丢弃。
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        if logger is None:
            logger = logging.getLogger("qwx")
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        """底层 logger。"""
        return self._logger

    def enabled(self, level: int) -> bool:
        """该级别会不会被输出。"""
        return self._logger.isEnabledFor(level)

    def log(self, level: int, message: str, fields: dict[str, Any] | None = None) -> None:
        """记一条日志。

        先问 handler 放不放行这个级别，不放行就不构造字段。
        """
        if not self.enabled(level):
            return
        self._logger.log(level, message, extra=fields or {})
