"""v1/weather 的服务客户端：路径、查询参数、缓存键与校验。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest

from qwx import APIKeyAuth, AsyncClient, Client, Lang, Location
from qwx.cache import MemoryCache
from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.request import Request
from qwx.ttl import Endpoint
from qwx.v1.weather.client import AsyncWeatherService, WeatherService
from qwx.v1.weather.types import (
    EndpointCurrent,
    EndpointDaily,
    EndpointHourly,
    Options,
)

LOC = Location(lat=39.92, lon=116.41)


class RecordingDoer:
    """记录请求的替身。"""

    def __init__(self) -> None:
        self.requests: list[Request] = []

    def do(self, request: Request) -> Any:
        self.requests.append(request)
        if request.out is None:
            return b"{}"
        return request.out.model_validate({})


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


def test_current_sends_latitude_first() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}})

    service = WeatherService(make_client(handler))
    service.current(LOC, Options(lang=Lang.ZH, local_time=True))

    assert seen[0].url.path == "/weather/v1/current/39.92/116.41"
    assert seen[0].url.query.decode() == "lang=zh&localTime=true"


def test_current_without_options_sends_no_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}})

    service = WeatherService(make_client(handler))
    service.current(LOC)

    assert seen[0].url.path == "/weather/v1/current/39.92/116.41"
    assert seen[0].url.query == b""


def test_hourly_sends_hours() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}, "hours": []})

    service = WeatherService(make_client(handler))
    service.hourly(LOC, 24)

    assert seen[0].url.path == "/weather/v1/hourly/39.92/116.41"
    assert seen[0].url.query.decode() == "hours=24"


def test_daily_sends_days() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}, "days": []})

    service = WeatherService(make_client(handler))
    service.daily(LOC, 7)

    assert seen[0].url.path == "/weather/v1/daily/39.92/116.41"
    assert seen[0].url.query.decode() == "days=7"


def test_cache_keys_are_frozen() -> None:
    doer = RecordingDoer()
    service = WeatherService(doer)

    service.current(LOC, Options(lang=Lang.ZH, local_time=True))
    assert doer.requests[-1].cache_key == "qwx:v1:current:39.92,116.41:lang=zh:localTime=1"

    # 没有可选参数时键里不留后缀。
    service.current(LOC)
    assert doer.requests[-1].cache_key == "qwx:v1:current:39.92,116.41"

    service.hourly(LOC, 24)
    assert doer.requests[-1].cache_key == "qwx:v1:hourly:39.92,116.41:h24"

    service.daily(LOC, 7)
    assert doer.requests[-1].cache_key == "qwx:v1:daily:39.92,116.41:d7"

    service.hourly(LOC, 24, Options(lang=Lang.ZH))
    assert doer.requests[-1].cache_key == "qwx:v1:hourly:39.92,116.41:h24:lang=zh"

    service.daily(LOC, 3, Options(local_time=True))
    assert doer.requests[-1].cache_key == "qwx:v1:daily:39.92,116.41:d3:localTime=1"


def test_cache_key_separates_affecting_params() -> None:
    doer = RecordingDoer()
    service = WeatherService(doer)

    keys = set()
    for opts in (
        Options(lang=Lang.ZH),
        Options(lang=Lang.EN),
        Options(lang=Lang.ZH, local_time=True),
    ):
        service.current(LOC, opts)
        keys.add(doer.requests[-1].cache_key)
    assert len(keys) == 3

    hourly_keys = set()
    for hours in (24, 48):
        service.hourly(LOC, hours)
        hourly_keys.add(doer.requests[-1].cache_key)
    assert len(hourly_keys) == 2


def test_endpoint_and_ttl_are_reported() -> None:
    doer = RecordingDoer()
    service = WeatherService(doer)

    service.current(LOC)
    assert doer.requests[-1].endpoint == EndpointCurrent
    assert doer.requests[-1].ttl == timedelta(seconds=600)

    service.hourly(LOC, 24)
    assert doer.requests[-1].endpoint == EndpointHourly
    assert doer.requests[-1].ttl == timedelta(seconds=3600)

    service.daily(LOC, 3)
    assert doer.requests[-1].endpoint == EndpointDaily
    assert doer.requests[-1].ttl == timedelta(seconds=3600)


def test_endpoint_constants_are_frozen() -> None:
    assert EndpointCurrent == Endpoint("weather/v1/current")
    assert EndpointHourly == Endpoint("weather/v1/hourly")
    assert EndpointDaily == Endpoint("weather/v1/daily")


def test_hourly_rejects_out_of_range() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = WeatherService(make_client(handler))

    for hours in (0, -1, 241):
        with pytest.raises(InvalidParameterError):
            service.hourly(LOC, hours)
    assert calls == []


def test_daily_rejects_out_of_range() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = WeatherService(make_client(handler))

    for days in (0, -1, 11):
        with pytest.raises(InvalidParameterError):
            service.daily(LOC, days)
    assert calls == []


def test_location_id_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = WeatherService(make_client(handler))

    with pytest.raises(InvalidLocationError):
        service.current(Location(id="101010100"))
    with pytest.raises(InvalidLocationError):
        service.hourly(Location(id="101010100"), 24)
    with pytest.raises(InvalidLocationError):
        service.daily(Location(id="101010100"), 3)
    assert calls == []


def test_invalid_lang_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = WeatherService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.current(LOC, Options(lang=Lang("中文", "zh hans")))
    assert calls == []


def test_cache_hit_does_not_reach_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}})

    service = WeatherService(make_client(handler, cache=MemoryCache()))
    service.current(LOC, Options(lang=Lang.ZH))
    service.current(LOC, Options(lang=Lang.ZH))

    assert len(calls) == 1


def test_different_langs_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}})

    service = WeatherService(make_client(handler, cache=MemoryCache()))
    service.current(LOC, Options(lang=Lang.ZH))
    service.current(LOC, Options(lang=Lang.EN))

    assert len(calls) == 2


def test_different_hours_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"metadata": {"tag": "t"}, "hours": []})

    service = WeatherService(make_client(handler, cache=MemoryCache()))
    service.hourly(LOC, 24)
    service.hourly(LOC, 48)

    assert len(calls) == 2


def test_async_service_returns_the_same_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"metadata": {"tag": "t"}})

    service = AsyncWeatherService(make_async_client(handler))

    async def run() -> Any:
        return await service.current(LOC, Options(lang=Lang.ZH))

    got = asyncio.run(run())
    assert got.metadata.tag == "t"
