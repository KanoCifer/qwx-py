"""v7/minutely 的服务客户端：路径、查询参数、缓存键与校验。"""

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
from qwx.v7.minutely.client import AsyncMinutelyService, MinutelyService

LOC = Location(lat=39.92, lon=116.41)

BODY = {
    "code": "200",
    "updateTime": "2021-12-16T18:55+08:00",
    "summary": "95分钟后雨就停了",
    "minutely": [
        {"fxTime": "2021-12-16T18:55+08:00", "precip": "0.00", "type": "rain"},
        {"fxTime": "2021-12-16T19:00+08:00", "precip": "0.15", "type": "rain"},
    ],
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


def test_minutely_sends_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = MinutelyService(make_client(handler))
    service.minutely(LOC)

    assert seen[0].url.path == "/v7/minutely/5m"
    # v7 的位置形态是经度在前。
    assert seen[0].url.params["location"] == "116.41,39.92"
    assert "lang" not in seen[0].url.params


def test_minutely_sends_lang() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = MinutelyService(make_client(handler))
    service.minutely(LOC, Lang.ZH)

    assert seen[0].url.params["lang"] == "zh"


def test_minutely_parses_the_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = MinutelyService(make_client(handler))
    got = service.minutely(LOC)

    assert got.summary == "95分钟后雨就停了"
    assert len(got.minutely) == 2
    # precip 保持字符串：空串与 "0.00" 含义不同。
    assert got.minutely[0].precip == "0.00"
    assert got.refer.license == ["QWeather Developers License"]


def test_cache_keys_are_frozen() -> None:
    doer = RecordingDoer()
    service = MinutelyService(doer)

    service.minutely(LOC)
    assert doer.requests[-1].cache_key == "qwx:minutely:116.41,39.92"

    service.minutely(LOC, Lang.ZH)
    assert doer.requests[-1].cache_key == "qwx:minutely:116.41,39.92:lang=zh"


def test_endpoint_and_ttl_are_reported() -> None:
    doer = RecordingDoer()
    service = MinutelyService(doer)

    service.minutely(LOC, Lang.ZH)
    assert doer.requests[-1].endpoint == Endpoint("v7/minutely/5m")
    assert doer.requests[-1].ttl == timedelta(seconds=300)


def test_missing_coordinates_are_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = MinutelyService(make_client(handler))

    # 上游只认坐标，LocationID 与地名都不接受。
    for loc in (Location(id="101010100"), Location(name="北京"), Location()):
        with pytest.raises(InvalidLocationError):
            service.minutely(loc)
    assert calls == []


def test_invalid_lang_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = MinutelyService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.minutely(LOC, Lang("中文", "zh hans"))
    assert calls == []


def test_cache_hit_does_not_reach_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = MinutelyService(make_client(handler, cache=MemoryCache()))
    service.minutely(LOC, Lang.ZH)
    service.minutely(LOC, Lang.ZH)

    assert len(calls) == 1


def test_different_langs_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = MinutelyService(make_client(handler, cache=MemoryCache()))
    service.minutely(LOC, Lang.ZH)
    service.minutely(LOC, Lang.EN)

    assert len(calls) == 2


def test_async_service_returns_the_same_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = AsyncMinutelyService(make_async_client(handler))

    async def run() -> Any:
        return await service.minutely(LOC, Lang.ZH)

    got = asyncio.run(run())
    assert got.summary == "95分钟后雨就停了"
