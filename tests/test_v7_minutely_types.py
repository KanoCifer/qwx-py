"""v7/minutely 的模型解析。"""

from __future__ import annotations

from qwx.v7.minutely.types import Minutely, Result

BODY = {
    "code": "200",
    "updateTime": "2021-12-16T18:55+08:00",
    "fxLink": "https://www.qweather.com",
    "summary": "95分钟后雨就停了",
    "minutely": [
        {"fxTime": "2021-12-16T18:55+08:00", "precip": "0.00", "type": "rain"},
        {"fxTime": "2021-12-16T19:00+08:00", "precip": "0.15", "type": "snow"},
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}


def test_result_parses_all_fields() -> None:
    result = Result.model_validate(BODY)

    assert result.code == "200"
    assert result.update_time == "2021-12-16T18:55+08:00"
    assert result.fx_link == "https://www.qweather.com"
    assert result.summary == "95分钟后雨就停了"
    assert len(result.minutely) == 2
    assert result.refer.sources == ["https://developer.qweather.com/attribution.html"]
    assert result.refer.license == ["QWeather Developers License"]


def test_minutely_parses_all_fields() -> None:
    result = Result.model_validate(BODY)
    first = result.minutely[0]
    assert first.fx_time == "2021-12-16T18:55+08:00"
    # precip 保持字符串：空串与 "0.00" 含义不同。
    assert first.precip == "0.00"
    assert first.type == "rain"
    assert result.minutely[1].precip == "0.15"
    assert result.minutely[1].type == "snow"


def test_missing_blocks_fall_back_to_defaults() -> None:
    result = Result.model_validate({"code": "200"})
    assert result.summary == ""
    assert result.minutely == []
    assert result.refer.sources == []


def test_models_keep_unknown_fields() -> None:
    result = Result.model_validate({**BODY, "someNewField": "x"})
    assert result.model_extra is not None
    assert result.model_extra["someNewField"] == "x"

    minutely = Minutely.model_validate({"fxTime": "2021-12-16T18:55+08:00", "newKey": 1})
    assert minutely.model_extra is not None
    assert minutely.model_extra["newKey"] == 1
