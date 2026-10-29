"""v7/ocean 的模型解析。"""

from __future__ import annotations

from qwx.v7.ocean.types import Result, Tide, TideHourly

BODY = {
    "code": "200",
    "updateTime": "2021-02-04T05:02+08:00",
    "fxLink": "https://www.qweather.com",
    "tideTable": [
        {"fxTime": "2021-02-06T03:48+08:00", "height": "2.17", "type": "H"},
        {"fxTime": "2021-02-06T09:52+08:00", "height": "0.31", "type": "L"},
    ],
    "tideHourly": [
        {"fxTime": "2021-02-06T00:00+08:00", "height": "1.02"},
        {"fxTime": "2021-02-06T01:00+08:00", "height": "1.28"},
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}


def test_result_parses_all_fields() -> None:
    result = Result.model_validate(BODY)

    assert result.code == "200"
    assert result.update_time == "2021-02-04T05:02+08:00"
    assert result.fx_link == "https://www.qweather.com"
    assert len(result.tide_table) == 2
    assert len(result.tide_hourly) == 2
    assert result.refer.sources == ["https://developer.qweather.com/attribution.html"]
    assert result.refer.license == ["QWeather Developers License"]


def test_tide_parses_all_fields() -> None:
    result = Result.model_validate(BODY)
    first = result.tide_table[0]

    # 时间是站点当地时间字符串，不是 UTC。
    assert first.fx_time == "2021-02-06T03:48+08:00"
    # 高度保持字符串：上游的小数位是它的表达精度。
    assert first.height == "2.17"
    assert first.type == "H"
    assert result.tide_table[1].type == "L"


def test_tide_hourly_parses_all_fields() -> None:
    result = Result.model_validate(BODY)
    first = result.tide_hourly[0]

    assert first.fx_time == "2021-02-06T00:00+08:00"
    assert first.height == "1.02"


def test_missing_blocks_fall_back_to_defaults() -> None:
    result = Result.model_validate({"code": "200"})

    assert result.update_time == ""
    assert result.fx_link == ""
    assert result.tide_table == []
    assert result.tide_hourly == []
    assert result.refer.sources == []
    assert result.refer.license == []


def test_models_keep_unknown_fields() -> None:
    result = Result.model_validate({**BODY, "someNewField": "x"})
    assert result.model_extra is not None
    assert result.model_extra["someNewField"] == "x"

    tide = Tide.model_validate({"fxTime": "2021-02-06T03:48+08:00", "newKey": 1})
    assert tide.model_extra is not None
    assert tide.model_extra["newKey"] == 1

    hourly = TideHourly.model_validate({"fxTime": "2021-02-06T00:00+08:00", "newKey": 1})
    assert hourly.model_extra is not None
    assert hourly.model_extra["newKey"] == 1
