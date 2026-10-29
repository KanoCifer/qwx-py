"""v7/historical 的服务客户端：路径、查询参数、缓存键与校验。"""

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
from qwx.v7.historical.client import AsyncHistoricalService, HistoricalService
from qwx.v7.historical.types import Options

LOC = Location(id="101010100")

BODY = {
    "code": "200",
    "fxLink": "https://www.qweather.com",
    "weatherDaily": {"date": "2020-07-25", "tempMax": "33", "tempMin": "23"},
    "weatherHourly": [{"time": "2020-07-25 21:00", "temp": "29"}],
    "refer": {
        "sources": ["https://developer.qweather.com/attribution.html"],
        "license": ["QWeather Developers License"],
    },
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


def test_weather_sends_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = HistoricalService(make_client(handler))
    service.weather(LOC, "20200725", Options(lang=Lang.ZH))

    assert seen[0].url.path == "/v7/historical/weather"
    query = seen[0].url.params
    assert query["location"] == "101010100"
    assert query["date"] == "20200725"
    assert query["lang"] == "zh"


def test_weather_without_options_sends_no_lang() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = HistoricalService(make_client(handler))
    service.weather(LOC, "20200725")

    query = seen[0].url.params
    assert query["location"] == "101010100"
    assert query["date"] == "20200725"
    assert "lang" not in query


def test_weather_parses_the_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = HistoricalService(make_client(handler))
    got = service.weather(LOC, "20200725")

    assert got.code == "200"
    assert got.daily is not None
    assert got.daily.date == "2020-07-25"
    assert len(got.hourly) == 1
    assert got.refer.license == ["QWeather Developers License"]


def test_cache_keys_are_frozen() -> None:
    doer = RecordingDoer()
    service = HistoricalService(doer)

    service.weather(LOC, "20200725")
    assert doer.requests[-1].cache_key == "qwx:historical:weather:101010100:20200725"

    service.weather(LOC, "20200725", Options(lang=Lang.EN))
    assert doer.requests[-1].cache_key == "qwx:historical:weather:101010100:20200725:lang=en"

    # 换一个日期是另一份数据。
    service.weather(LOC, "20200726")
    assert doer.requests[-1].cache_key == "qwx:historical:weather:101010100:20200726"


def test_endpoint_and_ttl_are_reported() -> None:
    doer = RecordingDoer()
    service = HistoricalService(doer)

    service.weather(LOC, "20200725")
    assert doer.requests[-1].endpoint == Endpoint("v7/historical/weather")
    assert doer.requests[-1].ttl == timedelta(seconds=86400)


def test_non_location_id_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = HistoricalService(make_client(handler))

    # 上游只认 LocationID，坐标对与地名都被拒。
    for loc in (
        Location(lat=39.92, lon=116.41),
        Location(name="北京"),
        Location(),
    ):
        with pytest.raises(InvalidLocationError):
            service.weather(loc, "20200725")
    assert calls == []


def test_invalid_date_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = HistoricalService(make_client(handler))

    for date in ("", "2020-07-25", "2020072", "202007255", "20201301", "20200230", "2020abcd"):
        with pytest.raises(InvalidParameterError):
            service.weather(LOC, date)
    assert calls == []


def test_invalid_lang_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = HistoricalService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.weather(LOC, "20200725", Options(lang=Lang("中文", "zh hans")))
    assert calls == []


def test_cache_hit_does_not_reach_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = HistoricalService(make_client(handler, cache=MemoryCache()))
    service.weather(LOC, "20200725", Options(lang=Lang.ZH))
    service.weather(LOC, "20200725", Options(lang=Lang.ZH))

    assert len(calls) == 1


def test_different_langs_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = HistoricalService(make_client(handler, cache=MemoryCache()))
    service.weather(LOC, "20200725", Options(lang=Lang.ZH))
    service.weather(LOC, "20200725", Options(lang=Lang.EN))

    assert len(calls) == 2


def test_async_service_returns_the_same_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = AsyncHistoricalService(make_async_client(handler))

    async def run() -> Any:
        return await service.weather(LOC, "20200725", Options(lang=Lang.ZH))

    got = asyncio.run(run())
    assert got.daily is not None
    assert got.daily.date == "2020-07-25"
