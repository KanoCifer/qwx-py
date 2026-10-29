"""新一代天气预报接口（/weather/v1/*）。

导出本族公开符号：模型、端点常量与服务客户端。
"""

from __future__ import annotations

from qwx.v1.weather.client import AsyncWeatherService, WeatherService
from qwx.v1.weather.types import (
    MAX_DAILY_DAYS,
    MAX_HOURLY_HOURS,
    Astro,
    Condition,
    CurrentWeather,
    Daily,
    DailyForecast,
    DayNight,
    DewPoint,
    EndpointCurrent,
    EndpointDaily,
    EndpointHourly,
    Hourly,
    HourlyForecast,
    Options,
    Precipitation,
    Pressure,
    Visibility,
    Wind,
    WindDirection,
    WindGust,
)

__all__ = [
    "MAX_DAILY_DAYS",
    "MAX_HOURLY_HOURS",
    "Astro",
    "AsyncWeatherService",
    "Condition",
    "CurrentWeather",
    "Daily",
    "DailyForecast",
    "DayNight",
    "DewPoint",
    "EndpointCurrent",
    "EndpointDaily",
    "EndpointHourly",
    "Hourly",
    "HourlyForecast",
    "Options",
    "Precipitation",
    "Pressure",
    "Visibility",
    "WeatherService",
    "Wind",
    "WindDirection",
    "WindGust",
]
