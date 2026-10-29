"""旧一代历史天气接口（/v7/historical/weather）。

导出本族公开符号：模型、端点常量与服务客户端。
"""

from __future__ import annotations

from qwx.v7.historical.client import AsyncHistoricalService, HistoricalService
from qwx.v7.historical.types import (
    Daily,
    Endpoint,
    Hourly,
    Options,
    Result,
)

__all__ = [
    "AsyncHistoricalService",
    "Daily",
    "Endpoint",
    "HistoricalService",
    "Hourly",
    "Options",
    "Result",
]
