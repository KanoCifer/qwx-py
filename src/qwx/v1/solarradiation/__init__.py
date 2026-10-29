"""太阳辐射预报接口（/solarradiation/v1/forecast）。

导出本族公开符号：模型、端点常量与服务客户端。
"""

from __future__ import annotations

from qwx.v1.solarradiation.client import AsyncSolarRadiationService, SolarRadiationService
from qwx.v1.solarradiation.types import (
    MAX_FORECAST_HOURS,
    MIN_FORECAST_HOURS,
    POA,
    Endpoint,
    Forecast,
    Options,
    Result,
    SolarAngle,
    Weather,
)

__all__ = [
    "MAX_FORECAST_HOURS",
    "MIN_FORECAST_HOURS",
    "POA",
    "AsyncSolarRadiationService",
    "Endpoint",
    "Forecast",
    "Options",
    "Result",
    "SolarAngle",
    "SolarRadiationService",
    "Weather",
]
