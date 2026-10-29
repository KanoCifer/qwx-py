"""空气质量端点族的请求行为。"""

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
from qwx.lang import Lang
from qwx.location import Location
from qwx.request import Request
from qwx.ttl import Endpoint, TTLMap
from qwx.v1.airquality import (
    AirQualityService,
    AsyncAirQualityService,
    Current,
    DailyForecast,
    EndpointCurrent,
    EndpointDaily,
    EndpointHourly,
    EndpointStation,
    HourlyForecast,
    Options,
    StationData,
)

CURRENT_BODY = {
    "metadata": {"tag": "t"},
    "indexes": [{"code": "us-epa", "aqi": 46, "aqiDisplay": "46"}],
    "pollutants": [
        {
            "code": "pm2p5",
            "concentration": {"value": 11.0, "unit": "μg/m3"},
        }
    ],
    "stations": [{"id": "P51762", "name": "North Holywood"}],
}


class RecordingCache:
    """记录读写的缓存替身。"""

    def __init__(self) -> None:
        self.gets: list[str] = []
        self.sets: list[tuple[str, bytes, timedelta]] = []
        self.data: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        self.gets.append(key)
        return self.data.get(key)

    def set(self, key: str, data: bytes, ttl: timedelta) -> None:
        self.sets.append((key, data, ttl))
        self.data[key] = data


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


def test_current_requests_coordinate_path_and_lang() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CURRENT_BODY)

    client = make_client(handler)
    service = AirQualityService(client)
    got = service.current(Location(lat=54.99, lon=-1.61), Options(lang=Lang.ZH))

    assert isinstance(got, Current)
    assert seen[0].url.path == "/airquality/v1/current/54.99/-1.61"
    assert seen[0].url.query == b"lang=zh"
    assert got.indexes[0].aqi == 46.0


def test_current_without_options_sends_no_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CURRENT_BODY)

    client = make_client(handler)
    service = AirQualityService(client)
    service.current(Location(lat=39.92, lon=116.41))

    assert seen[0].url.path == "/airquality/v1/current/39.92/116.41"
    assert seen[0].url.query == b""


def test_daily_and_hourly_request_paths() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}, "days": [], "hours": []})

    client = make_client(handler)
    service = AirQualityService(client)
    loc = Location(lat=39.92, lon=116.41)

    daily = service.daily(loc)
    hourly = service.hourly(loc)

    assert isinstance(daily, DailyForecast)
    assert isinstance(hourly, HourlyForecast)
    assert seen[0].url.path == "/airquality/v1/daily/39.92/116.41"
    assert seen[1].url.path == "/airquality/v1/hourly/39.92/116.41"


def test_station_requests_stations_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "metadata": {"tag": "t"},
                "pollutants": [
                    {
                        "code": "pm2p5",
                        "concentration": {"value": 9.5, "unit": "μg/m3"},
                    }
                ],
            },
        )

    client = make_client(handler)
    service = AirQualityService(client)
    got = service.station("P51762")

    assert isinstance(got, StationData)
    assert seen[0].url.path == "/airquality/v1/stations/P51762"
    assert got.pollutants[0].concentration.value == 9.5


def test_station_rejects_empty_id_without_calling_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = AirQualityService(client)

    with pytest.raises(InvalidParameterError):
        service.station("")

    assert calls == []


def test_location_without_coordinates_is_rejected() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = AirQualityService(client)

    with pytest.raises(InvalidLocationError):
        service.current(Location(id="101010100"))

    assert calls == []


@pytest.mark.parametrize(
    ("want", "call"),
    [
        ("qwx:aq:v1:current:39.92,116.41:lang=zh", "current"),
        ("qwx:aq:v1:daily:39.92,116.41", "daily"),
        ("qwx:aq:v1:hourly:39.92,116.41", "hourly"),
    ],
)
def test_cache_keys_are_frozen(want: str, call: str) -> None:
    """缓存键字面量在已发布版本里定死。"""
    doer = RecordingDoer()
    service = AirQualityService(doer)
    loc = Location(lat=39.92, lon=116.41)

    if call == "current":
        service.current(loc, Options(lang=Lang.ZH))
    elif call == "daily":
        service.daily(loc)
    else:
        service.hourly(loc)

    assert doer.requests[-1].cache_key == want


def test_station_cache_key_is_frozen() -> None:
    doer = RecordingDoer()
    service = AirQualityService(doer)

    service.station("P51762", Options(lang=Lang.ZH))

    assert doer.requests[-1].cache_key == "qwx:aq:v1:station:P51762:lang=zh"


def test_endpoints_and_ttls_are_reported() -> None:
    doer = RecordingDoer()
    service = AirQualityService(doer)
    loc = Location(lat=39.92, lon=116.41)

    service.current(loc)
    service.daily(loc)
    service.hourly(loc)
    service.station("P51762")

    current, daily, hourly, station = doer.requests
    assert current.endpoint == EndpointCurrent
    assert current.ttl == timedelta(minutes=30)
    assert daily.endpoint == EndpointDaily
    assert daily.ttl == timedelta(hours=1)
    assert hourly.endpoint == EndpointHourly
    assert hourly.ttl == timedelta(hours=1)
    assert station.endpoint == EndpointStation
    assert station.ttl == timedelta(minutes=30)


def test_endpoint_values_are_frozen() -> None:
    """端点常量的值在已发布版本里定死。"""
    assert EndpointCurrent == Endpoint("airquality/v1/current")
    assert EndpointDaily == Endpoint("airquality/v1/daily")
    assert EndpointHourly == Endpoint("airquality/v1/hourly")
    assert EndpointStation == Endpoint("airquality/v1/stations")


def test_ttl_policy_overrides_default_ttl() -> None:
    """TTLPolicy 按端点匹配时覆盖端点内置的默认时长。"""
    cache = RecordingCache()
    policy = TTLMap({EndpointCurrent: timedelta(seconds=60)})
    client = make_client(
        lambda request: httpx.Response(200, json=CURRENT_BODY),
        cache=cache,
        ttl_policy=policy,
    )
    service = AirQualityService(client)
    service.current(Location(lat=39.92, lon=116.41))

    assert cache.sets[0][2] == timedelta(seconds=60)


def test_cache_hit_does_not_call_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=CURRENT_BODY)

    client = make_client(handler, cache=MemoryCache())
    service = AirQualityService(client)
    loc = Location(lat=39.92, lon=116.41)

    first = service.current(loc, Options(lang=Lang.ZH))
    second = service.current(loc, Options(lang=Lang.ZH))

    assert len(calls) == 1
    assert first.indexes[0].aqi == second.indexes[0].aqi


def test_async_service_mirrors_sync() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CURRENT_BODY)

    async def run() -> Current:
        client = make_async_client(handler)
        service = AsyncAirQualityService(client)
        return await service.current(Location(lat=54.99, lon=-1.61), Options(lang=Lang.ZH))

    got = asyncio.run(run())

    assert isinstance(got, Current)
    assert seen[0].url.path == "/airquality/v1/current/54.99/-1.61"
    assert seen[0].url.query == b"lang=zh"


def test_async_service_rejects_empty_station_id() -> None:
    async def run() -> None:
        client = make_async_client(lambda request: httpx.Response(200, json={}))
        service = AsyncAirQualityService(client)
        await service.station("")

    with pytest.raises(InvalidParameterError):
        asyncio.run(run())
