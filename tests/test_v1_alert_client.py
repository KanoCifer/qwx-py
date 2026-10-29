"""预警接口的服务客户端。"""

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
from qwx.v1.alert.client import AlertService, AsyncAlertService
from qwx.v1.alert.types import Result
from qwx.v1.types import Options

BODY = {
    "metadata": {"tag": "t", "zeroResult": False},
    "alerts": [
        {
            "id": "202510241119105837988676",
            "senderName": "临桂区气象台",
            "messageType": {"code": "update", "supersedes": []},
            "eventType": {"name": "大风", "code": "1006"},
            "color": {"code": "blue", "red": 30, "green": 50, "blue": 205, "alpha": 1},
        }
    ],
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


def test_current_requests_the_coordinate_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler))
    result = service.current(
        Location(lat=25.42, lon=110.29),
        Options(lang=Lang.ZH, local_time=True),
    )
    assert isinstance(result, Result)
    assert seen[0].url.path == "/weatheralert/v1/current/25.42/110.29"
    assert seen[0].url.query.decode() == "lang=zh&localTime=true"
    assert len(result.alerts) == 1
    assert result.alerts[0].event_type.code == "1006"


def test_current_without_options_sends_no_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler))
    service.current(Location(lat=39.92, lon=116.41))
    assert seen[0].url.query.decode() == ""


def test_cache_key_is_frozen() -> None:
    """缓存键字面量在已发布版本里定死。

    改了会让已写入的缓存条目全部失效，也和 Go 版共享 Redis 时互相覆盖。
    """
    cache = RecordingCache()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler, cache=cache))
    service.current(
        Location(lat=39.92, lon=116.41),
        Options(lang=Lang.ZH, local_time=True),
    )
    assert cache.gets == ["qwx:alert:v1:39.92,116.41:lang=zh:localTime=1"]
    assert cache.sets[0][0] == "qwx:alert:v1:39.92,116.41:lang=zh:localTime=1"


def test_cache_key_without_parameters() -> None:
    cache = RecordingCache()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler, cache=cache))
    service.current(Location(lat=39.92, lon=116.41))
    assert cache.gets == ["qwx:alert:v1:39.92,116.41"]


def test_default_ttl_is_five_minutes() -> None:
    cache = RecordingCache()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler, cache=cache))
    service.current(Location(lat=39.92, lon=116.41))
    assert cache.sets[0][2] == timedelta(minutes=5)


def test_cache_hit_does_not_call_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler, cache=MemoryCache()))
    loc = Location(lat=39.92, lon=116.41)
    first = service.current(loc)
    second = service.current(loc)
    assert len(calls) == 1
    assert first.alerts[0].id == second.alerts[0].id


def test_location_without_coordinates_is_rejected() -> None:
    """这一代只认坐标：LocationID 不打上游，直接报错。"""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler))
    with pytest.raises(InvalidLocationError):
        service.current(Location(id="101010100"))
    assert calls == []


def test_empty_location_is_rejected() -> None:
    service = AlertService(make_client(lambda request: httpx.Response(200, json=BODY)))
    with pytest.raises(InvalidLocationError):
        service.current(Location())


def test_invalid_language_is_rejected_before_the_request() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=BODY)

    service = AlertService(make_client(handler))
    with pytest.raises(InvalidParameterError):
        service.current(Location(lat=39.92, lon=116.41), Options(lang=Lang("坏语言", "bad code")))
    assert calls == []


def test_async_service_shares_the_same_behavior() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=BODY)

    service = AsyncAlertService(make_async_client(handler))

    async def run() -> Result:
        return await service.current(
            Location(lat=25.42, lon=110.29),
            Options(lang=Lang.ZH),
        )

    result = asyncio.run(run())
    assert seen[0].url.path == "/weatheralert/v1/current/25.42/110.29"
    assert seen[0].url.query.decode() == "lang=zh"
    assert result.alerts[0].color.code == "blue"


def test_async_service_rejects_location_without_coordinates() -> None:
    service = AsyncAlertService(make_async_client(lambda request: httpx.Response(200, json=BODY)))

    async def run() -> None:
        await service.current(Location(id="101010100"))

    with pytest.raises(InvalidLocationError):
        asyncio.run(run())
