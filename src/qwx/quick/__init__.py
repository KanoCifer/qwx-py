"""快速查询层：按位置一次取齐天气、空气质量与预警。

它把 GeoAPI 城市检索、新一代天气、空气质量与预警几个端点组合成一次调用。

    from qwx.quick import QuickService

    report = QuickService(client).query("北京")
    print(report.current, report.air_quality)
"""

from __future__ import annotations

from .client import AsyncQuickService, QuickService
from .types import (
    DEFAULT_DAYS,
    DEFAULT_HOURS,
    EndpointError,
    Options,
    Part,
    Report,
)

__all__ = [
    "DEFAULT_DAYS",
    "DEFAULT_HOURS",
    "AsyncQuickService",
    "EndpointError",
    "Options",
    "Part",
    "QuickService",
    "Report",
]
