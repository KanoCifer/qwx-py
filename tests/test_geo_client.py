"""GeoAPI 端点族的请求行为。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest

from qwx import APIKeyAuth
from qwx.cache import MemoryCache
from qwx.client import AsyncClient, Client
from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.geo import (
    AsyncGeoService,
    CityResult,
    EndpointCity,
    EndpointPOI,
    EndpointPOIRange,
    EndpointTopCities,
    GeoService,
    Options,
    POIRangeOptions,
    POIResult,
    POIType,
    RangeResult,
    TopCityResult,
)
from qwx.lang import Lang
from qwx.location import Location
from qwx.request import Request
from qwx.ttl import Endpoint

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
        }
    ],
    "refer": {"sources": ["a"], "license": ["l"]},
}

POI_BODY = {
    "code": "200",
    "poi": [
        {
            "name": "景山公园",
            "id": "10101010012A",
            "lat": "39.91999",
            "lon": "116.38999",
            "adm2": "北京",
            "type": "scenic",
        }
    ],
}

TOP_BODY = {"code": "200", "topCityList": [{"name": "北京", "id": "101010100"}]}


class RecordingDoer:
    """记录最后一次请求的替身。"""

    def __init__(self) -> None:
        self.requests: list[Request] = []

    def do(self, request: Request) -> Any:
        self.requests.append(request)
        return request.out.model_validate({}) if request.out is not None else b""

    async def ado(self, request: Request) -> Any:
        return self.do(request)


def make_client(handler: Any, **kwargs: Any) -> Client:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    kwargs.setdefault("sleep", lambda _delay: None)
    return Client(APIKeyAuth("k"), "https://example.test", http_client=http, **kwargs)


def make_async_client(handler: Any, **kwargs: Any) -> AsyncClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    kwargs.setdefault("sleep", lambda _delay: asyncio.sleep(0))
    return AsyncClient(APIKeyAuth("k"), "https://example.test", http_client=http, **kwargs)


def test_lookup_city_requests_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CITY_BODY)

    client = make_client(handler)
    service = GeoService(client)
    got = service.lookup_city(Location(id="101011600"), Options(lang=Lang.ZH))

    assert isinstance(got, CityResult)
    assert seen[0].url.path == "/geo/v2/city/lookup"
    assert seen[0].url.params["location"] == "101011600"
    assert seen[0].url.params["lang"] == "zh"
    assert got.locations[0].adm2 == "北京"


def test_lookup_city_accepts_place_name() -> None:
    """GeoAPI 是唯一认地名的接口族。"""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CITY_BODY)

    client = make_client(handler)
    service = GeoService(client)
    service.lookup_city(Location(name="北京"))

    assert seen[0].url.params["location"] == "北京"


def test_lookup_poi_requests_path_and_type() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=POI_BODY)

    client = make_client(handler)
    service = GeoService(client)
    got = service.lookup_poi(Location(lat=39.92, lon=116.41), POIType.SCENIC)

    assert isinstance(got, POIResult)
    assert seen[0].url.path == "/geo/v2/poi/lookup"
    assert seen[0].url.params["type"] == "scenic"
    assert seen[0].url.params["location"] == "116.41,39.92"
    assert got.pois[0].name == "景山公园"


def test_poi_range_requests_path_type_and_radius() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=POI_BODY)

    client = make_client(handler)
    service = GeoService(client)
    got = service.poi_range(
        Location(lat=39.92, lon=116.41),
        POIType.TSTA,
        POIRangeOptions(radius=20),
    )

    assert isinstance(got, RangeResult)
    assert seen[0].url.path == "/geo/v2/poi/range"
    assert seen[0].url.params["type"] == "TSTA"
    assert seen[0].url.params["radius"] == "20"


def test_poi_range_with_zero_radius_does_not_report_radius() -> None:
    """半径为 0 只进键、不上报，上游按自己的默认值处理。"""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=POI_BODY)

    client = make_client(handler)
    service = GeoService(client)
    service.poi_range(Location(lat=39.92, lon=116.41), POIType.SCENIC)

    assert "radius" not in seen[0].url.params


def test_top_cities_requests_path_and_number() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=TOP_BODY)

    client = make_client(handler)
    service = GeoService(client)
    got = service.top_cities(Options(lang=Lang.ZH, number=5))

    assert isinstance(got, TopCityResult)
    assert seen[0].url.path == "/geo/v2/city/top"
    assert seen[0].url.params["number"] == "5"
    assert seen[0].url.params["lang"] == "zh"
    assert got.cities[0].id == "101010100"


def test_lookup_poi_rejects_unknown_type_without_calling_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = GeoService(client)

    with pytest.raises(InvalidParameterError):
        service.lookup_poi(Location(lat=39.92, lon=116.41), "bad")

    assert calls == []


def test_poi_range_rejects_unknown_type_without_calling_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = GeoService(client)

    with pytest.raises(InvalidParameterError):
        service.poi_range(Location(lat=39.92, lon=116.41), "bad")

    assert calls == []


def test_poi_range_requires_coordinates() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = GeoService(client)

    with pytest.raises(InvalidLocationError):
        service.poi_range(Location(id="101010100"), POIType.SCENIC)

    assert calls == []


def test_invalid_lang_rejects_without_calling_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = GeoService(client)

    with pytest.raises(InvalidParameterError):
        service.lookup_city(
            Location(lat=39.92, lon=116.41), Options(lang=Lang("zh_hans", "zh_hans"))
        )

    assert calls == []


@pytest.mark.parametrize(
    ("want", "call"),
    [
        ("qwx:geo:city:101011600:lang=zh", "city_id"),
        ("qwx:geo:city:116.41,39.92:lang=zh:adm=101010100:range=cn", "city_full"),
        ("qwx:geo:poi:scenic:116.41,39.92", "poi"),
        ("qwx:geo:poi:scenic:116.41,39.92:city=101010100", "poi_city"),
        (
            "qwx:geo:poirange:scenic:116.41,39.92:lang=zh:n=5:r=20",
            "range_full",
        ),
        ("qwx:geo:poirange:scenic:116.41,39.92:r=0", "range_zero"),
        ("qwx:geo:topcity:lang=zh:n=5", "top"),
        ("qwx:geo:topcity:range=world", "top_range"),
    ],
)
def test_cache_keys_are_frozen(want: str, call: str) -> None:
    """缓存键字面量在已发布版本里定死。"""
    doer = RecordingDoer()
    service = GeoService(doer)
    coord = Location(lat=39.92, lon=116.41)

    if call == "city_id":
        service.lookup_city(Location(id="101011600"), Options(lang=Lang.ZH))
    elif call == "city_full":
        service.lookup_city(coord, Options(lang=Lang.ZH, adm="101010100", range="cn"))
    elif call == "poi":
        service.lookup_poi(coord, POIType.SCENIC)
    elif call == "poi_city":
        service.lookup_poi(coord, POIType.SCENIC, Options(city="101010100"))
    elif call == "range_full":
        service.poi_range(
            coord,
            POIType.SCENIC,
            POIRangeOptions(lang=Lang.ZH, number=5, radius=20),
        )
    elif call == "range_zero":
        service.poi_range(coord, POIType.SCENIC, POIRangeOptions())
    elif call == "top":
        service.top_cities(Options(lang=Lang.ZH, number=5))
    else:
        service.top_cities(Options(range="world"))

    assert doer.requests[-1].cache_key == want


def test_optional_params_reach_query_and_key() -> None:
    """既要发给上游，也要进缓存键 —— 漏进键就是一次串味。"""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CITY_BODY)

    client = make_client(handler)
    service = GeoService(client)
    service.lookup_city(
        Location(lat=39.92, lon=116.41),
        Options(lang=Lang.ZH, adm="101010100", range="cn"),
    )

    assert seen[0].url.params["adm"] == "101010100"
    assert seen[0].url.params["range"] == "cn"


def test_endpoints_and_ttls_are_reported() -> None:
    doer = RecordingDoer()
    service = GeoService(doer)
    coord = Location(lat=39.92, lon=116.41)

    service.lookup_city(coord)
    service.lookup_poi(coord, POIType.SCENIC)
    service.poi_range(coord, POIType.SCENIC)
    service.top_cities()

    city, poi, poi_range, top = doer.requests
    assert city.endpoint == EndpointCity
    assert city.ttl == timedelta(hours=24)
    assert poi.endpoint == EndpointPOI
    assert poi.ttl == timedelta(hours=24)
    assert poi_range.endpoint == EndpointPOIRange
    assert poi_range.ttl == timedelta(hours=24)
    assert top.endpoint == EndpointTopCities
    assert top.ttl == timedelta(hours=24)


def test_endpoint_values_are_frozen() -> None:
    """端点常量的值在已发布版本里定死。"""
    assert EndpointCity == Endpoint("geo/v2/city/lookup")
    assert EndpointPOI == Endpoint("geo/v2/poi/lookup")
    assert EndpointPOIRange == Endpoint("geo/v2/poi/range")
    assert EndpointTopCities == Endpoint("geo/v2/city/top")


def test_cache_hit_does_not_call_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=CITY_BODY)

    client = make_client(handler, cache=MemoryCache())
    service = GeoService(client)
    loc = Location(id="101011600")

    first = service.lookup_city(loc, Options(lang=Lang.ZH))
    second = service.lookup_city(loc, Options(lang=Lang.ZH))

    assert len(calls) == 1
    assert first.locations[0].id == second.locations[0].id


def test_async_service_mirrors_sync() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CITY_BODY)

    async def run() -> CityResult:
        client = make_async_client(handler)
        service = AsyncGeoService(client)
        return await service.lookup_city(Location(id="101011600"), Options(lang=Lang.ZH))

    got = asyncio.run(run())

    assert isinstance(got, CityResult)
    assert seen[0].url.path == "/geo/v2/city/lookup"
    assert seen[0].url.params["location"] == "101011600"


def test_async_service_rejects_unknown_poi_type() -> None:
    async def run() -> None:
        client = make_async_client(lambda request: httpx.Response(200, json={}))
        service = AsyncGeoService(client)
        await service.lookup_poi(Location(lat=39.92, lon=116.41), "bad")

    with pytest.raises(InvalidParameterError):
        asyncio.run(run())
