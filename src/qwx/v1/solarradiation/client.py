"""太阳辐射预报接口（/solarradiation/v1/forecast）的调用入口。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝。
这一族没有 lang 参数 —— 上游的太阳辐射预报不返回文字描述。

同步与异步共用同一套端点方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidParameterError
from qwx.location import Location
from qwx.request import Request
from qwx.v1.solarradiation.types import (
    MAX_FORECAST_HOURS,
    MIN_FORECAST_HOURS,
    Endpoint,
    Options,
    Result,
)

__all__ = ["AsyncSolarRadiationService", "SolarRadiationService"]

CACHE_TTL = timedelta(seconds=3600)
"""太阳辐射预报的默认缓存时长：上游逐 15 分钟更新一次预报。"""

_ALLOWED_INTERVALS = (15, 30, 60)
"""上游接受的预报间隔分钟数。"""

_ALLOWED_EXTRAS = ("weather", "poa")
"""extra 只认这两项，多项用逗号分隔。"""


def _params(opts: Options) -> Params:
    """把可选参数转成缓存键与查询串共用的参数集。"""
    return Params(
        local_time=opts.local_time,
        interval=opts.interval,
        tilt=opts.tilt,
        azimuth=opts.azimuth,
        extra=opts.extra,
    )


def _parse_extra(raw: str) -> set[str]:
    """解析 extra 参数，只认 "weather" 与 "poa"，不许重复。

    取值原样透传给上游与缓存键，顺序不做归一。
    """
    if not raw:
        return set()
    seen: set[str] = set()
    for part in raw.split(","):
        if part not in _ALLOWED_EXTRAS:
            raise InvalidParameterError(f"qwx: extra {raw!r} contains unknown value {part!r}")
        if part in seen:
            raise InvalidParameterError(f"qwx: extra {raw!r} contains duplicate value {part!r}")
        seen.add(part)
    return seen


def _validate_forecast(hours: int, opts: Options) -> None:
    """校验端点参数，越界抛 InvalidParameterError，不打上游。"""
    if hours < MIN_FORECAST_HOURS or hours > MAX_FORECAST_HOURS:
        raise InvalidParameterError(
            f"qwx: hours {hours} out of range [{MIN_FORECAST_HOURS},{MAX_FORECAST_HOURS}]"
        )
    if opts.interval != 0 and opts.interval not in _ALLOWED_INTERVALS:
        raise InvalidParameterError(f"qwx: interval {opts.interval} not in {15, 30, 60}")
    if opts.tilt is not None and not (0 <= opts.tilt <= 90):
        raise InvalidParameterError(f"qwx: tilt {opts.tilt} out of range [0,90]")
    if opts.azimuth is not None and not (0 <= opts.azimuth <= 359):
        raise InvalidParameterError(f"qwx: azimuth {opts.azimuth} out of range [0,359]")
    extras = _parse_extra(opts.extra)
    if "poa" in extras and (opts.tilt is None or opts.azimuth is None):
        raise InvalidParameterError("qwx: extra=poa requires both tilt and azimuth")


class _SolarRadiationCalls(Service):
    """太阳辐射预报端点族的方法体。同步与异步共用。"""

    def _forecast_call(self, loc: Location, hours: int, opts: Options | None = None) -> Any:
        options = opts if opts is not None else Options()
        _validate_forecast(hours, options)
        lat, lon = loc.path()
        params = _params(options)
        query = params.query()
        query["hours"] = str(hours)
        cache_key = str(
            Key(Family.SOLAR_RADIATION)
            .path("forecast")
            .path_coord(loc.lat, loc.lon)
            .count("h", hours)
            .params(params)
        )
        return self._call(
            Request(
                method="GET",
                path=f"/solarradiation/v1/forecast/{lat}/{lon}",
                query=query,
                endpoint=Endpoint,
                cache_key=cache_key,
                ttl=CACHE_TTL,
                out=Result,
            )
        )


class SolarRadiationService(_SolarRadiationCalls):
    """同步太阳辐射预报服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = SolarRadiationService(client)
        result = service.forecast(Location(lat=39.92, lon=116.41), 24)
    """

    def forecast(self, loc: Location, hours: int, opts: Options | None = None) -> Result:
        """查询坐标点上的太阳辐射预报。

        调 GET /solarradiation/v1/forecast/{latitude}/{longitude}?hours=N。

        loc 必须带坐标：这一代只认经纬度路径参数，**纬度在前**。LocationID
        塞进路径上游直接 400。用 LocationID 时先用 geo 包的检索换成坐标。

        hours 取值 1~72，越界抛 InvalidParameterError，不打上游。上游的默认
        是 24 小时，但本方法要求显式给 hours —— 0 同样按越界处理，不替调用方
        套用上游默认值。

        上限以官方文档页为准：页面写「最多支持未来72小时预报」，参数表写
        「可选1-72」。OpenAPI 的 schema 写 maximum: 60，是整份 spec 里唯一的
        maximum: 60，与同一条参数自己的 description 也矛盾。

        opts.interval 只能是 15、30、60；0 表示用上游默认（60 分钟）。
        opts.tilt 是 0~90、opts.azimuth 是 0~359，都是 None 表示不传，
        0 是合法值。opts.extra 只能是 "weather"、"poa" 或两者的组合
        （逗号分隔）。

        opts.extra 含 "poa" 时上游要求 tilt 与 azimuth 都传，缺任一抛
        InvalidParameterError。

        这一族没有 lang 参数：上游不返回文字描述，多传上游会 400。

        时间默认 UTC，要当地时间设 `Options(local_time=True)`。

        缓存键：`qwx:solarradiation:v1:forecast:<lat>,<lon>:h<hours>` 加查询
        参数后缀。预报小时数进键：hours=24 与 hours=48 是两份不同的数据，
        共键会串。extra 原样进键，"poa,weather" 与 "weather,poa" 是两个键。

        默认 TTL 1 小时，可用 TTLPolicy 按 `Endpoint` 覆盖。
        """
        return cast(Result, self._forecast_call(loc, hours, opts))


class AsyncSolarRadiationService(_SolarRadiationCalls):
    """异步太阳辐射预报服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncSolarRadiationService(async_client)
        result = await service.forecast(Location(lat=39.92, lon=116.41), 24)
    """

    async def forecast(self, loc: Location, hours: int, opts: Options | None = None) -> Result:
        """查询坐标点上的太阳辐射预报。

        调 GET /solarradiation/v1/forecast/{latitude}/{longitude}?hours=N。

        loc 必须带坐标：这一代只认经纬度路径参数，**纬度在前**。LocationID
        塞进路径上游直接 400。

        hours 取值 1~72，越界抛 InvalidParameterError，不打上游。

        这一族没有 lang 参数：上游不返回文字描述，多传上游会 400。

        时间默认 UTC，要当地时间设 `Options(local_time=True)`。

        缓存键：`qwx:solarradiation:v1:forecast:<lat>,<lon>:h<hours>` 加查询
        参数后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 `Endpoint` 覆盖。
        """
        return cast(Result, await self._forecast_call(loc, hours, opts))
