"""v1/solarradiation 的服务客户端。"""

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
from qwx.location import Location
from qwx.ttl import TTLMap
from qwx.v1.solarradiation.client import (
    AsyncSolarRadiationService,
    SolarRadiationService,
)
from qwx.v1.solarradiation.types import Endpoint, Options, Result

UPSTREAM_BODY = {
    "metadata": {"tag": "c4ca4238a0b923820dcc509a6f75849b"},
    "forecasts": [
        {
            "forecastTime": "2023-10-15T11:30Z",
            "solarAngle": {"azimuth": 184, "elevation": 40},
            "dni": {"value": 25.16, "unit": "W/m²"},
            "dhi": {"value": 136.29, "unit": "W/m²"},
            "ghi": {"value": 152.57, "unit": "W/m²"},
            "weather": {
                "temperature": {"value": 18.6, "unit": "°C"},
                "windSpeed": {"value": 2.78, "unit": "m/s"},
                "humidity": 76,
            },
            "poa": {
                "global": {"value": 134.39, "unit": "W/m²"},
                "direct": {"value": 9.35, "unit": "W/m²"},
                "diffuse": {"value": 125.04, "unit": "W/m²"},
                "reflected": {"value": 1.52, "unit": "W/m²"},
            },
        },
        {
            "forecastTime": "2023-10-15T11:45Z",
            "solarAngle": {"azimuth": 189, "elevation": 40},
            "dni": {"value": 20.71, "unit": "W/m²"},
            "dhi": {"value": 132.14, "unit": "W/m²"},
            "ghi": {"value": 145.47, "unit": "W/m²"},
        },
    ],
}

LOC = Location(lat=39.92, lon=116.41)


class FakeServer:
    """记录上游请求的假服务器。"""

    def __init__(self, body: dict[str, Any] | None = None) -> None:
        self.body = body if body is not None else UPSTREAM_BODY
        self.hits = 0
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.hits += 1
        self.requests.append(request)
        return httpx.Response(200, json=self.body)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def query(self, name: str) -> str:
        return self.last.url.params.get(name, "")


class RecordingCache:
    """记录读写的缓存替身：缓存键不进 URL，只能从这里读回来。"""

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


def make_client(server: FakeServer, **kwargs: Any) -> Client:
    transport = httpx.MockTransport(server.handler)
    http = httpx.Client(transport=transport)
    kwargs.setdefault("sleep", lambda _delay: None)
    return Client(APIKeyAuth("k"), "https://example.test", http_client=http, **kwargs)


def make_async_client(server: FakeServer, **kwargs: Any) -> AsyncClient:
    transport = httpx.MockTransport(server.handler)
    http = httpx.AsyncClient(transport=transport)
    kwargs.setdefault("sleep", lambda _delay: asyncio.sleep(0))
    return AsyncClient(APIKeyAuth("k"), "https://example.test", http_client=http, **kwargs)


def test_forecast_sends_the_expected_request() -> None:
    """路径是纬度在前、经度在后，查询参数齐全。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    got = service.forecast(
        LOC,
        24,
        Options(
            local_time=True,
            interval=15,
            tilt=30,
            azimuth=180,
            extra="weather,poa",
        ),
    )

    assert isinstance(got, Result)
    assert server.last.url.path == "/solarradiation/v1/forecast/39.92/116.41"
    assert server.query("hours") == "24"
    assert server.query("interval") == "15"
    assert server.query("tilt") == "30"
    assert server.query("azimuth") == "180"
    assert server.query("extra") == "weather,poa"
    assert server.query("localTime") == "true"
    assert len(got.forecasts) == 2
    assert got.forecasts[0].ghi.value == 152.57


def test_forecast_omits_unset_options() -> None:
    """没设的可选参数不上报上游。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    service.forecast(LOC, 12)

    assert server.query("hours") == "12"
    for key in ("interval", "tilt", "azimuth", "extra", "localTime"):
        assert server.query(key) == ""


def test_forecast_never_sends_lang() -> None:
    """这一族没有 lang 参数：上游不返回文字描述，多传上游会 400。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    service.forecast(LOC, 24)

    assert server.query("lang") == ""


def test_forecast_sends_zero_tilt_and_azimuth() -> None:
    """0 是合法取值，不是「没传」。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    service.forecast(LOC, 24, Options(tilt=0, azimuth=0, extra="poa"))

    assert server.query("tilt") == "0"
    assert server.query("azimuth") == "0"


def test_cache_key_literal_is_frozen() -> None:
    """缓存键字面量在已发布版本里定死。"""
    server = FakeServer()
    cache = RecordingCache()
    service = SolarRadiationService(make_client(server, cache=cache))

    service.forecast(LOC, 24)
    assert cache.sets[-1][0] == "qwx:solarradiation:v1:forecast:39.92,116.41:h24"

    service.forecast(
        LOC,
        24,
        Options(
            local_time=True,
            interval=15,
            tilt=30,
            azimuth=180,
            extra="weather,poa",
        ),
    )
    assert cache.sets[-1][0] == (
        "qwx:solarradiation:v1:forecast:39.92,116.41:h24"
        ":localTime=1:interval=15:tilt=30:azimuth=180:extra=weather,poa"
    )


def test_cache_key_separates_extra_order() -> None:
    """extra 原样进键，两种顺序是两个键。"""
    server = FakeServer()
    cache = RecordingCache()
    service = SolarRadiationService(make_client(server, cache=cache))

    service.forecast(LOC, 24, Options(tilt=30, azimuth=180, extra="poa,weather"))
    service.forecast(LOC, 24, Options(tilt=30, azimuth=180, extra="weather,poa"))

    first, second = cache.sets[-2][0], cache.sets[-1][0]
    assert first != second
    assert first.endswith(":extra=poa,weather")
    assert second.endswith(":extra=weather,poa")


def test_cache_key_separates_affecting_params() -> None:
    """影响结果的参数不同不能共用缓存。"""
    server = FakeServer()
    cache = RecordingCache()
    service = SolarRadiationService(make_client(server, cache=cache))

    service.forecast(LOC, 24, Options(interval=15, tilt=30, azimuth=180, extra="poa"))
    service.forecast(LOC, 48, Options(interval=15, tilt=30, azimuth=180, extra="poa"))
    service.forecast(LOC, 24, Options(interval=30, tilt=30, azimuth=180, extra="poa"))
    service.forecast(LOC, 24, Options(interval=15, tilt=45, azimuth=180, extra="poa"))
    service.forecast(LOC, 24, Options(interval=15, tilt=30, azimuth=90, extra="poa"))
    service.forecast(LOC, 24, Options(interval=15, tilt=30, azimuth=180, extra="weather"))

    keys = {key for key, _data, _ttl in cache.sets}
    assert len(keys) == 6


def test_cache_hit_does_not_reach_upstream() -> None:
    """同一组参数的第二次调用命中缓存。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server, cache=MemoryCache()))

    service.forecast(LOC, 24)
    service.forecast(LOC, 24)

    assert server.hits == 1


def test_different_hours_do_not_share_the_cache() -> None:
    """hours 不同是两份数据，不能共用缓存。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server, cache=MemoryCache()))

    service.forecast(LOC, 24)
    service.forecast(LOC, 48)

    assert server.hits == 2


def test_default_ttl_is_one_hour() -> None:
    """默认 TTL 1 小时。"""
    server = FakeServer()
    cache = RecordingCache()
    service = SolarRadiationService(make_client(server, cache=cache))

    service.forecast(LOC, 24)

    assert cache.sets[-1][2] == timedelta(hours=1)


def test_ttl_policy_overrides_the_default() -> None:
    """策略按端点标识覆盖默认时长。"""
    server = FakeServer()
    cache = RecordingCache()
    policy = TTLMap({Endpoint: timedelta(minutes=5)})
    service = SolarRadiationService(make_client(server, cache=cache, ttl_policy=policy))

    service.forecast(LOC, 24)

    assert cache.sets[-1][2] == timedelta(minutes=5)


@pytest.mark.parametrize("hours", [0, -1, 73])
def test_hours_out_of_range_is_rejected(hours: int) -> None:
    """hours 越界抛 InvalidParameterError，不打上游。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    with pytest.raises(InvalidParameterError):
        service.forecast(LOC, hours)

    assert server.hits == 0


@pytest.mark.parametrize("interval", [5, 45, 90])
def test_interval_out_of_range_is_rejected(interval: int) -> None:
    """interval 只能是 15、30、60。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    with pytest.raises(InvalidParameterError):
        service.forecast(LOC, 24, Options(interval=interval))

    assert server.hits == 0


@pytest.mark.parametrize("tilt", [-1, 91])
def test_tilt_out_of_range_is_rejected(tilt: int) -> None:
    """tilt 越界抛 InvalidParameterError，不打上游。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    with pytest.raises(InvalidParameterError):
        service.forecast(LOC, 24, Options(tilt=tilt))

    assert server.hits == 0


@pytest.mark.parametrize("azimuth", [-1, 360])
def test_azimuth_out_of_range_is_rejected(azimuth: int) -> None:
    """azimuth 越界抛 InvalidParameterError，不打上游。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    with pytest.raises(InvalidParameterError):
        service.forecast(LOC, 24, Options(azimuth=azimuth))

    assert server.hits == 0


@pytest.mark.parametrize("extra", ["wind", "weather,wind", "weather,weather", "Weather"])
def test_invalid_extra_is_rejected(extra: str) -> None:
    """extra 只认 weather 与 poa，且不许重复。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    with pytest.raises(InvalidParameterError):
        service.forecast(LOC, 24, Options(extra=extra))

    assert server.hits == 0


@pytest.mark.parametrize(
    "opts",
    [
        Options(extra="poa"),
        Options(extra="poa", tilt=30),
        Options(extra="poa", azimuth=180),
        Options(extra="weather,poa", azimuth=180),
    ],
)
def test_poa_requires_tilt_and_azimuth(opts: Options) -> None:
    """extra 含 poa 时上游要求两个都传。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    with pytest.raises(InvalidParameterError):
        service.forecast(LOC, 24, opts)

    assert server.hits == 0


def test_location_without_coordinates_is_rejected() -> None:
    """LocationID 没有坐标，新一代接口只认坐标路径参数。"""
    server = FakeServer()
    service = SolarRadiationService(make_client(server))

    with pytest.raises(InvalidLocationError):
        service.forecast(Location(id="101010100"), 24)

    assert server.hits == 0


def test_async_service_forecast() -> None:
    """异步服务客户端与同步版语义对等。"""
    server = FakeServer()
    service = AsyncSolarRadiationService(make_async_client(server))

    got = asyncio.run(service.forecast(LOC, 24, Options(local_time=True)))

    assert isinstance(got, Result)
    assert server.last.url.path == "/solarradiation/v1/forecast/39.92/116.41"
    assert server.query("hours") == "24"
    assert server.query("localTime") == "true"
