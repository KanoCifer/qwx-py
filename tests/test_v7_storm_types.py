"""台风端点族的模型解析。"""

from __future__ import annotations

import json

from qwx.refer import Refer
from qwx.v7.storm import (
    Forecast,
    ForecastResult,
    ListResult,
    StormState,
    StormSummary,
    TrackPoint,
    TrackResult,
    WindRadius,
)

LIST_BODY = {
    "code": "200",
    "updateTime": "2020-12-31T16:00+00:00",
    "fxLink": "https://www.qweather.com",
    "storm": [
        {"id": "NP2018", "name": "莫拉菲", "basin": "NP", "year": "2020", "isActive": "0"},
        {"id": "NP2022", "name": "环高", "basin": "NP", "year": "2020", "isActive": "1"},
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}

FORECAST_BODY = {
    "code": "200",
    "updateTime": "2021-07-27T03:00+00:00",
    "fxLink": "https://www.qweather.com",
    "forecast": [
        {
            "fxTime": "2021-07-27T20:00+08:00",
            "lat": "31.7",
            "lon": "118.4",
            "type": "TS",
            "pressure": "990",
            "windSpeed": "18",
            "moveSpeed": "",
            "moveDir": "",
            "move360": "",
        }
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}

TRACK_BODY = {
    "code": "200",
    "updateTime": "2024-05-30T06:11+00:00",
    "fxLink": "https://www.qweather.com",
    "isActive": "1",
    "now": {
        "pubTime": "2024-05-30T05:00+08:00",
        "lat": "27.7",
        "lon": "134.5",
        "type": "STS",
        "pressure": "980",
        "windSpeed": "30",
        "moveSpeed": "21",
        "moveDir": "NE",
        "move360": "",
        "windRadius30": {
            "neRadius": "120",
            "seRadius": "150",
            "swRadius": "120",
            "nwRadius": "100",
        },
    },
    "track": [
        {
            "time": "2024-05-29T05:00+08:00",
            "lat": "25.3",
            "lon": "136.1",
            "type": "STS",
            "pressure": "980",
            "windSpeed": "30",
            "moveSpeed": "21",
            "moveDir": "NE",
            "move360": "",
        }
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}


def test_list_result_parses_storm_array_alias() -> None:
    """上游的 "storm" 是数组，不是对象。"""
    got = ListResult.model_validate(LIST_BODY)

    assert got.code == "200"
    assert got.update_time == "2020-12-31T16:00+00:00"
    assert got.fx_link == "https://www.qweather.com"
    assert len(got.storms) == 2
    first = got.storms[0]
    assert isinstance(first, StormSummary)
    assert first.id == "NP2018"
    assert first.name == "莫拉菲"
    assert first.basin == "NP"
    assert first.year == "2020"
    # isActive 上游是字符串 "1"/"0"，不是 bool。
    assert first.is_active == "0"
    assert got.storms[1].is_active == "1"

    # 展示上游数据时要一并展示来源与许可声明。
    assert isinstance(got.refer, Refer)
    assert got.refer.sources == ["https://developer.qweather.com/attribution.html"]
    assert got.refer.license == ["QWeather Developers License"]


def test_forecast_result_parses_flat_storm_state() -> None:
    """预报元素把台风属性平铺在上游 JSON 里。"""
    got = ForecastResult.model_validate(FORECAST_BODY)

    assert len(got.forecast) == 1
    item = got.forecast[0]
    assert isinstance(item, Forecast)
    assert item.fx_time == "2021-07-27T20:00+08:00"
    # 数值保持字符串，不转浮点数。
    assert item.lat == "31.7"
    assert item.lon == "118.4"
    assert item.type == "TS"
    assert item.pressure == "990"
    assert item.wind_speed == "18"
    # 上游可能给空串，不是缺字段。
    assert item.move_speed == ""
    assert item.move_dir == ""
    assert item.move360 == ""
    # 上游没给风圈时是 None，不是零值半径。
    assert item.wind_radius30 is None
    assert item.wind_radius50 is None
    assert item.wind_radius64 is None


def test_forecast_result_parses_wind_radius() -> None:
    got = ForecastResult.model_validate(
        {
            "forecast": [
                {
                    "fxTime": "2024-05-30T13:00+08:00",
                    "windRadius30": {
                        "neRadius": "120",
                        "seRadius": "150",
                        "swRadius": "120",
                        "nwRadius": "100",
                    },
                    "windRadius50": {
                        "neRadius": "60",
                        "seRadius": "60",
                        "swRadius": "60",
                        "nwRadius": "50",
                    },
                }
            ]
        }
    )

    item = got.forecast[0]
    radius30 = item.wind_radius30
    assert isinstance(radius30, WindRadius)
    assert radius30.ne_radius == "120"
    assert radius30.se_radius == "150"
    assert radius30.sw_radius == "120"
    assert radius30.nw_radius == "100"

    radius50 = item.wind_radius50
    assert radius50 is not None
    assert radius50.nw_radius == "50"
    # 12 级风圈上游没给，仍是 None。
    assert item.wind_radius64 is None


def test_track_result_parses_now_and_track() -> None:
    got = TrackResult.model_validate(TRACK_BODY)

    assert got.is_active == "1"
    now = got.now
    assert isinstance(now, TrackPoint)
    assert now.pub_time == "2024-05-30T05:00+08:00"
    assert now.lat == "27.7"
    assert now.lon == "134.5"
    assert now.type == "STS"
    assert now.pressure == "980"
    assert now.wind_speed == "30"
    assert now.move_dir == "NE"
    radius30 = now.wind_radius30
    assert radius30 is not None
    assert radius30.ne_radius == "120"
    # 10 级与 12 级风圈上游没给。
    assert now.wind_radius50 is None
    assert now.wind_radius64 is None

    assert len(got.track) == 1
    point = got.track[0]
    assert point.time == "2024-05-29T05:00+08:00"
    assert point.lat == "25.3"


def test_track_result_now_is_none_when_storm_ended() -> None:
    """台风结束时上游给 now=null。"""
    got = TrackResult.model_validate({"code": "200", "isActive": "0", "now": None, "track": []})

    assert got.now is None
    assert got.is_active == "0"
    assert got.track == []


def test_forecast_result_is_empty_when_storm_ended() -> None:
    """台风结束时预报列表为空 —— 不是错误。"""
    got = ForecastResult.model_validate(
        {"code": "200", "updateTime": "2021-07-27T03:00+00:00", "forecast": []}
    )

    assert got.forecast == []
    assert got.code == "200"


def test_missing_fields_fall_back_to_zero_values() -> None:
    got = ListResult.model_validate({})

    assert got.code == ""
    assert got.update_time == ""
    assert got.fx_link == ""
    assert got.storms == []
    assert got.refer.sources == []
    assert got.refer.license == []


def test_optional_fields_are_none_when_missing() -> None:
    got = TrackResult.model_validate({"code": "200"})

    assert got.now is None
    assert got.track == []

    state = StormState.model_validate({})
    assert state.wind_radius30 is None
    assert state.wind_radius50 is None
    assert state.wind_radius64 is None


def test_unknown_fields_are_kept() -> None:
    got = ListResult.model_validate({"code": "200", "extra": 1})

    assert got.model_extra == {"extra": 1}
    assert got.model_dump()["extra"] == 1


def test_nested_unknown_fields_are_kept() -> None:
    got = ListResult.model_validate({"storm": [{"id": "NP2018", "extra": 1}]})

    assert got.storms[0].model_extra == {"extra": 1}


def test_models_accept_python_field_names() -> None:
    got = ListResult.model_validate({"storms": [{"id": "NP2018"}]})

    assert len(got.storms) == 1
    assert got.storms[0].id == "NP2018"


def test_json_round_trip_keeps_fields() -> None:
    got = ForecastResult.model_validate(json.loads(json.dumps(FORECAST_BODY)))

    assert got.forecast[0].lat == "31.7"
    assert got.refer.license == ["QWeather Developers License"]
