"""GeoAPI 端点族的模型解析。"""

from __future__ import annotations

import json

import pytest

from qwx.errors import InvalidLocationError
from qwx.geo import (
    CityResult,
    Options,
    Place,
    POIRangeOptions,
    POIResult,
    POIType,
    RangeResult,
    TopCityResult,
)
from qwx.lang import Lang
from qwx.refer import Refer

CITY_BODY = {
    "code": "200",
    "location": [
        {
            "name": "东城",
            "id": "101011600",
            "lat": "39.91755",
            "lon": "116.41876",
            "adm2": "北京",
            "adm1": "北京市",
            "country": "中国",
            "tz": "Asia/Shanghai",
            "utcOffset": "+08:00",
            "isDst": "0",
            "type": "city",
            "rank": "35",
            "fxLink": "https://www.qweather.com/weather/dongcheng-101011600.html",
        }
    ],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
}


def test_city_result_parses_locations_and_refer() -> None:
    got = CityResult.model_validate(CITY_BODY)

    assert got.code == "200"
    assert len(got.locations) == 1
    place = got.locations[0]
    assert isinstance(place, Place)
    assert place.id == "101011600"
    assert place.name == "东城"
    assert place.lat == "39.91755"
    assert place.lon == "116.41876"
    assert place.adm1 == "北京市"
    assert place.adm2 == "北京"
    assert place.country == "中国"
    assert place.tz == "Asia/Shanghai"
    assert place.utc_offset == "+08:00"
    assert place.is_dst == "0"
    assert place.type == "city"
    assert place.rank == "35"
    assert place.fx_link.endswith("dongcheng-101011600.html")

    assert isinstance(got.refer, Refer)
    assert got.refer.sources == ["https://developer.qweather.com/attribution.html"]
    assert got.refer.license == ["QWeather Developers License"]


def test_poi_result_parses_poi_alias() -> None:
    got = POIResult.model_validate(
        {
            "code": "200",
            "poi": [
                {
                    "name": "景山公园",
                    "id": "10101010012A",
                    "lat": "39.91999",
                    "lon": "116.38999",
                    "adm2": "北京",
                    "adm1": "北京",
                    "type": "scenic",
                    "rank": "671",
                }
            ],
        }
    )

    assert len(got.pois) == 1
    assert got.pois[0].name == "景山公园"
    assert got.pois[0].type == "scenic"


def test_range_result_parses_poi_alias() -> None:
    got = RangeResult.model_validate({"code": "200", "poi": [{"name": "景山公园"}]})

    assert len(got.pois) == 1
    assert got.pois[0].name == "景山公园"


def test_top_city_result_parses_top_city_list_alias() -> None:
    got = TopCityResult.model_validate(
        {"code": "200", "topCityList": [{"name": "北京", "id": "101010100"}]}
    )

    assert len(got.cities) == 1
    assert got.cities[0].id == "101010100"
    assert got.cities[0].name == "北京"


def test_missing_fields_fall_back_to_zero_values() -> None:
    got = CityResult.model_validate({})

    assert got.code == ""
    assert got.locations == []
    assert got.refer.sources == []
    assert got.refer.license == []


def test_unknown_fields_are_kept() -> None:
    got = CityResult.model_validate({"code": "200", "extra": 1})

    assert got.model_extra == {"extra": 1}
    assert got.model_dump()["extra"] == 1


def test_place_extra_fields_are_kept() -> None:
    got = CityResult.model_validate({"location": [{"name": "东城", "extra": 1}]})

    assert got.locations[0].model_extra == {"extra": 1}


def test_models_accept_python_field_names() -> None:
    got = POIResult.model_validate({"pois": [{"name": "景山公园"}]})

    assert len(got.pois) == 1


def test_display_name_joins_city_and_district() -> None:
    place = CityResult.model_validate(CITY_BODY).locations[0]

    # name=区县、adm2=城市，拼出来是"城市+区县"。
    assert place.display_name() == "北京东城"


def test_display_name_deduplicates_city() -> None:
    # 城市级条目 name 与 adm2 同名，不能拼成"北京北京"。
    place = Place(name="北京", adm2="北京")

    assert place.display_name() == "北京"


def test_coordinates_parse_lat_lon_strings() -> None:
    place = Place(lat="39.91755", lon="116.41876")

    lat, lon = place.coordinates()

    assert lat == 39.91755
    assert lon == 116.41876


def test_coordinates_without_numbers_raise() -> None:
    place = Place(name="东城")

    with pytest.raises(InvalidLocationError):
        place.coordinates()


def test_options_defaults_match_go() -> None:
    options = Options()

    assert options.lang is Lang.UNSPECIFIED
    assert options.number == 0
    assert options.adm == ""
    assert options.range == ""
    assert options.city == ""


def test_poi_range_options_defaults_match_go() -> None:
    options = POIRangeOptions()

    assert options.lang is Lang.UNSPECIFIED
    assert options.number == 0
    assert options.radius == 0


def test_poi_type_members_are_closed_set() -> None:
    assert POIType.SCENIC.value == "scenic"
    assert POIType.CSTA.value == "CSTA"
    assert POIType.TSTA.value == "TSTA"


def test_json_round_trip_keeps_fields() -> None:
    got = CityResult.model_validate(json.loads(json.dumps(CITY_BODY)))

    assert got.locations[0].utc_offset == "+08:00"
    assert got.refer.license == ["QWeather Developers License"]
