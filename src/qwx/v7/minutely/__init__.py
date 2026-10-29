"""旧一代分钟级降水预报接口（/v7/minutely/5m）。

导出本族公开符号：模型、端点常量与服务客户端。
"""

from __future__ import annotations

from qwx.v7.minutely.client import AsyncMinutelyService, MinutelyService
from qwx.v7.minutely.types import (
    Endpoint,
    Minutely,
    Result,
)

__all__ = [
    "AsyncMinutelyService",
    "Endpoint",
    "Minutely",
    "MinutelyService",
    "Result",
]
