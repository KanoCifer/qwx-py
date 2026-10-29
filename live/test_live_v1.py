"""新一代 v1 四个端点族的联网冒烟测试。

覆盖天气、空气质量、预警、太阳辐射预报四个族，每个族打到真实上游，
断言响应的关键字段。

    pytest live -q

需要真实凭据（QWX_API_HOST + QWX_API_KEY 或 QWX_JWT_*）。缺凭据时整份
文件跳过，不会红。

太阳辐射预报的 hours 上限另有一个探测用例：官方文档页写 72、同一份
OpenAPI 的 schema 写 60，上游实际取哪个值以实测为准，用例把两种结果都
记下来，不因为上游行为与文档不符而失败。
"""

from __future__ import annotations

import warnings

import pytest
from conftest import LOC, requires_credentials

import qwx
from qwx.request import Request
from qwx.v1 import solarradiation
from qwx.v1.airquality import AirQualityService
from qwx.v1.airquality.types import Options as AirQualityOptions
from qwx.v1.alert import AlertService
from qwx.v1.solarradiation import Result as SolarRadiationResult
from qwx.v1.solarradiation import SolarRadiationService
from qwx.v1.solarradiation.types import Options as SolarRadiationOptions
from qwx.v1.types import Options as V1Options
from qwx.v1.weather import WeatherService

pytestmark = [pytest.mark.live, requires_credentials]

# 监测站 ID 取自官方文档示例。
STATION_ID = "P58911"


def test_weather_current(client: qwx.Client) -> None:
    """实时天气：温度带单位、天气现象有文字、湿度是 0~1 的比例。"""
    service = WeatherService(client)
    result = service.current(LOC, V1Options(lang=qwx.Lang.ZH, local_time=True))

    assert result.temperature.unit, "温度必须带单位"
    assert result.condition.text, "天气现象必须有文字描述"
    assert 0.0 <= result.humidity <= 1.0, f"湿度是比例不是百分数，实际 {result.humidity}"


def test_weather_hourly(client: qwx.Client) -> None:
    """逐小时预报：拿到列表，每条有预报时刻。"""
    service = WeatherService(client)
    result = service.hourly(LOC, 24, V1Options(lang=qwx.Lang.ZH, local_time=True))

    assert result.hours, "逐小时预报不应为空"
    for item in result.hours:
        assert item.forecast_time, "每条逐小时预报都要有预报时刻"


def test_weather_daily(client: qwx.Client) -> None:
    """逐日预报：拿到列表，每条有起止时刻与最高气温单位。"""
    service = WeatherService(client)
    result = service.daily(LOC, 3, V1Options(lang=qwx.Lang.ZH, local_time=True))

    assert result.days, "逐日预报不应为空"
    for item in result.days:
        assert item.forecast_start_time, "每条逐日预报都要有起始时刻"
        assert item.temperature_max.unit, "最高气温必须带单位"


def test_air_quality_current(client: qwx.Client) -> None:
    """实时空气质量：拿到指数与污染物列表，条目字段齐全。"""
    service = AirQualityService(client)
    result = service.current(LOC, AirQualityOptions(lang=qwx.Lang.ZH))

    assert result.indexes is not None, "indexes 不应是 None"
    assert result.pollutants is not None, "pollutants 不应是 None"
    assert isinstance(result.indexes, list)
    assert isinstance(result.pollutants, list)
    for index in result.indexes:
        assert index.code, "每个指数条目都要有标准代码"
        assert index.aqi >= 0, "指数值不应为负"
    for pollutant in result.pollutants:
        assert pollutant.code, "每个污染物都要有代码"


def test_air_quality_station(client: qwx.Client) -> None:
    """单个监测站：拿到污染物列表，浓度带单位。"""
    service = AirQualityService(client)
    result = service.station(STATION_ID, AirQualityOptions(lang=qwx.Lang.ZH))

    assert result.pollutants is not None, "pollutants 不应是 None"
    assert isinstance(result.pollutants, list)
    for pollutant in result.pollutants:
        assert pollutant.code, "每个污染物都要有代码"
        assert pollutant.concentration.unit, "浓度必须带单位"


def test_alert_current(client: qwx.Client) -> None:
    """预警实况：alerts 是列表不是 None。

    没有预警时上游给空列表，不是 null，所以这里只断言类型与条目结构。
    """
    service = AlertService(client)
    result = service.current(LOC, V1Options(lang=qwx.Lang.ZH, local_time=True))

    assert result.alerts is not None, "alerts 不应是 None"
    assert isinstance(result.alerts, list)
    for alert in result.alerts:
        assert alert.id, "每条预警都要有 ID"
        assert alert.event_type.code, "每条预警都要有事件代码"


def test_solar_radiation_forecast(client: qwx.Client) -> None:
    """太阳辐射预报：拿到结果模型与预报列表，每条的总水平面辐照带单位。"""
    service = SolarRadiationService(client)
    result = service.forecast(LOC, 24, SolarRadiationOptions(interval=60))

    assert isinstance(result, SolarRadiationResult), "应解析成 Result 模型"
    assert result.forecasts, "预报列表不应为空"
    for forecast in result.forecasts:
        assert forecast.forecast_time, "每条预报都要有预报时刻"
        assert forecast.ghi.unit, "总水平面辐照必须带单位"


def test_solar_radiation_hours_upper_bound(client: qwx.Client) -> None:
    """探测上游对 hours 的真实上限。

    绕过 SDK 的客户端校验直接打上游：hours=72 是官方文档页写的上限，
    hours=73 应当被上游拒绝（400）。实测与口径不一致时记一条警告，不让
    用例失败 —— 官方文档页写 72、OpenAPI schema 写 60，这个分歧本身已知。
    """
    errors: dict[int, qwx.UpstreamError | None] = {}
    for hours in (72, 73):
        request = Request(
            method="GET",
            path="/solarradiation/v1/forecast/39.92/116.41",
            query={"hours": str(hours)},
            endpoint=solarradiation.Endpoint,
        )
        try:
            client.do(request)
        except qwx.UpstreamError as exc:
            errors[hours] = exc
        else:
            errors[hours] = None

    rejected = errors[73]
    if errors[72] is None and isinstance(rejected, qwx.UpstreamRejectedError):
        # 与口径一致：72 小时放行，73 小时被上游拒绝。
        assert rejected.status_code == 400, f"预期 400，实际 {rejected.status_code}"
        return

    detail = f"hours 上限实测与口径不符：hours=72 -> {errors[72]!r}；hours=73 -> {rejected!r}"
    warnings.warn(detail, UserWarning, stacklevel=2)
