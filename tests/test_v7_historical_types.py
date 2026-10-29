"""v7/historical 的模型解析。"""

from __future__ import annotations

from qwx.v7.historical.types import Daily, Hourly, Result

BODY = {
    "code": "200",
    "fxLink": "https://www.qweather.com",
    "weatherDaily": {
        "date": "2020-07-25",
        "sunrise": "05:08",
        "sunset": "19:33",
        "moonrise": "09:54",
        "moonset": "22:40",
        "moonPhase": "峨眉月",
        "tempMax": "33",
        "tempMin": "23",
        "humidity": "52",
        "precip": "0.0",
        "pressure": "1000",
    },
    "weatherHourly": [
        {
            "time": "2020-07-25 21:00",
            "temp": "29",
            "icon": "104",
            "text": "阴",
            "precip": "0.0",
            "wind360": "208",
            "windDir": "西南风",
            "windScale": "2",
            "windSpeed": "7",
            "humidity": "52",
            "pressure": "1000",
        },
        {
            "time": "2020-07-25 22:00",
            "temp": "29",
            "icon": "104",
            "text": "阴",
            "precip": "0.0",
            "wind360": "188",
            "windDir": "南风",
            "windScale": "2",
            "windSpeed": "7",
            "humidity": "57",
            "pressure": "1000",
        },
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}


def test_result_parses_the_two_aliased_blocks() -> None:
    result = Result.model_validate(BODY)

    assert result.code == "200"
    assert result.fx_link == "https://www.qweather.com"
    # 上游的键是 weatherDaily / weatherHourly，不是 daily / hourly。
    assert result.daily is not None
    assert result.daily.date == "2020-07-25"
    assert len(result.hourly) == 2
    assert result.hourly[0].wind_dir == "西南风"
    assert result.hourly[1].wind_dir == "南风"


def test_daily_keeps_numbers_as_strings() -> None:
    result = Result.model_validate(BODY)
    daily = result.daily
    assert daily is not None
    # 小数位数是上游的表达精度，转数值会丢掉。
    assert daily.precip == "0.0"
    assert daily.temp_max == "33"
    assert daily.temp_min == "23"
    assert daily.humidity == "52"
    assert daily.pressure == "1000"
    assert daily.moon_phase == "峨眉月"


def test_hourly_keeps_numbers_as_strings() -> None:
    result = Result.model_validate(BODY)
    hourly = result.hourly[0]
    assert hourly.time == "2020-07-25 21:00"
    assert hourly.temp == "29"
    assert hourly.icon == "104"
    assert hourly.text == "阴"
    assert hourly.wind360 == "208"
    assert hourly.wind_scale == "2"
    assert hourly.wind_speed == "7"
    assert hourly.humidity == "52"
    assert hourly.precip == "0.0"
    assert hourly.pressure == "1000"


def test_refer_is_parsed() -> None:
    result = Result.model_validate(BODY)
    assert result.refer.sources == ["https://developer.qweather.com/attribution.html"]
    assert result.refer.license == ["QWeather Developers License"]


def test_missing_optional_times_are_none() -> None:
    result = Result.model_validate(
        {
            "code": "200",
            "weatherDaily": {
                "date": "2020-07-25",
                "sunrise": None,
                "sunset": None,
                "moonrise": None,
                "moonset": None,
                "moonPhase": "",
                "tempMax": "10",
                "tempMin": "2",
                "humidity": "60",
                "precip": "0.0",
                "pressure": "1001",
            },
        }
    )
    daily = result.daily
    assert daily is not None
    assert daily.sunrise is None
    assert daily.sunset is None
    assert daily.moonrise is None
    assert daily.moonset is None


def test_daily_block_may_be_absent() -> None:
    result = Result.model_validate({"code": "200"})
    assert result.daily is None
    assert result.hourly == []


def test_models_keep_unknown_fields() -> None:
    result = Result.model_validate({**BODY, "someNewField": "x"})
    assert result.model_extra is not None
    assert result.model_extra["someNewField"] == "x"

    daily = Daily.model_validate({"date": "2020-07-25", "newKey": 1})
    assert daily.model_extra is not None
    assert daily.model_extra["newKey"] == 1

    hourly = Hourly.model_validate({"time": "2020-07-25 21:00", "newKey": 2})
    assert hourly.model_extra is not None
    assert hourly.model_extra["newKey"] == 2
