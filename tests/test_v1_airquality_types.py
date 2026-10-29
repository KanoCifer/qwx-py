"""空气质量端点族的模型解析。"""

from __future__ import annotations

import json

from qwx.v1.airquality import (
    Advice,
    Color,
    Current,
    DailyForecast,
    Day,
    Health,
    Hour,
    HourlyForecast,
    Index,
    Pollutant,
    PollutantBrief,
    Station,
    StationData,
    SubIndex,
)
from qwx.v1.types import Metadata, Value

CURRENT_BODY = {
    "metadata": {"tag": "t", "attributions": ["a"]},
    "indexes": [
        {
            "code": "us-epa",
            "name": "AQI (US)",
            "aqi": 46,
            "aqiDisplay": "46",
            "level": "1",
            "category": "Good",
            "color": {"red": 0, "green": 228, "blue": 0, "alpha": 1},
            "primaryPollutant": {"code": "pm2p5", "name": "PM 2.5", "fullName": "细颗粒物"},
            "health": {
                "effect": "No health effects.",
                "advice": {
                    "generalPopulation": "正常",
                    "sensitivePopulation": "正常",
                },
            },
        }
    ],
    "pollutants": [
        {
            "code": "pm2p5",
            "name": "PM 2.5",
            "fullName": "Fine particulate matter",
            "concentration": {"value": 11.0, "unit": "μg/m3"},
            "subIndexes": [{"code": "us-epa", "aqi": 46, "aqiDisplay": "46"}],
        }
    ],
    "stations": [{"id": "P51762", "name": "North Holywood"}],
}


def test_current_parses_indexes_pollutants_and_stations() -> None:
    got = Current.model_validate(CURRENT_BODY)

    assert isinstance(got.metadata, Metadata)
    assert got.metadata.tag == "t"
    assert got.metadata.attributions == ["a"]

    assert len(got.indexes) == 1
    index = got.indexes[0]
    assert index.code == "us-epa"
    assert index.name == "AQI (US)"
    assert index.aqi == 46.0
    assert index.aqi_display == "46"
    assert index.level == "1"
    assert index.category == "Good"

    assert index.color == Color(red=0, green=228, blue=0, alpha=1)

    assert index.primary_pollutant == PollutantBrief(
        code="pm2p5", name="PM 2.5", full_name="细颗粒物"
    )
    assert index.health == Health(
        effect="No health effects.",
        advice=Advice(general_population="正常", sensitive_population="正常"),
    )

    assert len(got.pollutants) == 1
    pollutant = got.pollutants[0]
    assert pollutant.code == "pm2p5"
    assert pollutant.full_name == "Fine particulate matter"
    assert pollutant.concentration == Value(value=11.0, unit="μg/m3")
    assert pollutant.sub_indexes == [SubIndex(code="us-epa", aqi=46.0, aqi_display="46")]

    assert got.stations == [Station(id="P51762", name="North Holywood")]


def test_optional_fields_are_none_when_missing() -> None:
    got = Current.model_validate({"indexes": [{"code": "qaqi", "aqi": 0.5}]})

    index = got.indexes[0]
    assert index.aqi == 0.5
    assert index.primary_pollutant is None
    assert index.health is None
    # 缺失与零值可区分：没给的字段是零值而不是 None。
    assert index.aqi_display == ""
    assert index.color == Color(red=0, green=0, blue=0, alpha=0)
    assert got.metadata.tag == ""
    assert got.indexes[0].color.red == 0


def test_daily_forecast_parses_days() -> None:
    body = {
        "metadata": {"tag": "t"},
        "days": [
            {
                "forecastStartTime": "2026-10-29T00:00+08:00",
                "forecastEndTime": "2026-10-29T23:59+08:00",
                "indexes": [{"code": "us-epa", "aqi": 30}],
                "pollutants": [
                    {
                        "code": "pm2p5",
                        "concentration": {"value": 20.0, "unit": "μg/m3"},
                    }
                ],
            }
        ],
    }
    got = DailyForecast.model_validate(body)

    assert len(got.days) == 1
    day = got.days[0]
    assert isinstance(day, Day)
    assert day.forecast_start_time == "2026-10-29T00:00+08:00"
    assert day.forecast_end_time == "2026-10-29T23:59+08:00"
    assert day.indexes[0].aqi == 30.0
    assert day.pollutants[0].concentration.value == 20.0


def test_hourly_forecast_parses_hours() -> None:
    body = {
        "metadata": {"tag": "t"},
        "hours": [
            {
                "forecastTime": "2026-10-29T05:00Z",
                "indexes": [{"code": "qaqi", "aqi": 0.2}],
                "pollutants": [],
            }
        ],
    }
    got = HourlyForecast.model_validate(body)

    assert len(got.hours) == 1
    hour = got.hours[0]
    assert isinstance(hour, Hour)
    assert hour.forecast_time == "2026-10-29T05:00Z"
    assert hour.indexes[0].aqi == 0.2
    assert hour.pollutants == []


def test_station_data_parses_pollutants() -> None:
    body = {
        "metadata": {"tag": "t"},
        "pollutants": [
            {
                "code": "pm2p5",
                "name": "PM 2.5",
                "concentration": {"value": 9.5, "unit": "μg/m3"},
                "subIndexes": [],
            }
        ],
    }
    got = StationData.model_validate(body)

    assert len(got.pollutants) == 1
    pollutant = got.pollutants[0]
    assert isinstance(pollutant, Pollutant)
    assert pollutant.concentration.value == 9.5


def test_empty_payload_gives_empty_lists() -> None:
    got = Current.model_validate({})

    assert got.indexes == []
    assert got.pollutants == []
    assert got.stations == []


def test_unknown_fields_are_kept() -> None:
    got = Current.model_validate({"indexes": [{"code": "us-epa", "aqi": 46, "extra": 1}]})

    index = got.indexes[0]
    assert index.model_extra == {"extra": 1}
    assert index.model_dump()["extra"] == 1


def test_model_accepts_python_field_names() -> None:
    got = Index.model_validate(
        {
            "code": "us-epa",
            "aqi_display": "46",
            "primary_pollutant": {"code": "pm2p5"},
        }
    )

    assert got.aqi_display == "46"
    assert got.primary_pollutant == PollutantBrief(code="pm2p5")


def test_models_are_frozen() -> None:
    got = Index.model_validate({"code": "us-epa"})

    try:
        got.code = "qaqi"  # type: ignore[misc]
    except Exception as exc:
        assert "frozen" in str(exc).lower() or "cannot assign" in str(exc).lower()
    else:
        raise AssertionError("model should be frozen")


def test_json_round_trip_keeps_fields() -> None:
    got = Current.model_validate(json.loads(json.dumps(CURRENT_BODY)))

    assert got.indexes[0].aqi_display == "46"
    assert got.pollutants[0].concentration.unit == "μg/m3"
