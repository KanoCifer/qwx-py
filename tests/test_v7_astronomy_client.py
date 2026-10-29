"""v7/astronomy 的服务客户端：请求路径、查询参数、缓存键与校验。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest

from qwx import APIKeyAuth, AsyncClient, Client
from qwx.cache import MemoryCache
from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.lang import Lang
from qwx.location import Location
from qwx.request import Request
from qwx.ttl import Endpoint
from qwx.v7.astronomy.client import AstronomyService, AsyncAstronomyService
from qwx.v7.astronomy.types import (
    EndpointAngle,
    EndpointMoon,
    EndpointSun,
    Options,
)

LOC = Location(lat=39.92, lon=116.41)

SUN_BODY = {
    "code": "200",
    "updateTime": "2026-05-31T02:00+08:00",
    "sunrise": "05:12",
    "sunset": "19:24",
}

MOON_BODY = {
    "code": "200",
    "moonrise": "20:11",
    "moonset": "06:12",
    "moonPhase": [{"fxTime": "2026-05-31T20:00+08:00", "value": "1", "name": "新月"}],
}

ANGLE_BODY = {
    "code": "200",
    "solarElevationAngle": "35.42",
    "solarAzimuthAngle": "196.31",
    "solarHour": "1102",
    "hourAngle": "-12.55",
}


class RecordingDoer:
    """记录请求的替身。"""

    def __init__(self) -> None:
        self.requests: list[Request] = []

    def do(self, request: Request) -> Any:
        self.requests.append(request)
        if request.out is None:
            return b"{}"
        return request.out.model_validate({})

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


def test_sun_sends_location_and_date() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SUN_BODY)

    service = AstronomyService(make_client(handler))
    got = service.sun(LOC, "20260531")

    assert seen[0].url.path == "/v7/astronomy/sun"
    assert seen[0].url.params["location"] == "116.41,39.92"
    assert seen[0].url.params["date"] == "20260531"
    assert got.sunrise == "05:12"
    assert got.sunset == "19:24"


def test_sun_accepts_location_id() -> None:
    """上游这个参数认 LocationID。"""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SUN_BODY)

    service = AstronomyService(make_client(handler))
    service.sun(Location(id="101010100"), "20260531")

    assert seen[0].url.params["location"] == "101010100"


def test_sun_has_no_language_parameter() -> None:
    """日出日落端点不带语言。"""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SUN_BODY)

    service = AstronomyService(make_client(handler))
    service.sun(LOC, "20260531")

    assert "lang" not in seen[0].url.params


def test_moon_sends_location_date_and_lang() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=MOON_BODY)

    service = AstronomyService(make_client(handler))
    got = service.moon(LOC, "20260531", Options(lang=Lang.ZH))

    assert seen[0].url.path == "/v7/astronomy/moon"
    assert seen[0].url.params["location"] == "116.41,39.92"
    assert seen[0].url.params["date"] == "20260531"
    assert seen[0].url.params["lang"] == "zh"
    assert got.moonrise == "20:11"
    assert got.moon_phase[0].name == "新月"


def test_moon_without_lang_sends_no_lang() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=MOON_BODY)

    service = AstronomyService(make_client(handler))
    service.moon(LOC, "20260531")

    assert "lang" not in seen[0].url.params


def test_solar_elevation_angle_sends_all_parameters() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ANGLE_BODY)

    service = AstronomyService(make_client(handler))
    got = service.solar_elevation_angle(LOC, "20260531", "1200", "0800", 43)

    assert seen[0].url.path == "/v7/astronomy/solar-elevation-angle"
    assert seen[0].url.params["location"] == "116.41,39.92"
    assert seen[0].url.params["date"] == "20260531"
    assert seen[0].url.params["time"] == "1200"
    assert seen[0].url.params["tz"] == "0800"
    assert seen[0].url.params["alt"] == "43"
    assert got.solar_elevation_angle == "35.42"
    assert got.solar_hour == "1102"


def test_solar_elevation_angle_accepts_negative_timezone() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ANGLE_BODY)

    service = AstronomyService(make_client(handler))
    service.solar_elevation_angle(LOC, "20260531", "1200", "-0530", 43)

    assert seen[0].url.params["tz"] == "-0530"


def test_cache_keys_are_frozen() -> None:
    """缓存键字面量在已发布版本里定死。"""
    doer = RecordingDoer()
    service = AstronomyService(doer)

    service.sun(LOC, "20260531")
    assert doer.requests[-1].cache_key == "qwx:astronomy:sun:116.41,39.92:20260531"

    service.moon(LOC, "20260531", Options(lang=Lang.ZH))
    assert doer.requests[-1].cache_key == "qwx:astronomy:moon:116.41,39.92:20260531:lang=zh"

    service.moon(LOC, "20260531")
    assert doer.requests[-1].cache_key == "qwx:astronomy:moon:116.41,39.92:20260531"

    service.solar_elevation_angle(LOC, "20260531", "1200", "0800", 43)
    assert doer.requests[-1].cache_key == "qwx:astronomy:angle:116.41,39.92:20260531:1200:0800:43"


def test_cache_key_uses_location_id_for_sun() -> None:
    doer = RecordingDoer()
    service = AstronomyService(doer)

    service.sun(Location(id="101010100"), "20260531")

    assert doer.requests[-1].cache_key == "qwx:astronomy:sun:101010100:20260531"


def test_cache_key_separates_affecting_params() -> None:
    """影响结果的参数各产生不同的键，共键就是串味。"""
    doer = RecordingDoer()
    service = AstronomyService(doer)

    sun_keys = set()
    for date in ("20260531", "20260601"):
        service.sun(LOC, date)
        sun_keys.add(doer.requests[-1].cache_key)
    assert len(sun_keys) == 2

    moon_keys = set()
    for lang in (Lang.UNSPECIFIED, Lang.ZH, Lang.EN):
        service.moon(LOC, "20260531", Options(lang=lang))
        moon_keys.add(doer.requests[-1].cache_key)
    assert len(moon_keys) == 3

    angle_keys = set()
    for time_str in ("1200", "1800"):
        service.solar_elevation_angle(LOC, "20260531", time_str, "0800", 43)
        angle_keys.add(doer.requests[-1].cache_key)
    assert len(angle_keys) == 2

    tz_keys = set()
    for tz in ("0800", "-0530"):
        service.solar_elevation_angle(LOC, "20260531", "0900", tz, 43)
        tz_keys.add(doer.requests[-1].cache_key)
    assert len(tz_keys) == 2

    alt_keys = set()
    for alt in (0, 43):
        service.solar_elevation_angle(LOC, "20260531", "2100", "0800", alt)
        alt_keys.add(doer.requests[-1].cache_key)
    assert len(alt_keys) == 2


def test_endpoint_and_ttl_are_reported() -> None:
    doer = RecordingDoer()
    service = AstronomyService(doer)

    service.sun(LOC, "20260531")
    assert doer.requests[-1].endpoint == EndpointSun
    assert doer.requests[-1].ttl == timedelta(seconds=86400)

    service.moon(LOC, "20260531")
    assert doer.requests[-1].endpoint == EndpointMoon
    assert doer.requests[-1].ttl == timedelta(seconds=86400)

    service.solar_elevation_angle(LOC, "20260531", "1200", "0800", 43)
    assert doer.requests[-1].endpoint == EndpointAngle
    assert doer.requests[-1].ttl == timedelta(seconds=86400)


def test_endpoint_constants_are_frozen() -> None:
    assert EndpointSun == Endpoint("v7/astronomy/sun")
    assert EndpointMoon == Endpoint("v7/astronomy/moon")
    assert EndpointAngle == Endpoint("v7/astronomy/solar-elevation-angle")


def test_bad_date_is_rejected_without_reaching_upstream() -> None:
    """客户端只校验格式，日期范围交给上游。"""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = AstronomyService(make_client(handler))

    for date in ("", "2026-05-31", "2026053", "202605311", "20260230", "20261345"):
        with pytest.raises(InvalidParameterError):
            service.sun(LOC, date)
        with pytest.raises(InvalidParameterError):
            service.moon(LOC, date)
        with pytest.raises(InvalidParameterError):
            service.solar_elevation_angle(LOC, date, "1200", "0800", 43)
    assert calls == []


def test_bad_time_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = AstronomyService(make_client(handler))

    for time_str in ("", "120", "12000", "2400", "1260", "abcd"):
        with pytest.raises(InvalidParameterError):
            service.solar_elevation_angle(LOC, "20260531", time_str, "0800", 43)
    assert calls == []


def test_bad_timezone_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = AstronomyService(make_client(handler))

    for tz in ("", "080", "08000", "0800x", "1500", "-1400", "0890"):
        with pytest.raises(InvalidParameterError):
            service.solar_elevation_angle(LOC, "20260531", "1200", tz, 43)
    assert calls == []


def test_negative_altitude_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = AstronomyService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.solar_elevation_angle(LOC, "20260531", "1200", "0800", -1)
    assert calls == []


def test_unsupported_location_form_is_rejected_without_reaching_upstream() -> None:
    """上游不认地名；太阳高度角端点连 LocationID 都不认。"""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = AstronomyService(make_client(handler))

    for loc in (Location(name="北京"), Location()):
        with pytest.raises(InvalidLocationError):
            service.sun(loc, "20260531")
        with pytest.raises(InvalidLocationError):
            service.moon(loc, "20260531")

    with pytest.raises(InvalidLocationError):
        service.solar_elevation_angle(Location(id="101010100"), "20260531", "1200", "0800", 43)
    assert calls == []


def test_invalid_lang_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = AstronomyService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.moon(LOC, "20260531", Options(lang=Lang("中文", "zh hans")))
    assert calls == []


def test_cache_hit_does_not_reach_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=SUN_BODY)

    service = AstronomyService(make_client(handler, cache=MemoryCache()))
    first = service.sun(LOC, "20260531")
    second = service.sun(LOC, "20260531")

    assert len(calls) == 1
    assert first.sunrise == second.sunrise


def test_different_dates_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=SUN_BODY)

    service = AstronomyService(make_client(handler, cache=MemoryCache()))
    service.sun(LOC, "20260531")
    service.sun(LOC, "20260601")

    assert len(calls) == 2


def test_async_service_returns_the_same_models() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SUN_BODY)

    service = AsyncAstronomyService(make_async_client(handler))

    async def run() -> Any:
        return await service.sun(LOC, "20260531")

    got = asyncio.run(run())

    assert got.sunrise == "05:12"
    assert seen[0].url.path == "/v7/astronomy/sun"
    assert seen[0].url.params["location"] == "116.41,39.92"


def test_async_service_rejects_bad_date() -> None:
    async def run() -> None:
        service = AsyncAstronomyService(
            make_async_client(lambda request: httpx.Response(200, json={}))
        )
        await service.sun(LOC, "2026053")

    with pytest.raises(InvalidParameterError):
        asyncio.run(run())
