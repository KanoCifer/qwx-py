"""v1/solarradiation 的模型解析。"""

from __future__ import annotations

from qwx.v1.solarradiation.types import (
    POA,
    Endpoint,
    Forecast,
    Result,
    SolarAngle,
    Weather,
)

UPSTREAM_BODY = {
    "metadata": {"tag": "c4ca4238a0b923820dcc509a6f75849b"},
    "forecasts": [
        {
            "forecastTime": "2023-10-15T11:30Z",
            "solarAngle": {"azimuth": 184, "elevation": 40},
            "dni": {"value": 25.16, "unit": "W/m²"},
            "dhi": {"value": 136.29, "unit": "W/m²"},
            "ghi": {"value": 152.57, "unit": "W/m²"},
            "weather": {
                "temperature": {"value": 18.6, "unit": "°C"},
                "windSpeed": {"value": 2.78, "unit": "m/s"},
                "humidity": 76,
            },
            "poa": {
                "global": {"value": 134.39, "unit": "W/m²"},
                "direct": {"value": 9.35, "unit": "W/m²"},
                "diffuse": {"value": 125.04, "unit": "W/m²"},
                "reflected": {"value": 1.52, "unit": "W/m²"},
            },
        },
        {
            "forecastTime": "2023-10-15T11:45Z",
            "solarAngle": {"azimuth": 189, "elevation": 40},
            "dni": {"value": 20.71, "unit": "W/m²"},
            "dhi": {"value": 132.14, "unit": "W/m²"},
            "ghi": {"value": 145.47, "unit": "W/m²"},
        },
    ],
}


def test_result_parses_the_upstream_shape() -> None:
    """结果类型按上游 JSON 形态解析。"""
    got = Result.model_validate(UPSTREAM_BODY)

    assert got.metadata.tag == "c4ca4238a0b923820dcc509a6f75849b"
    assert len(got.forecasts) == 2

    first = got.forecasts[0]
    assert first.forecast_time == "2023-10-15T11:30Z"
    assert first.solar_angle.azimuth == 184
    assert first.solar_angle.elevation == 40
    assert first.dni.value == 25.16
    assert first.dni.unit == "W/m²"
    assert first.dhi.value == 136.29
    assert first.ghi.value == 152.57


def test_optional_blocks_are_none_when_absent() -> None:
    """没请求 extra 时上游不给这两个对象。"""
    got = Result.model_validate(UPSTREAM_BODY)

    second = got.forecasts[1]
    assert second.weather is None
    assert second.poa is None


def test_weather_block_is_parsed() -> None:
    """extra=weather 的对象解析。"""
    got = Result.model_validate(UPSTREAM_BODY)
    weather = got.forecasts[0].weather

    assert weather is not None
    assert weather.temperature.value == 18.6
    assert weather.temperature.unit == "°C"
    assert weather.wind_speed.value == 2.78
    assert weather.wind_speed.unit == "m/s"
    # 这一族的湿度是百分数（0~100），不是新一代天气端点的 0~1 比例。
    assert weather.humidity == 76


def test_poa_block_is_parsed() -> None:
    """extra=poa 的对象解析。"""
    got = Result.model_validate(UPSTREAM_BODY)
    poa = got.forecasts[0].poa

    assert poa is not None
    assert poa.global_.value == 134.39
    assert poa.global_.unit == "W/m²"
    assert poa.direct.value == 9.35
    assert poa.diffuse.value == 125.04
    assert poa.reflected.value == 1.52


def test_missing_optional_fields_are_none() -> None:
    """可选字段缺失时是 None，与零值可区分。"""
    got = Forecast.model_validate({"forecastTime": "2023-10-15T11:30Z"})

    assert got.weather is None
    assert got.poa is None
    assert got.forecast_time == "2023-10-15T11:30Z"


def test_unknown_fields_are_kept() -> None:
    """上游新增的字段被保留，不丢弃。"""
    got = Forecast.model_validate({"forecastTime": "2023-10-15T11:30Z", "brandNewField": 1})

    assert got.model_extra is not None
    assert got.model_extra["brandNewField"] == 1


def test_empty_result_has_defaults() -> None:
    """空响应也能解析出模型。"""
    got = Result.model_validate({})

    assert got.forecasts == []
    assert got.metadata.tag == ""


def test_poa_global_alias_is_the_upstream_key() -> None:
    """`global` 是 Python 关键字，字段名写成 global_，别名仍是 global。"""
    poa = POA.model_validate({"global": {"value": 1.0, "unit": "W/m²"}})

    assert poa.global_.value == 1.0


def test_endpoint_identifier_is_frozen() -> None:
    """端点标识是公开契约，取值发布后不再变更。"""
    assert str(Endpoint) == "solarradiation/v1/forecast"


def test_solar_angle_defaults() -> None:
    """太阳角度缺失时是零值。"""
    angle = SolarAngle.model_validate({})

    assert angle.azimuth == 0.0
    assert angle.elevation == 0.0


def test_weather_humidity_default() -> None:
    """湿度缺失时是零值。"""
    weather = Weather.model_validate({})

    assert weather.humidity == 0.0
    assert weather.temperature.value == 0.0
