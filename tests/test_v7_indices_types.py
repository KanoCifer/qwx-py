"""v7/indices 的模型解析。"""

from __future__ import annotations

from qwx.v7.indices.types import DailyIndex, Result

BODY = {
    "code": "200",
    "updateTime": "2021-12-16T18:35+08:00",
    "fxLink": "https://www.qweather.com",
    "daily": [
        {
            "date": "2021-12-16",
            "type": "1",
            "name": "运动指数",
            "level": "3",
            "category": "较不宜",
            "text": "天气较好，但考虑天气寒冷。",
        },
        {
            "date": "2021-12-17",
            "type": "4",
            "name": "钓鱼指数",
            "level": "2",
            "category": "适宜",
            "text": "",
        },
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}


def test_result_parses_all_fields() -> None:
    result = Result.model_validate(BODY)

    assert result.code == "200"
    assert result.update_time == "2021-12-16T18:35+08:00"
    assert result.fx_link == "https://www.qweather.com"
    assert len(result.daily) == 2
    assert result.refer.sources == ["https://developer.qweather.com/attribution.html"]
    assert result.refer.license == ["QWeather Developers License"]


def test_daily_index_parses_all_fields() -> None:
    result = Result.model_validate(BODY)
    first = result.daily[0]

    assert first.date == "2021-12-16"
    # type 与 level 上游给的是字符串，保持字符串。
    assert first.type == "1"
    assert first.name == "运动指数"
    assert first.level == "3"
    assert first.category == "较不宜"
    assert first.text == "天气较好，但考虑天气寒冷。"


def test_missing_blocks_fall_back_to_defaults() -> None:
    result = Result.model_validate({"code": "200"})

    assert result.update_time == ""
    assert result.fx_link == ""
    assert result.daily == []
    assert result.refer.sources == []


def test_daily_index_missing_fields_fall_back_to_defaults() -> None:
    index = DailyIndex.model_validate({"date": "2021-12-16"})

    assert index.type == ""
    assert index.name == ""
    assert index.level == ""
    assert index.category == ""
    assert index.text == ""


def test_models_keep_unknown_fields() -> None:
    result = Result.model_validate({**BODY, "someNewField": "x"})
    assert result.model_extra is not None
    assert result.model_extra["someNewField"] == "x"

    index = DailyIndex.model_validate({"date": "2021-12-16", "newKey": 1})
    assert index.model_extra is not None
    assert index.model_extra["newKey"] == 1
