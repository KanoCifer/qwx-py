"""console 的服务客户端：路径、查询参数、缓存键与校验。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import pytest

from qwx import APIKeyAuth, AsyncClient, Client
from qwx.cache import MemoryCache
from qwx.console.client import AsyncConsoleService, ConsoleService
from qwx.console.types import EndpointFinance, EndpointStats, StatsOptions
from qwx.errors import InvalidParameterError
from qwx.request import Request
from qwx.ttl import Endpoint


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


def test_finance_sends_the_summary_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"asOf": "2024-04-03T17:13Z"})

    service = ConsoleService(make_client(handler))
    service.finance()

    assert seen[0].url.path == "/finance/v1/summary"
    assert seen[0].url.query == b""


def test_stats_sends_the_stats_path_without_filters() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"asOf": "2025-05-12T02:59Z"})

    service = ConsoleService(make_client(handler))
    service.stats()

    assert seen[0].url.path == "/metrics/v1/stats"
    assert seen[0].url.query == b""


def test_stats_sends_project_filter() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    service = ConsoleService(make_client(handler))
    service.stats(StatsOptions(project="proj-1"))

    assert seen[0].url.path == "/metrics/v1/stats"
    assert seen[0].url.query.decode() == "project=proj-1"


def test_stats_sends_credential_filter() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    service = ConsoleService(make_client(handler))
    service.stats(StatsOptions(credential="cred-1"))

    assert seen[0].url.query.decode() == "credential=cred-1"


def test_cache_keys_are_frozen() -> None:
    doer = RecordingDoer()
    service = ConsoleService(doer)

    service.finance()
    assert doer.requests[-1].cache_key == "qwx:console:finance"

    service.stats()
    assert doer.requests[-1].cache_key == "qwx:console:stats"

    service.stats(StatsOptions(project="proj-1"))
    assert doer.requests[-1].cache_key == "qwx:console:stats:project=proj-1"

    service.stats(StatsOptions(credential="cred-1"))
    assert doer.requests[-1].cache_key == "qwx:console:stats:credential=cred-1"


def test_endpoint_and_ttl_are_reported() -> None:
    doer = RecordingDoer()
    service = ConsoleService(doer)

    service.finance()
    assert doer.requests[-1].endpoint == EndpointFinance
    assert doer.requests[-1].endpoint == Endpoint("finance/v1/summary")
    assert doer.requests[-1].ttl == timedelta(seconds=3600)
    assert doer.requests[-1].path == "/finance/v1/summary"

    service.stats()
    assert doer.requests[-1].endpoint == EndpointStats
    assert doer.requests[-1].endpoint == Endpoint("metrics/v1/stats")
    assert doer.requests[-1].ttl == timedelta(seconds=3600)
    assert doer.requests[-1].path == "/metrics/v1/stats"


def test_stats_rejects_both_filters_without_reaching_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = ConsoleService(make_client(handler))

    with pytest.raises(InvalidParameterError):
        service.stats(StatsOptions(project="proj-1", credential="cred-1"))
    assert calls == []

    doer = RecordingDoer()
    with pytest.raises(InvalidParameterError):
        ConsoleService(doer).stats(StatsOptions(project="p", credential="c"))
    assert doer.requests == []


def test_cache_hit_does_not_reach_upstream() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"asOf": "2024-04-03T17:13Z"})

    service = ConsoleService(make_client(handler, cache=MemoryCache()))
    service.finance()
    service.finance()

    assert len(calls) == 1


def test_different_filters_do_not_share_the_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    service = ConsoleService(make_client(handler, cache=MemoryCache()))
    service.stats(StatsOptions(project="proj-1"))
    service.stats(StatsOptions(credential="cred-1"))

    assert len(calls) == 2


def test_finance_result_is_parsed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "metadata": {"tag": "t"},
                "asOf": "2024-04-03T17:13Z",
                "currency": "CNY",
                "balance": -17.54,
            },
        )

    service = ConsoleService(make_client(handler))
    got = service.finance()

    assert got.metadata.tag == "t"
    assert got.as_of == "2024-04-03T17:13Z"
    assert got.currency == "CNY"
    assert got.balance == -17.54


def test_async_service_returns_the_same_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"metadata": {"tag": "t"}})

    service = AsyncConsoleService(make_async_client(handler))

    async def run() -> Any:
        return await service.stats(StatsOptions(project="proj-1"))

    got = asyncio.run(run())
    assert got.metadata.tag == "t"


def test_async_service_rejects_both_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    service = AsyncConsoleService(make_async_client(handler))

    async def run() -> Any:
        return await service.stats(StatsOptions(project="p", credential="c"))

    with pytest.raises(InvalidParameterError):
        asyncio.run(run())
