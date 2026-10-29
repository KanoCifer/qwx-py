"""新一代空气质量接口（/airquality/v1/*）。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝。
"""

from __future__ import annotations

from .client import AirQualityService, AsyncAirQualityService
from .types import (
    Advice,
    Color,
    Current,
    DailyForecast,
    Day,
    EndpointCurrent,
    EndpointDaily,
    EndpointHourly,
    EndpointStation,
    Health,
    Hour,
    HourlyForecast,
    Index,
    Options,
    Pollutant,
    PollutantBrief,
    Station,
    StationData,
    SubIndex,
)

__all__ = [
    "Advice",
    "AirQualityService",
    "AsyncAirQualityService",
    "Color",
    "Current",
    "DailyForecast",
    "Day",
    "EndpointCurrent",
    "EndpointDaily",
    "EndpointHourly",
    "EndpointStation",
    "Health",
    "Hour",
    "HourlyForecast",
    "Index",
    "Options",
    "Pollutant",
    "PollutantBrief",
    "Station",
    "StationData",
    "SubIndex",
]
