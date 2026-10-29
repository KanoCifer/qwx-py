"""v7/astronomy 的模型解析：字段、可选字段缺失与未知字段保留。"""

from __future__ import annotations

from qwx.lang import Lang
from qwx.v7.astronomy import (
    AngleResult,
    MoonPhase,
    MoonResult,
    Options,
    SunResult,
)

SUN_BODY = {
    "code": "200",
    "updateTime": "2026-05-31T02:00+08:00",
    "fxLink": "https://dev.qweather.com/docs/api/astronomy/sunrise-sunset/",
    "sunrise": "05:12",
    "sunset": "19:24",
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}

MOON_BODY = {
    "code": "200",
    "updateTime": "2026-05-31T02:00+08:00",
    "fxLink": "https://dev.qweather.com/docs/api/astronomy/moon-and-moon-phase/",
    "moonrise": "20:11",
    "moonset": "06:12",
    "moonPhase": [
        {
            "fxTime": "2026-05-31T20:00+08:00",
            "value": "1",
            "name": "新月",
            "illumination": "0.5",
            "icon": "01",
        }
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}

ANGLE_BODY = {
    "code": "200",
    "solarElevationAngle": "35.42",
    "solarAzimuthAngle": "196.31",
    "solarHour": "1102",
    "hourAngle": "-12.55",
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}


def test_sun_result_parses_fields() -> None:
    got = SunResult.model_validate(SUN_BODY)

    assert got.code == "200"
    assert got.update_time == "2026-05-31T02:00+08:00"
    assert got.fx_link == "https://dev.qweather.com/docs/api/astronomy/sunrise-sunset/"
    assert got.sunrise == "05:12"
    assert got.sunset == "19:24"
    # 展示上游数据时要一并展示来源与许可声明。
    assert got.refer.sources == ["https://developer.qweather.com/attribution.html"]
    assert got.refer.license == ["QWeather Developers License"]


def test_sun_result_missing_sunrise_is_none() -> None:
    """高纬度与极昼极夜地区上游给 null。"""
    got = SunResult.model_validate({"code": "200", "sunrise": None, "sunset": None})

    assert got.sunrise is None
    assert got.sunset is None


def test_sun_result_absent_sunrise_is_none() -> None:
    got = SunResult.model_validate({"code": "200"})

    assert got.sunrise is None
    assert got.sunset is None
    assert got.update_time == ""
    assert got.refer.sources == []


def test_sun_result_keeps_unknown_fields() -> None:
    got = SunResult.model_validate({**SUN_BODY, "extraField": "keep-me"})

    assert got.model_extra is not None
    assert got.model_extra["extraField"] == "keep-me"


def test_moon_result_parses_fields() -> None:
    got = MoonResult.model_validate(MOON_BODY)

    assert got.code == "200"
    assert got.moonrise == "20:11"
    assert got.moonset == "06:12"
    assert len(got.moon_phase) == 1
    phase = got.moon_phase[0]
    assert phase.fx_time == "2026-05-31T20:00+08:00"
    assert phase.value == "1"
    assert phase.name == "新月"
    assert phase.illumination == "0.5"
    assert phase.icon == "01"


def test_moon_result_missing_moonrise_is_none() -> None:
    got = MoonResult.model_validate({"code": "200", "moonPhase": []})

    assert got.moonrise is None
    assert got.moonset is None
    assert got.moon_phase == []


def test_moon_result_keeps_unknown_fields() -> None:
    got = MoonResult.model_validate({**MOON_BODY, "extraField": 1})

    assert got.model_extra is not None
    assert got.model_extra["extraField"] == 1


def test_moon_phase_defaults() -> None:
    phase = MoonPhase.model_validate({})

    assert phase.fx_time == ""
    assert phase.value == ""
    assert phase.name == ""
    assert phase.illumination == ""
    assert phase.icon == ""


def test_angle_result_parses_fields() -> None:
    got = AngleResult.model_validate(ANGLE_BODY)

    assert got.code == "200"
    assert got.solar_elevation_angle == "35.42"
    assert got.solar_azimuth_angle == "196.31"
    assert got.solar_hour == "1102"
    assert got.hour_angle == "-12.55"
    assert len(got.refer.sources) == 1


def test_angle_result_keeps_unknown_fields() -> None:
    got = AngleResult.model_validate({**ANGLE_BODY, "extraField": "x"})

    assert got.model_extra is not None
    assert got.model_extra["extraField"] == "x"


def test_options_default_lang_is_unspecified() -> None:
    options = Options()

    assert options.lang == Lang.UNSPECIFIED
    assert options.lang.api == ""
