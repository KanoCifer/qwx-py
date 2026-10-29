"""v1/weather 的模型解析。"""

from __future__ import annotations

from qwx.v1.weather.types import (
    Astro,
    Condition,
    CurrentWeather,
    Daily,
    DailyForecast,
    DayNight,
    DewPoint,
    Hourly,
    HourlyForecast,
    Precipitation,
    Pressure,
    Value,
    Visibility,
    Wind,
    WindDirection,
    WindGust,
)

CURRENT_BODY = {
    "metadata": {"tag": "abc", "attributions": ["https://developer.qweather.com/attribution.html"]},
    "condition": {"text": "少云", "code": "102"},
    "temperature": {"value": 31.71, "unit": "°C"},
    "feelsLike": {"value": 33.64, "unit": "°C"},
    "humidity": 0.69,
    "wind": {
        "direction": {"degree": 226, "compass": "sw"},
        "speed": {"value": 4.74, "unit": "m/s"},
        "scale": 3,
    },
    "windGust": {"value": 7.07, "unit": "m/s"},
    "precipitation": {
        "amount": {"value": 0, "unit": "mm"},
        "intensity": {"value": 0, "unit": "mm/h"},
        "type": "none",
    },
    "pressure": {"value": 1001.5, "unit": "hPa"},
    "visibility": {"value": 29020, "unit": "m"},
    "dewPoint": {"value": 25.36, "unit": "°C"},
    "cloudCover": 0.05,
    "uvIndex": 3,
}

DAILY_BODY = {
    "metadata": {"tag": "abc"},
    "days": [
        {
            "forecastStartTime": "2024-08-10T22:00Z",
            "forecastEndTime": "2024-08-11T22:00Z",
            "astro": {
                "sunrise": "2024-08-11T04:22Z",
                "sunset": "2024-08-11T19:34Z",
                "moonPhase": "waning-gibbous",
            },
            "temperatureMax": {"value": 29.94, "unit": "°C"},
            "temperatureMin": {"value": 20.93, "unit": "°C"},
            "temperatureAvg": {"value": 25.57, "unit": "°C"},
            "uvIndexMax": 6,
            "daytime": {
                "forecastStartTime": "2024-08-11T05:00Z",
                "forecastEndTime": "2024-08-11T17:00Z",
                "condition": {"text": "小雨", "code": "305"},
                "temperatureMax": {"value": 29.94, "unit": "°C"},
                "temperatureMin": {"value": 20.93, "unit": "°C"},
                "wind": {
                    "direction": {"degree": 270, "compass": "w"},
                    "speed": {"value": 1.87, "unit": "m/s"},
                    "scale": 2,
                },
                "windGustMax": {"value": 6.64, "unit": "m/s"},
                "precipitation": {
                    "amount": {"value": 0.75, "unit": "mm"},
                    "probability": 0.64,
                    "type": "rain",
                },
                "cloudCover": 0.32,
                "humidity": 0.52,
            },
            "nighttime": {
                "forecastStartTime": "2024-08-11T17:00Z",
                "forecastEndTime": "2024-08-12T05:00Z",
                "condition": {"text": "晴间多云", "code": "103"},
                "temperatureMax": {"value": 29.8, "unit": "°C"},
                "temperatureMin": {"value": 19.95, "unit": "°C"},
                "wind": {
                    "direction": {"degree": 343, "compass": "nnw"},
                    "speed": {"value": 2.33, "unit": "m/s"},
                    "scale": 2,
                },
                "windGustMax": {"value": 7.16, "unit": "m/s"},
                "precipitation": {
                    "amount": {"value": 0, "unit": "mm"},
                    "probability": 0,
                    "type": "none",
                },
                "cloudCover": 0.34,
                "humidity": 0.56,
            },
        }
    ],
}


def test_current_weather_parses() -> None:
    got = CurrentWeather.model_validate(CURRENT_BODY)

    assert got.metadata.tag == "abc"
    assert got.metadata.attributions == ["https://developer.qweather.com/attribution.html"]
    assert got.condition == Condition(text="少云", code="102")
    assert got.temperature.value == 31.71
    assert got.temperature.unit == "°C"
    assert got.feels_like.value == 33.64
    # 湿度与云量是 0~1 的比例，不是百分数。
    assert got.humidity == 0.69
    assert got.cloud_cover == 0.05
    assert got.uv_index == 3
    assert got.wind == Wind(
        direction=WindDirection(degree=226, compass="sw"),
        speed=Value(value=4.74, unit="m/s"),
        scale=3,
    )
    assert got.wind_gust == WindGust(value=7.07, unit="m/s")
    assert got.pressure == Pressure(value=1001.5, unit="hPa")
    assert got.visibility == Visibility(value=29020, unit="m")
    assert got.dew_point == DewPoint(value=25.36, unit="°C")


def test_current_precipitation_has_intensity_but_no_probability() -> None:
    got = CurrentWeather.model_validate(CURRENT_BODY)

    assert got.precipitation.amount.value == 0
    assert got.precipitation.amount.unit == "mm"
    assert got.precipitation.intensity is not None
    assert got.precipitation.intensity.unit == "mm/h"
    # 实时天气没有降水概率字段，应为 None 而非 0。
    assert got.precipitation.probability is None
    assert got.precipitation.type == "none"


def test_missing_optional_fields_are_none() -> None:
    got = CurrentWeather.model_validate({"condition": {"code": "100"}})

    assert got.precipitation.intensity is None
    assert got.precipitation.probability is None
    assert got.metadata.zero_result is None
    # 缺失的标量取零值，而不是 None。
    assert got.humidity == 0.0
    assert got.condition.text == ""


def test_unknown_fields_are_kept() -> None:
    got = CurrentWeather.model_validate({**CURRENT_BODY, "futureField": {"a": 1}})

    assert got.model_extra is not None
    assert got.model_extra["futureField"] == {"a": 1}


def test_daily_forecast_parses_day_and_night() -> None:
    got = DailyForecast.model_validate(DAILY_BODY)

    assert len(got.days) == 1
    day = got.days[0]
    assert isinstance(day, Daily)
    assert day.forecast_start_time == "2024-08-10T22:00Z"
    assert day.forecast_end_time == "2024-08-11T22:00Z"
    assert day.temperature_avg.value == 25.57
    assert day.temperature_max.value == 29.94
    assert day.temperature_min.value == 20.93
    assert day.uv_index_max == 6
    assert day.astro is not None
    assert day.astro.moon_phase == "waning-gibbous"
    assert day.astro.sunrise == "2024-08-11T04:22Z"
    assert day.astro.sunset == "2024-08-11T19:34Z"


def test_day_night_uses_wind_gust_max() -> None:
    day = DailyForecast.model_validate(DAILY_BODY).days[0]

    assert isinstance(day.daytime, DayNight)
    assert day.daytime.wind_gust_max.value == 6.64
    assert day.nighttime.wind_gust_max.value == 7.16
    assert day.daytime.humidity == 0.52
    assert day.daytime.cloud_cover == 0.32


def test_day_night_probability_zero_is_not_none() -> None:
    day = DailyForecast.model_validate(DAILY_BODY).days[0]

    assert day.daytime.precipitation.probability == 0.64
    # 概率为 0 与没有该字段是两回事。
    assert day.nighttime.precipitation.probability == 0
    assert day.nighttime.precipitation.probability is not None
    # 逐日预报的白天/夜间时段上游不给降水强度，不能读出零值强度。
    assert day.daytime.precipitation.intensity is None
    assert day.nighttime.precipitation.intensity is None


def test_daily_without_astro_has_none() -> None:
    day = Daily.model_validate({"forecastStartTime": "2024-08-10T22:00Z"})

    assert day.astro is None
    assert day.daytime.condition.code == ""


def test_hourly_forecast_parses() -> None:
    got = HourlyForecast.model_validate(
        {
            "metadata": {"tag": "t"},
            "hours": [
                {
                    "forecastTime": "2024-08-11T05:00Z",
                    "condition": {"text": "小雨", "code": "305"},
                    "temperature": {"value": 22.5, "unit": "°C"},
                    "feelsLike": {"value": 23.5, "unit": "°C"},
                    "humidity": 0.72,
                    "wind": {"direction": {"degree": 90, "compass": "e"}, "scale": 2},
                    "windGust": {"value": 5.0, "unit": "m/s"},
                    "precipitation": {
                        "amount": {"value": 0.5, "unit": "mm"},
                        "intensity": {"value": 0.2, "unit": "mm/h"},
                        "probability": 0.3,
                        "type": "rain",
                    },
                    "pressure": {"value": 1002.0, "unit": "hPa"},
                    "visibility": {"value": 10000, "unit": "m"},
                    "dewPoint": {"value": 18.0, "unit": "°C"},
                    "cloudCover": 0.9,
                    "uvIndex": 1,
                }
            ],
        }
    )

    assert len(got.hours) == 1
    hour = got.hours[0]
    assert isinstance(hour, Hourly)
    assert hour.forecast_time == "2024-08-11T05:00Z"
    assert hour.humidity == 0.72
    assert hour.cloud_cover == 0.9
    assert hour.precipitation.probability == 0.3
    assert hour.precipitation.intensity is not None
    assert hour.precipitation.intensity.value == 0.2


def test_astro_defaults_to_empty_strings() -> None:
    astro = Astro.model_validate({"moonPhase": "waxing-gibbous"})

    assert astro.moon_phase == "waxing-gibbous"
    assert astro.sunrise == ""
    assert astro.solar_noon == ""
    assert astro.moon_transit == ""


def test_precipitation_defaults() -> None:
    got = Precipitation.model_validate({})

    assert got.amount.value == 0.0
    assert got.intensity is None
    assert got.probability is None
    assert got.type == ""
