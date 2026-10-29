"""位置解析与两代位置形态。"""

from __future__ import annotations

import pytest

from qwx.errors import InvalidLocationError
from qwx.location import Location, parse_location


def test_parse_coordinate_pair_is_longitude_first() -> None:
    loc = parse_location("116.41,39.92")
    assert loc.lon == pytest.approx(116.41)
    assert loc.lat == pytest.approx(39.92)


def test_parse_location_id() -> None:
    assert parse_location("101010100").id == "101010100"
    assert parse_location("10101010012A").id == "10101010012A"
    assert parse_location("P2352").id == "P2352"


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "121.47", "abc", "1,2,3", "116.41,abc", "abc,39.92", "NaN,39.92", "181,0", "0,91"],
)
def test_parse_rejects_bad_locations(raw: str) -> None:
    with pytest.raises(InvalidLocationError):
        parse_location(raw)


def test_query_is_longitude_first() -> None:
    loc = Location(lat=39.92, lon=116.41)
    assert loc.query() == "116.41,39.92"


def test_query_falls_back_to_id_then_name() -> None:
    assert Location(id="101010100").query() == "101010100"
    assert Location(name="北京").query() == "北京"
    assert Location().query() == ""


def test_path_is_latitude_first() -> None:
    # 新一代接口的路径参数是纬度在前，写反了上游回 400。
    lat, lon = Location(lat=39.92, lon=116.41).path()
    assert (lat, lon) == ("39.92", "116.41")


def test_path_requires_coordinates() -> None:
    with pytest.raises(InvalidLocationError):
        Location(id="101010100").path()


def test_coordinates_are_rounded_to_two_decimals() -> None:
    lat, lon = Location(lat=39.923456, lon=116.417894).coordinates()
    assert (lat, lon) == (39.92, 116.42)


def test_zero_location() -> None:
    assert Location().is_zero()
    assert not Location(lat=39.92).is_zero()
    assert Location(lat=39.92).has_coordinates()
