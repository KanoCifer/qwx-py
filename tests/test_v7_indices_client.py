"""v7/indices 的服务客户端：路径、查询参数、缓存键与校验。"""

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
from qwx.v7.indices.client import AsyncIndicesService, IndicesService
from qwx.v7.indices.types import MAX_TYPE, TYPE_ALL, TYPE_FISHING

LOC = Location(lat=39.92, lon=116.41)

BODY = {
    "code": "200",
    "updateTime": "2021-12-16T18:35+08:00",
    "daily": [
        {
            "date": "2021-12-16",
            "type": "1",
            "name": "运动指数",
            "level": "3",
            "category": "较不宜",
            "text": "天气较好，但考虑天气寒冷。",
        },
        {
            "date": "2021-12-16",
            "type": "4",
            "name": "钓鱼指数",
            "level": "2",
            "category": "适宜",
            "text": "",
        },
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


def test_indices_sends_path_and_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = IndicesService(make_client(handler))
    service.indices(LOC, TYPE_FISHING, 1)

    assert seen[0].url.path == "/v7/indices/1d"
    # v7 的位置形态是经度在前。
    assert seen[0].url.params["location"] == "116.41,39.92"
    assert seen[0].url.params["type"] == "4"
    assert "lang" not in seen[0].url.params


def test_indices_sends_lang() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = IndicesService(make_client(handler))
    service.indices(LOC, TYPE_ALL, 3, Lang.ZH)

    assert seen[0].url.path == "/v7/indices/3d"
    assert seen[0].url.params["lang"] == "zh"
    assert seen[0].url.params["type"] == "0"


def test_indices_parses_the_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = IndicesService(make_client(handler))
    got = service.indices(LOC, TYPE_FISHING, 1)

    assert got.code == "200"
    assert len(got.daily) == 2
    # level 上游给的是字符串。
    assert got.daily[0].level == "3"
    assert got.daily[1].name == "钓鱼指数"
    assert got.refer.license == ["QWeather Developers License"]


def test_indices_multi_sends_comma_separated_types() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = IndicesService(make_client(handler))
    service.indices_multi(LOC, [3, 4], 1, Lang.ZH)

    assert seen[0].url.path == "/v7/indices/1d"
    assert seen[0].url.params["type"] == "3,4"
    assert seen[0].url.params["location"] == "116.41,39.92"


def test_cache_keys_are_frozen() -> None:
    doer = RecordingDoer()
    service = IndicesService(doer)

    service.indices(LOC, TYPE_ALL, 3, Lang.ZH)
    assert doer.requests[-1].cache_key == "qwx:indices:116.41,39.92:t0:d3:lang=zh"

    service.indices(LOC, TYPE_FISHING, 1)
    assert doer.requests[-1].cache_key == "qwx:indices:116.41,39.92:t4:d1"

    # 多种类型的键用逗号连接，单类型时与单类型调用完全一致。
    service.indices_multi(LOC, [3, 4], 1, Lang.ZH)
    assert doer.requests[-1].cache_key == "qwx:indices:116.41,39.92:t3,4:d1:lang=zh"

    service.indices_multi(LOC, [3], 1, Lang.ZH)
    assert doer.requests[-1].cache_key == "qwx:indices:116.41,39.92:t3:d1:lang=zh"


def test_endpoint_and_ttl_are_reported() -> None:
    doer = RecordingDoer()
    service = IndicesService(doer)

    service.indices(LOC, TYPE_ALL, 3, Lang.ZH)
    assert doer.requests[-1].endpoint == Endpoint("v7/indices")
    assert doer.requests[-1].ttl == timedelta(seconds=3600)


def test_unsupported_days_are_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = IndicesService(make_client(handler))

    # 上游只认 1d 与 3d，其余天数码 404。
    for days in (0, 2, 7, 10, 15, 30):
        with pytest.raises(InvalidParameterError):
            service.indices(LOC, TYPE_ALL, days)
    assert calls == []


def test_out_of_range_types_are_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = IndicesService(make_client(handler))

    for typ in (-1, MAX_TYPE + 1):
        with pytest.raises(InvalidParameterError):
            service.indices(LOC, typ, 1)
    with pytest.raises(InvalidParameterError):
        service.indices_multi(LOC, [3, MAX_TYPE + 1], 1)
    assert calls == []


def test_type_all_cannot_be_combined_with_other_types() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = IndicesService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.indices_multi(LOC, [TYPE_ALL, 3], 1)
    assert calls == []


def test_empty_type_list_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = IndicesService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.indices_multi(LOC, [], 1)
    assert calls == []


def test_missing_coordinates_are_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = IndicesService(make_client(handler))

    # 上游只认坐标对，裸经度与 LocationID 都不接受。
    for loc in (Location(id="101010100"), Location(name="北京"), Location()):
        with pytest.raises(InvalidLocationError):
            service.indices(loc, TYPE_ALL, 1)
        with pytest.raises(InvalidLocationError):
            service.indices_multi(loc, [3], 1)
    assert calls == []


def test_invalid_lang_is_rejected_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = IndicesService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.indices(LOC, TYPE_ALL, 1, Lang("中文", "zh hans"))
    assert calls == []


def test_cache_hit_does_not_reach_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = IndicesService(make_client(handler, cache=MemoryCache()))
    service.indices(LOC, TYPE_ALL, 3, Lang.ZH)
    service.indices(LOC, TYPE_ALL, 3, Lang.ZH)

    assert len(calls) == 1


def test_different_types_and_days_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = IndicesService(make_client(handler, cache=MemoryCache()))
    service.indices(LOC, TYPE_ALL, 3, Lang.ZH)
    service.indices(LOC, TYPE_FISHING, 3, Lang.ZH)
    service.indices(LOC, TYPE_ALL, 1, Lang.ZH)
    service.indices(LOC, TYPE_ALL, 3, Lang.EN)

    assert len(calls) == 4


def test_async_service_returns_the_same_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = AsyncIndicesService(make_async_client(handler))

    async def run() -> Any:
        return await service.indices_multi(LOC, [3, 4], 1, Lang.ZH)

    got = asyncio.run(run())
    assert len(got.daily) == 2
