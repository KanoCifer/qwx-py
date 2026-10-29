"""v7/ocean 的服务客户端：路径、查询参数、缓存键与校验。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest

from qwx import APIKeyAuth, AsyncClient, Client
from qwx.cache import MemoryCache
from qwx.errors import InvalidParameterError
from qwx.request import Request
from qwx.ttl import Endpoint
from qwx.v7.ocean.client import AsyncOceanService, OceanService

BODY = {
    "code": "200",
    "updateTime": "2021-02-04T05:02+08:00",
    "tideTable": [{"fxTime": "2021-02-06T03:48+08:00", "height": "2.17", "type": "H"}],
    "tideHourly": [{"fxTime": "2021-02-06T00:00+08:00", "height": "1.02"}],
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


def test_tide_sends_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = OceanService(make_client(handler))
    service.tide("P2352", "20210206")

    assert seen[0].url.path == "/v7/ocean/tide"
    # 位置形态是潮汐站 ID，不是坐标。
    assert seen[0].url.params["location"] == "P2352"
    assert seen[0].url.params["date"] == "20210206"


def test_tide_parses_the_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = OceanService(make_client(handler))
    got = service.tide("P2352", "20210206")

    assert len(got.tide_table) == 1
    assert got.tide_table[0].type == "H"
    # 高度保持字符串，保留上游的小数位表达。
    assert got.tide_table[0].height == "2.17"
    assert len(got.tide_hourly) == 1
    assert got.refer.license == ["QWeather Developers License"]


def test_cache_key_is_frozen() -> None:
    doer = RecordingDoer()
    service = OceanService(doer)

    service.tide("P2352", "20260101")
    # 键前缀是 qwx:tide:（不是 qwx:ocean:）—— 已发布字面量不可改。
    assert doer.requests[-1].cache_key == "qwx:tide:P2352:20260101"


def test_endpoint_and_ttl_are_reported() -> None:
    doer = RecordingDoer()
    service = OceanService(doer)

    service.tide("P2352", "20260101")
    assert doer.requests[-1].endpoint == Endpoint("v7/ocean/tide")
    assert doer.requests[-1].ttl == timedelta(seconds=3600)


def test_empty_station_id_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = OceanService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.tide("", "20210206")
    assert calls == []


def test_eight_digit_date_is_passed_through_to_upstream() -> None:
    # 与 Go 版一致：只校验 8 位数字，日历合法性由上游判。
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = OceanService(make_client(handler))
    service.tide("P2352", "20211301")
    assert len(calls) == 1
    assert calls[0].url.params["date"] == "20211301"


def test_invalid_date_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = OceanService(make_client(handler))

    # 只校验 8 位数字，不校验日历合法性：非法日历日（如 20211301）交给上游回 400。
    for date in ("", "2021-02-06", "2021020", "202102061", "2021023 "):
        with pytest.raises(InvalidParameterError):
            service.tide("P2352", date)
    assert calls == []


def test_cache_hit_does_not_reach_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = OceanService(make_client(handler, cache=MemoryCache()))
    service.tide("P2352", "20210206")
    service.tide("P2352", "20210206")

    assert len(calls) == 1


def test_different_dates_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = OceanService(make_client(handler, cache=MemoryCache()))
    service.tide("P2352", "20210206")
    service.tide("P2352", "20210207")

    assert len(calls) == 2


def test_async_service_returns_the_same_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = AsyncOceanService(make_async_client(handler))

    async def run() -> Any:
        return await service.tide("P2352", "20210206")

    got = asyncio.run(run())
    assert got.tide_table[0].height == "2.17"
