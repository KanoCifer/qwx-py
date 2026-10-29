"""台风端点族的请求行为。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest

from qwx import APIKeyAuth
from qwx.cache import MemoryCache
from qwx.client import AsyncClient, Client
from qwx.errors import InvalidParameterError
from qwx.request import Request
from qwx.ttl import Endpoint
from qwx.v7.storm import (
    AsyncStormService,
    BasinNP,
    EndpointForecast,
    EndpointList,
    EndpointTrack,
    ForecastResult,
    ListResult,
    StormService,
    TrackResult,
)

LIST_BODY = {
    "code": "200",
    "updateTime": "2020-12-31T16:00+00:00",
    "fxLink": "https://www.qweather.com",
    "storm": [
        {"id": "NP2018", "name": "莫拉菲", "basin": "NP", "year": "2020", "isActive": "0"},
    ],
    "refer": {"sources": ["a"], "license": ["l"]},
}

FORECAST_BODY = {
    "code": "200",
    "updateTime": "2021-07-27T03:00+00:00",
    "forecast": [
        {
            "fxTime": "2021-07-27T20:00+08:00",
            "lat": "31.7",
            "lon": "118.4",
            "type": "TS",
            "pressure": "990",
            "windSpeed": "18",
        }
    ],
}

TRACK_BODY = {
    "code": "200",
    "updateTime": "2024-05-30T06:11+00:00",
    "isActive": "1",
    "now": {
        "pubTime": "2024-05-30T05:00+08:00",
        "lat": "27.7",
        "lon": "134.5",
        "type": "STS",
        "pressure": "980",
        "windSpeed": "30",
        "moveDir": "NE",
    },
    "track": [
        {
            "time": "2024-05-29T05:00+08:00",
            "lat": "25.3",
            "lon": "136.1",
            "type": "STS",
        }
    ],
}


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


def test_list_requests_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=LIST_BODY)

    client = make_client(handler)
    service = StormService(client)
    got = service.list(BasinNP, 2020)

    assert isinstance(got, ListResult)
    assert seen[0].url.path == "/v7/tropical/storm-list"
    assert seen[0].url.params["basin"] == "NP"
    assert seen[0].url.params["year"] == "2020"
    assert got.storms[0].id == "NP2018"


def test_forecast_requests_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=FORECAST_BODY)

    client = make_client(handler)
    service = StormService(client)
    got = service.forecast("NP2018")

    assert isinstance(got, ForecastResult)
    assert seen[0].url.path == "/v7/tropical/storm-forecast"
    assert seen[0].url.params["stormid"] == "NP2018"
    assert got.forecast[0].lat == "31.7"


def test_track_requests_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=TRACK_BODY)

    client = make_client(handler)
    service = StormService(client)
    got = service.track("NP2018")

    assert isinstance(got, TrackResult)
    assert seen[0].url.path == "/v7/tropical/storm-track"
    assert seen[0].url.params["stormid"] == "NP2018"
    assert got.now is not None
    assert got.now.pub_time == "2024-05-30T05:00+08:00"
    assert got.track[0].time == "2024-05-29T05:00+08:00"


@pytest.mark.parametrize("basin", ["AL", "EP", "SP", "NI", "SI", "", "np"])
def test_list_rejects_unsupported_basin_without_calling_upstream(basin: str) -> None:
    """上游只支持 NP，其余流域代码客户端就挡掉。"""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = StormService(client)

    with pytest.raises(InvalidParameterError):
        service.list(basin, 2020)

    assert calls == []


@pytest.mark.parametrize("year", [0, -1, -2020])
def test_list_rejects_non_positive_year_without_calling_upstream(year: int) -> None:
    """年份必须是正整数。"""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = StormService(client)

    with pytest.raises(InvalidParameterError):
        service.list(BasinNP, year)

    assert calls == []


def test_forecast_rejects_empty_storm_id_without_calling_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = StormService(client)

    with pytest.raises(InvalidParameterError):
        service.forecast("")

    assert calls == []


def test_track_rejects_empty_storm_id_without_calling_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler)
    service = StormService(client)

    with pytest.raises(InvalidParameterError):
        service.track("")

    assert calls == []


def test_cache_keys_are_frozen() -> None:
    """缓存键字面量在已发布版本里定死。"""
    doer = RecordingDoer()
    service = StormService(doer)

    service.list(BasinNP, 2020)
    assert doer.requests[-1].cache_key == "qwx:storm:list:NP:2020"

    service.forecast("NP2018")
    assert doer.requests[-1].cache_key == "qwx:storm:forecast:NP2018"

    service.track("NP2018")
    assert doer.requests[-1].cache_key == "qwx:storm:track:NP2018"


def test_cache_keys_distinguish_parameters() -> None:
    """影响结果的参数都要进键：共键就是串味。"""
    doer = RecordingDoer()
    service = StormService(doer)

    service.list(BasinNP, 2020)
    service.list(BasinNP, 2021)
    service.forecast("NP2018")
    service.forecast("NP2020")
    service.track("NP2018")
    service.track("NP2020")

    keys = [request.cache_key for request in doer.requests]
    assert len(set(keys)) == 6


def test_endpoints_and_ttls_are_reported() -> None:
    doer = RecordingDoer()
    service = StormService(doer)

    service.list(BasinNP, 2020)
    service.forecast("NP2018")
    service.track("NP2018")

    list_req, forecast_req, track_req = doer.requests
    assert list_req.endpoint == EndpointList
    assert list_req.ttl == timedelta(seconds=86400)
    assert forecast_req.endpoint == EndpointForecast
    assert forecast_req.ttl == timedelta(seconds=3600)
    assert track_req.endpoint == EndpointTrack
    assert track_req.ttl == timedelta(seconds=3600)


def test_endpoint_values_are_frozen() -> None:
    """端点常量的值在已发布版本里定死。"""
    assert EndpointList == Endpoint("v7/tropical/storm-list")
    assert EndpointForecast == Endpoint("v7/tropical/storm-forecast")
    assert EndpointTrack == Endpoint("v7/tropical/storm-track")


def test_cache_hit_does_not_call_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=LIST_BODY)

    client = make_client(handler, cache=MemoryCache())
    service = StormService(client)

    first = service.list(BasinNP, 2020)
    second = service.list(BasinNP, 2020)

    assert len(calls) == 1
    assert first.storms[0].id == second.storms[0].id


def test_forecast_cache_hit_does_not_call_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=FORECAST_BODY)

    client = make_client(handler, cache=MemoryCache())
    service = StormService(client)

    service.forecast("NP2018")
    service.forecast("NP2018")

    assert len(calls) == 1


def test_async_service_mirrors_sync() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=TRACK_BODY)

    async def run() -> TrackResult:
        client = make_async_client(handler)
        service = AsyncStormService(client)
        return await service.track("NP2018")

    got = asyncio.run(run())

    assert isinstance(got, TrackResult)
    assert seen[0].url.path == "/v7/tropical/storm-track"
    assert seen[0].url.params["stormid"] == "NP2018"


def test_async_service_rejects_unsupported_basin() -> None:
    async def run() -> None:
        client = make_async_client(lambda request: httpx.Response(200, json={}))
        service = AsyncStormService(client)
        await service.list("AL", 2020)

    with pytest.raises(InvalidParameterError):
        asyncio.run(run())
