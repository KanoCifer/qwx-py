"""快速查询层：按位置一次取齐天气、空气质量与预警。

它不是一个上游资源族，而是把几个已有端点组合成一次调用：

- 位置是坐标对时直接用；
- 位置是地名或 LocationID 时先查 GeoAPI 的城市检索换坐标 —— 新一代接口
  只认坐标；
- 五块数据并发取，缓存与 TTL 各自按端点常量走。

同步与异步共用同一套端点方法体与调用计划，只有并发调度与发送层不同：
同步用线程池，异步用 asyncio。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.geo.client import AsyncGeoService, GeoService
from qwx.geo.types import Options as GeoOptions
from qwx.geo.types import Place
from qwx.location import Location, parse_location
from qwx.ttl import Endpoint
from qwx.v1.airquality.client import AirQualityService, AsyncAirQualityService
from qwx.v1.airquality.types import Current as AirQualityCurrent
from qwx.v1.airquality.types import EndpointCurrent as EndpointAirQuality
from qwx.v1.airquality.types import Options as AirQualityOptions
from qwx.v1.alert.client import AlertService, AsyncAlertService
from qwx.v1.alert.types import Endpoint as EndpointAlert
from qwx.v1.alert.types import Options as AlertOptions
from qwx.v1.alert.types import Result as AlertResult
from qwx.v1.weather.client import AsyncWeatherService, WeatherService
from qwx.v1.weather.types import (
    MAX_DAILY_DAYS,
    MAX_HOURLY_HOURS,
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
)
from qwx.v1.weather.types import EndpointCurrent as EndpointCurrentWeather
from qwx.v1.weather.types import EndpointDaily as EndpointDailyWeather
from qwx.v1.weather.types import EndpointHourly as EndpointHourlyWeather
from qwx.v1.weather.types import Options as WeatherOptions

from .types import DEFAULT_DAYS, DEFAULT_HOURS, EndpointError, Options, Part, Report

__all__ = ["AsyncQuickService", "QuickService"]

ALL_PARTS: tuple[Part, ...] = (
    Part.CURRENT,
    Part.HOURLY,
    Part.DAILY,
    Part.AIR_QUALITY,
    Part.ALERTS,
)
"""报告默认取齐的五块，顺序固定。"""


@dataclass(frozen=True, slots=True)
class _Call:
    """一次待取回的数据块。

    fn 返回模型（同步）或协程（异步），两类调用在这里是同一种形状。
    """

    part: Part
    endpoint: Endpoint
    fn: Callable[[], Any]


def _selected_parts(options: Options) -> list[Part]:
    """本次要取的数据块。未知的数据块抛 InvalidParameterError。"""
    skip: set[str] = set()
    for part in options.skip:
        value = part.value if isinstance(part, Part) else str(part)
        if value not in {item.value for item in ALL_PARTS}:
            raise InvalidParameterError(f"qwx: unknown quick part {value!r}")
        skip.add(value)
    return [item for item in ALL_PARTS if item.value not in skip]


def _counts(options: Options) -> tuple[int, int]:
    """逐时逐日的条数，0 用默认值。越界抛 InvalidParameterError。"""
    hours = options.hours or DEFAULT_HOURS
    if hours < 1 or hours > MAX_HOURLY_HOURS:
        raise InvalidParameterError(f"qwx: hours {hours} out of range [1,{MAX_HOURLY_HOURS}]")
    days = options.days or DEFAULT_DAYS
    if days < 1 or days > MAX_DAILY_DAYS:
        raise InvalidParameterError(f"qwx: days {days} out of range [1,{MAX_DAILY_DAYS}]")
    return hours, days


def _target(loc: str | Location | None) -> tuple[Location, bool]:
    """把用户给的位置归一成（查询用位置, 是否需要查 GeoAPI）。

    字符串先按坐标对与 LocationID 试，识别不了的一律当地名。
    """
    if loc is None:
        raise InvalidLocationError("qwx: quick query needs a location")
    if isinstance(loc, Location):
        if loc.has_coordinates():
            return loc, False
        if loc.id:
            return Location(id=loc.id), True
        if loc.name:
            return Location(name=loc.name), True
        raise InvalidLocationError("qwx: location has no coordinates, ID or name")
    text = loc.strip()
    if not text:
        raise InvalidLocationError("qwx: empty location")
    try:
        parsed = parse_location(text)
    except InvalidLocationError:
        return Location(name=text), True
    if parsed.has_coordinates():
        return parsed, False
    return Location(id=parsed.id), True


def _plan(
    weather: Any,
    airquality: Any,
    alert: Any,
    parts: list[Part],
    loc: Location,
    hours: int,
    days: int,
    options: Options,
) -> list[_Call]:
    """排出本次要打的请求。

    三个服务对象标成 Any 是有意的：同步实现返回模型，异步实现返回协程，
    静态检查无法统一 —— 与 qwx._service 的做法一致。
    """
    weather_options = WeatherOptions(lang=options.lang, local_time=options.local_time)
    air_options = AirQualityOptions(lang=options.lang)
    alert_options = AlertOptions(lang=options.lang, local_time=options.local_time)
    calls: list[_Call] = []
    for part in parts:
        if part is Part.CURRENT:
            calls.append(
                _Call(
                    part,
                    EndpointCurrentWeather,
                    lambda: weather.current(loc, weather_options),
                )
            )
        elif part is Part.HOURLY:
            calls.append(
                _Call(
                    part,
                    EndpointHourlyWeather,
                    lambda: weather.hourly(loc, hours, weather_options),
                )
            )
        elif part is Part.DAILY:
            calls.append(
                _Call(
                    part,
                    EndpointDailyWeather,
                    lambda: weather.daily(loc, days, weather_options),
                )
            )
        elif part is Part.AIR_QUALITY:
            calls.append(
                _Call(
                    part,
                    EndpointAirQuality,
                    lambda: airquality.current(loc, air_options),
                )
            )
        else:
            calls.append(
                _Call(
                    part,
                    EndpointAlert,
                    lambda: alert.current(loc, alert_options),
                )
            )
    return calls


def _report(
    location: Location,
    place: Place | None,
    parts: list[Part],
    results: list[tuple[_Call, Any, BaseException | None]],
    options: Options,
) -> Report:
    """把各块的取回结果拼成报告。

    默认宽松：某块失败记进 errors，其余照常返回；全部失败或严格模式下
    第一块失败即抛异常 —— 报告没有意义。
    """
    errors: list[EndpointError] = []
    current: CurrentWeather | None = None
    hourly: HourlyForecast | None = None
    daily: DailyForecast | None = None
    air_quality: AirQualityCurrent | None = None
    alerts: AlertResult | None = None
    for call, value, error in results:
        if error is not None:
            errors.append(EndpointError(call.part, call.endpoint, error))
            continue
        if call.part is Part.CURRENT:
            current = value
        elif call.part is Part.HOURLY:
            hourly = value
        elif call.part is Part.DAILY:
            daily = value
        elif call.part is Part.AIR_QUALITY:
            air_quality = value
        else:
            alerts = value
    if errors and (options.strict or len(errors) == len(parts)):
        raise errors[0]
    return Report(
        location=location,
        place=place,
        current=current,
        hourly=hourly,
        daily=daily,
        air_quality=air_quality,
        alerts=alerts,
        errors=tuple(errors),
    )


class QuickService:
    """同步快速查询客户端。

    用基础客户端构造，无状态，可并发共享：

        service = QuickService(client)
        report = service.query("北京", Options(lang=Lang.ZH, local_time=True))
    """

    def __init__(self, base: Any) -> None:
        self._geo = GeoService(base)
        self._weather = WeatherService(base)
        self._airquality = AirQualityService(base)
        self._alert = AlertService(base)

    def query(self, loc: str | Location | None, options: Options | None = None) -> Report:
        """按位置查一份完整的天气信息。

        loc 是位置，支持三种写法：

        - 字符串：经纬度对（"116.41,39.92"，经度在前）、地名（"北京"）、
          LocationID（"101010100"）。经纬度与 LocationID 用
          [qwx.parse_location] 识别，识别不了的一律当地名处理。
        - [qwx.Location]：带坐标直接用，带 ID 或 Name 先查 GeoAPI 换坐标。

        位置是地名或 LocationID 时，先调 GeoAPI 的城市检索换坐标 —— 新一代
        接口只认坐标。解析出的地点取第一条，重名城市用 [Options.adm] 或
        [Options.range] 限定。

        五块数据并发取，缓存与 TTL 各自按端点常量走。用 [Options.skip] 跳过
        不需要的块。

        默认宽松：某块失败记进 [Report.errors]，其余照常返回；全部失败才抛
        [EndpointError]。开了 [Options.strict] 则任一块失败即抛异常。
        """
        opts = options if options is not None else Options()
        opts.lang.validate()
        parts = _selected_parts(opts)
        if not parts:
            raise InvalidParameterError("qwx: no part requested")
        hours, days = _counts(opts)

        target, need_lookup = _target(loc)
        place: Place | None = None
        resolved = target
        if need_lookup:
            resolved, place = self._lookup(target, opts)

        calls = _plan(
            self._weather,
            self._airquality,
            self._alert,
            parts,
            resolved,
            hours,
            days,
            opts,
        )
        results = _run_sync(calls)
        return _report(resolved, place, parts, results, opts)

    def _lookup(self, target: Location, options: Options) -> tuple[Location, Place]:
        """用 GeoAPI 的城市检索把地名或 LocationID 换成坐标。

        取第一条结果。地名有重名时用 [Options.adm] 或 [Options.range] 限定。
        """
        result = self._geo.lookup_city(
            target,
            GeoOptions(
                lang=options.lang,
                number=options.number,
                adm=options.adm,
                range=options.range,
            ),
        )
        if not result.locations:
            raise InvalidLocationError(f"qwx: no place matched {target.query()!r}")
        place = result.locations[0]
        lat, lon = place.coordinates()
        return Location(lat=lat, lon=lon), place


class AsyncQuickService:
    """异步快速查询客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncQuickService(async_client)
        report = await service.query("北京", Options(lang=Lang.ZH))
    """

    def __init__(self, base: Any) -> None:
        self._geo = AsyncGeoService(base)
        self._weather = AsyncWeatherService(base)
        self._airquality = AsyncAirQualityService(base)
        self._alert = AsyncAlertService(base)

    async def query(self, loc: str | Location | None, options: Options | None = None) -> Report:
        """按位置查一份完整的天气信息。

        语义与 [QuickService.query] 一致，只是请求在 asyncio 里并发。
        """
        opts = options if options is not None else Options()
        opts.lang.validate()
        parts = _selected_parts(opts)
        if not parts:
            raise InvalidParameterError("qwx: no part requested")
        hours, days = _counts(opts)

        target, need_lookup = _target(loc)
        place: Place | None = None
        resolved = target
        if need_lookup:
            resolved, place = await self._lookup(target, opts)

        calls = _plan(
            self._weather,
            self._airquality,
            self._alert,
            parts,
            resolved,
            hours,
            days,
            opts,
        )
        results = await _run_async(calls)
        return _report(resolved, place, parts, results, opts)

    async def _lookup(self, target: Location, options: Options) -> tuple[Location, Place]:
        """用 GeoAPI 的城市检索把地名或 LocationID 换成坐标。

        语义与 [QuickService._lookup] 一致。
        """
        result = await self._geo.lookup_city(
            target,
            GeoOptions(
                lang=options.lang,
                number=options.number,
                adm=options.adm,
                range=options.range,
            ),
        )
        if not result.locations:
            raise InvalidLocationError(f"qwx: no place matched {target.query()!r}")
        place = result.locations[0]
        lat, lon = place.coordinates()
        return Location(lat=lat, lon=lon), place


def _run_sync(calls: list[_Call]) -> list[tuple[_Call, Any, BaseException | None]]:
    """并发取回各块数据。

    上游请求彼此独立，并发能把总耗时压到最慢的那一个。基础客户端无状态，
    可以并发共享。
    """
    results: list[tuple[_Call, Any, BaseException | None]] = []
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [(call, pool.submit(call.fn)) for call in calls]
        for call, future in futures:
            try:
                results.append((call, future.result(), None))
            except Exception as exc:
                results.append((call, None, exc))
    return results


async def _run_async(calls: list[_Call]) -> list[tuple[_Call, Any, BaseException | None]]:
    """并发取回各块数据。

    语义与 [_run_sync] 一致，只是调度交给 asyncio。
    """

    async def _one(call: _Call) -> tuple[_Call, Any, BaseException | None]:
        try:
            value = await call.fn()
        except Exception as exc:
            return (call, None, exc)
        return (call, value, None)

    return list(await asyncio.gather(*[_one(call) for call in calls]))
