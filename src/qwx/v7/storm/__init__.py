"""旧一代台风数据接口（/v7/tropical/*）。

台风数据至今只有旧一代版本，没有新一代。导出本族公开符号：模型、端点
常量与服务客户端。
"""

from __future__ import annotations

from .client import AsyncStormService, StormService
from .types import (
    BasinNP,
    EndpointForecast,
    EndpointList,
    EndpointTrack,
    Forecast,
    ForecastResult,
    ListResult,
    StormState,
    StormSummary,
    TrackPoint,
    TrackResult,
    WindRadius,
)

__all__ = [
    "AsyncStormService",
    "BasinNP",
    "EndpointForecast",
    "EndpointList",
    "EndpointTrack",
    "Forecast",
    "ForecastResult",
    "ListResult",
    "StormService",
    "StormState",
    "StormSummary",
    "TrackPoint",
    "TrackResult",
    "WindRadius",
]
