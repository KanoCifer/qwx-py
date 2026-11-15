"""quick 组合层：位置解析、并发取数、宽松与严格模式。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from qwx import APIKeyAuth, AsyncClient, Client, Lang, Location
from qwx.errors import InvalidLocationError, InvalidParameterError, UnauthorizedError
from qwx.quick import AsyncQuickService, EndpointError, Options, Part, QuickService
from qwx.request import Request
from qwx.v1.airquality.client import AirQualityService
from qwx.v1.airquality.types import Options as AirQualityOptions
from qwx.v1.alert.client import AlertService
from qwx.v1.alert.types import Options as AlertOptions
from qwx.v1.weather.client import WeatherService
from qwx.v1.weather.types import Options as WeatherOptions

LOC = Location(lat=39.92, lon=116.41)

GEO_BODY = {
    "code": "200",
    "location": [
        {
            "id": "101010100",
            "name": "东城",
            "lat": "39.92",
            "lon": "116.41",
            "adm1": "北京市",
            "adm2": "北京",
            "country": "中国",
        }
    ],
}

CURRENT_BODY = {
    "metadata": {"tag": "t"},
    "condition": {"text": "晴", "code": "100"},
    "temperature": {"value": 30.5, "unit": "°C"},
}


def _default_body(path: str) -> dict[str, Any]:
    if path == "/geo/v2/city/lookup":
        return GEO_BODY
    if path.startswith("/weather/v1/current/"):
        return CURRENT_BODY
    if path.startswith("/weather/v1/hourly/"):
        return {"metadata": {"tag": "t"}, "hours": [{"forecastTime": "2026-01-01T00:00Z"}]}
    if path.startswith("/weather/v1/daily/"):
        return {"metadata": {"tag": "t"}, "days": [{"temperatureMax": {"value": 31}}]}
    if path.startswith("/airquality/v1/current/"):
        return {"metadata": {"tag": "t"}, "indexes": [{"code": "us-epa", "aqi": 52}]}
    if path.startswith("/weatheralert/v1/current/"):
        return {"metadata": {"tag": "t"}, "alerts": []}
    return {}


class Upstream:
    """按路径应答的假上游。

    并发安全：快速查询会同时发多个请求，记录请求时必须加锁。
    """

    def __init__(self, fail_paths: tuple[str, ...] = ()) -> None:
        self.paths: list[str] = []
        self.queries: list[str] = []
        self.fail_paths = fail_paths

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        self.queries.append(request.url.query.decode())
        for prefix in self.fail_paths:
            if path.startswith(prefix):
                return httpx.Response(403, json={"error": {"title": "no permission"}})
        return httpx.Response(200, json=_default_body(path))

    def count(self, prefix: str) -> int:
        return sum(1 for path in self.paths if path.startswith(prefix))


class RecordingDoer:
    """记录请求的替身。"""

    def __init__(self) -> None:
        self.requests: list[Request] = []

    def do(self, request: Request) -> Any:
        self.requests.append(request)
        if request.out is None:
            return b"{}"
        return request.out.model_validate({})


def make_client(upstream: Upstream) -> Client:
    http = httpx.Client(transport=httpx.MockTransport(upstream.handler))
    return Client(APIKeyAuth("k"), "https://example.test", http_client=http)


def make_async_client(upstream: Upstream) -> AsyncClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(upstream.handler))
    return AsyncClient(APIKeyAuth("k"), "https://example.test", http_client=http)


def test_query_by_coordinates_skips_geo() -> None:
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    report = service.query("116.41,39.92", Options(lang=Lang.ZH, local_time=True))

    assert upstream.count("/geo/v2/") == 0
    assert report.place is None
    assert report.location.lat == 39.92
    assert report.location.lon == 116.41
    assert report.current is not None
    assert report.current.temperature.value == 30.5
    assert report.hourly is not None
    assert report.daily is not None
    assert report.air_quality is not None
    assert report.alerts is not None
    assert report.alerts.alerts == []
    assert report.errors == ()


def test_query_by_city_name_looks_up_place() -> None:
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    report = service.query("北京", Options(lang=Lang.ZH))

    assert upstream.count("/geo/v2/city/lookup") == 1
    assert report.place is not None
    assert report.place.display_name() == "北京东城"
    assert report.location.lat == 39.92
    assert report.location.lon == 116.41
    assert report.current is not None


def test_query_by_location_id_looks_up_place() -> None:
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    report = service.query("101010100")

    assert upstream.count("/geo/v2/city/lookup") == 1
    assert report.location.lat == 39.92


def test_query_by_location_object() -> None:
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    report = service.query(LOC)

    assert upstream.count("/geo/v2/") == 0
    assert report.location == LOC


def test_query_by_location_object_with_name() -> None:
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    report = service.query(Location(name="北京"))

    assert upstream.count("/geo/v2/city/lookup") == 1
    assert report.place is not None


def test_skip_drops_part() -> None:
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    report = service.query(LOC, Options(skip=(Part.AIR_QUALITY, Part.ALERTS)))

    assert report.air_quality is None
    assert report.alerts is None
    assert report.current is not None
    assert upstream.count("/airquality/") == 0
    assert upstream.count("/weatheralert/") == 0


def test_hours_and_days_reach_upstream() -> None:
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    service.query(LOC, Options(hours=48, days=7))

    assert any("hours=48" in query for query in upstream.queries)
    assert any("days=7" in query for query in upstream.queries)


def test_invalid_hours_rejected() -> None:
    service = QuickService(make_client(Upstream()))
    with pytest.raises(InvalidParameterError):
        service.query(LOC, Options(hours=241))


def test_invalid_days_rejected() -> None:
    service = QuickService(make_client(Upstream()))
    with pytest.raises(InvalidParameterError):
        service.query(LOC, Options(days=11))


def test_unknown_part_rejected() -> None:
    service = QuickService(make_client(Upstream()))
    with pytest.raises(InvalidParameterError):
        service.query(LOC, Options(skip=("rainbow",)))  # type: ignore[arg-type]


def test_skipping_everything_rejected() -> None:
    service = QuickService(make_client(Upstream()))
    with pytest.raises(InvalidParameterError):
        service.query(LOC, Options(skip=tuple(Part)))


def test_empty_location_rejected() -> None:
    service = QuickService(make_client(Upstream()))
    with pytest.raises(InvalidLocationError):
        service.query("  ")
    with pytest.raises(InvalidLocationError):
        service.query(None)


def test_failed_part_is_recorded() -> None:
    upstream = Upstream(fail_paths=("/airquality/",))
    service = QuickService(make_client(upstream))

    report = service.query(LOC)

    assert report.air_quality is None
    assert report.current is not None
    assert len(report.errors) == 1
    error = report.errors[0]
    assert error.part is Part.AIR_QUALITY
    assert isinstance(error.error, UnauthorizedError)


def test_strict_mode_raises() -> None:
    upstream = Upstream(fail_paths=("/airquality/",))
    service = QuickService(make_client(upstream))

    with pytest.raises(EndpointError) as excinfo:
        service.query(LOC, Options(strict=True))
    assert excinfo.value.part is Part.AIR_QUALITY
    assert isinstance(excinfo.value.error, UnauthorizedError)


def test_all_parts_failed_raises() -> None:
    upstream = Upstream(fail_paths=("/weather/", "/airquality/", "/weatheralert/"))
    service = QuickService(make_client(upstream))

    with pytest.raises(EndpointError):
        service.query(LOC)


def test_quick_reuses_endpoint_cache_keys() -> None:
    """quick 不另起缓存键：它用的就是各端点自己的键。"""
    quick_doer = RecordingDoer()
    QuickService(quick_doer).query(LOC, Options(lang=Lang.ZH, local_time=True, hours=48, days=7))
    quick_keys = {request.cache_key for request in quick_doer.requests}

    single_doer = RecordingDoer()
    weather_options = WeatherOptions(lang=Lang.ZH, local_time=True)
    WeatherService(single_doer).current(LOC, weather_options)
    WeatherService(single_doer).hourly(LOC, 48, weather_options)
    WeatherService(single_doer).daily(LOC, 7, weather_options)
    AirQualityService(single_doer).current(LOC, AirQualityOptions(lang=Lang.ZH))
    AlertService(single_doer).current(LOC, AlertOptions(lang=Lang.ZH, local_time=True))
    single_keys = {request.cache_key for request in single_doer.requests}

    assert quick_keys == single_keys


def test_async_query_by_coordinates() -> None:
    upstream = Upstream()
    service = AsyncQuickService(make_async_client(upstream))

    report = asyncio.run(service.query("116.41,39.92", Options(lang=Lang.ZH)))

    assert upstream.count("/geo/v2/") == 0
    assert report.current is not None
    assert report.current.temperature.value == 30.5
    assert report.errors == ()


def test_async_query_by_city_name() -> None:
    upstream = Upstream()
    service = AsyncQuickService(make_async_client(upstream))

    report = asyncio.run(service.query("北京"))

    assert upstream.count("/geo/v2/city/lookup") == 1
    assert report.place is not None


def test_async_failed_part_is_recorded() -> None:
    upstream = Upstream(fail_paths=("/weatheralert/",))
    service = AsyncQuickService(make_async_client(upstream))

    report = asyncio.run(service.query(LOC))

    assert report.alerts is None
    assert len(report.errors) == 1
    assert report.errors[0].part is Part.ALERTS


def test_async_strict_mode_raises() -> None:
    upstream = Upstream(fail_paths=("/weatheralert/",))
    service = AsyncQuickService(make_async_client(upstream))

    with pytest.raises(EndpointError):
        asyncio.run(service.query(LOC, Options(strict=True)))


def test_report_is_serializable() -> None:
    """报告是纯数据模型，可以直接序列化给上层用。"""
    upstream = Upstream()
    service = QuickService(make_client(upstream))

    report = service.query(LOC)
    payload = json.dumps(report.current.model_dump(by_alias=True))
    assert "temperature" in payload
