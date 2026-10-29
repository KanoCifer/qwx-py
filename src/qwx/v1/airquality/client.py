"""空气质量端点族的服务客户端。

同步与异步共用同一套端点方法体，只有发送层不同。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidParameterError
from qwx.location import Location
from qwx.request import Request

from .types import (
    Current,
    DailyForecast,
    EndpointCurrent,
    EndpointDaily,
    EndpointHourly,
    EndpointStation,
    HourlyForecast,
    Options,
    StationData,
)

__all__ = ["AirQualityService", "AsyncAirQualityService"]

CURRENT_CACHE_TTL = timedelta(minutes=30)
"""实时与监测站端点的默认缓存时长。

上游逐小时更新，留一半余量。
"""

FORECAST_CACHE_TTL = timedelta(hours=1)
"""预报端点的默认缓存时长。"""


class _AirQualityCalls(Service):
    """空气质量端点族的方法体。同步与异步共用。"""

    def _current_call(self, loc: Location, opts: Options | None = None) -> Any:
        """实时空气质量的请求参数与发送。"""
        options = opts if opts is not None else Options()
        options.lang.validate()
        lat, lon = loc.path()
        params = Params(lang=options.lang.api)
        return self._call(
            Request(
                method="GET",
                path=f"/airquality/v1/current/{lat}/{lon}",
                query=params.query(),
                endpoint=EndpointCurrent,
                cache_key=str(
                    Key(Family.AIR_QUALITY)
                    .path("current")
                    .path_coord(loc.lat, loc.lon)
                    .params(params)
                ),
                ttl=CURRENT_CACHE_TTL,
                out=Current,
            )
        )

    def _daily_call(self, loc: Location, opts: Options | None = None) -> Any:
        """逐日空气质量预报的请求参数与发送。"""
        options = opts if opts is not None else Options()
        options.lang.validate()
        lat, lon = loc.path()
        params = Params(lang=options.lang.api)
        return self._call(
            Request(
                method="GET",
                path=f"/airquality/v1/daily/{lat}/{lon}",
                query=params.query(),
                endpoint=EndpointDaily,
                cache_key=str(
                    Key(Family.AIR_QUALITY)
                    .path("daily")
                    .path_coord(loc.lat, loc.lon)
                    .params(params)
                ),
                ttl=FORECAST_CACHE_TTL,
                out=DailyForecast,
            )
        )

    def _hourly_call(self, loc: Location, opts: Options | None = None) -> Any:
        """逐小时空气质量预报的请求参数与发送。"""
        options = opts if opts is not None else Options()
        options.lang.validate()
        lat, lon = loc.path()
        params = Params(lang=options.lang.api)
        return self._call(
            Request(
                method="GET",
                path=f"/airquality/v1/hourly/{lat}/{lon}",
                query=params.query(),
                endpoint=EndpointHourly,
                cache_key=str(
                    Key(Family.AIR_QUALITY)
                    .path("hourly")
                    .path_coord(loc.lat, loc.lon)
                    .params(params)
                ),
                ttl=FORECAST_CACHE_TTL,
                out=HourlyForecast,
            )
        )

    def _station_call(self, station_id: str, opts: Options | None = None) -> Any:
        """单个监测站数据的请求参数与发送。"""
        if not station_id:
            raise InvalidParameterError("qwx: empty station ID")
        options = opts if opts is not None else Options()
        options.lang.validate()
        params = Params(lang=options.lang.api)
        return self._call(
            Request(
                method="GET",
                path=f"/airquality/v1/stations/{station_id}",
                query=params.query(),
                endpoint=EndpointStation,
                cache_key=str(Key(Family.AIR_QUALITY).path("station", station_id).params(params)),
                ttl=CURRENT_CACHE_TTL,
                out=StationData,
            )
        )


class AirQualityService(_AirQualityCalls):
    """同步空气质量服务客户端。

    用基础客户端构造，无状态，可并发共享。
    """

    def current(self, loc: Location, opts: Options | None = None) -> Current:
        """查询实时空气质量。

        调 GET /airquality/v1/current/{latitude}/{longitude}。

        这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝，
        位置不合法时抛 [qwx.errors.InvalidLocationError]，不打上游。

        opts 是可选参数，lang 留空用上游默认。opts 为 None 表示不传任何
        可选参数。

        缓存键：`qwx:aq:v1:current:<lat>,<lon>` 加语言后缀。

        默认 TTL 30 分钟，可用 TTLPolicy 按 [EndpointCurrent] 覆盖。
        """
        return cast(Current, self._current_call(loc, opts))

    def daily(self, loc: Location, opts: Options | None = None) -> DailyForecast:
        """查询逐日空气质量预报。

        调 GET /airquality/v1/daily/{latitude}/{longitude}。

        这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝，
        位置不合法时抛 [qwx.errors.InvalidLocationError]，不打上游。

        opts 是可选参数，lang 留空用上游默认。

        缓存键：`qwx:aq:v1:daily:<lat>,<lon>` 加语言后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 [EndpointDaily] 覆盖。
        """
        return cast(DailyForecast, self._daily_call(loc, opts))

    def hourly(self, loc: Location, opts: Options | None = None) -> HourlyForecast:
        """查询逐小时空气质量预报。

        调 GET /airquality/v1/hourly/{latitude}/{longitude}。

        这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝，
        位置不合法时抛 [qwx.errors.InvalidLocationError]，不打上游。

        opts 是可选参数，lang 留空用上游默认。

        缓存键：`qwx:aq:v1:hourly:<lat>,<lon>` 加语言后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 [EndpointHourly] 覆盖。
        """
        return cast(HourlyForecast, self._hourly_call(loc, opts))

    def station(self, station_id: str, opts: Options | None = None) -> StationData:
        """查询单个监测站的污染物数据。

        调 GET /airquality/v1/stations/{locationId}。

        station_id 是监测站 ID（如 "P51762"），来自 [Current] 的 stations 列表。
        为空时抛 [qwx.errors.InvalidParameterError]，不打上游。

        opts 是可选参数，lang 留空用上游默认。官方文档页：
        https://dev.qweather.com/docs/api/air-quality/air-station/ —— 明确带
        lang 参数。

        上游警告：监测站的观测值仅供参考，可能由于故障、移除、维护或当地法律
        法规等各种原因导致数据延迟或缺失，无法确保该数据的可用性。

        缓存键：`qwx:aq:v1:station:<id>` 加语言后缀。

        默认 TTL 30 分钟，可用 TTLPolicy 按 [EndpointStation] 覆盖。
        """
        return cast(StationData, self._station_call(station_id, opts))


class AsyncAirQualityService(_AirQualityCalls):
    """异步空气质量服务客户端。

    用异步基础客户端构造，无状态，可并发共享。
    """

    async def current(self, loc: Location, opts: Options | None = None) -> Current:
        """查询实时空气质量。

        调 GET /airquality/v1/current/{latitude}/{longitude}。

        这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝，
        位置不合法时抛 [qwx.errors.InvalidLocationError]，不打上游。

        缓存键：`qwx:aq:v1:current:<lat>,<lon>` 加语言后缀。

        默认 TTL 30 分钟，可用 TTLPolicy 按 [EndpointCurrent] 覆盖。
        """
        return cast(Current, await self._current_call(loc, opts))

    async def daily(self, loc: Location, opts: Options | None = None) -> DailyForecast:
        """查询逐日空气质量预报。

        调 GET /airquality/v1/daily/{latitude}/{longitude}。

        这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝，
        位置不合法时抛 [qwx.errors.InvalidLocationError]，不打上游。

        缓存键：`qwx:aq:v1:daily:<lat>,<lon>` 加语言后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 [EndpointDaily] 覆盖。
        """
        return cast(DailyForecast, await self._daily_call(loc, opts))

    async def hourly(self, loc: Location, opts: Options | None = None) -> HourlyForecast:
        """查询逐小时空气质量预报。

        调 GET /airquality/v1/hourly/{latitude}/{longitude}。

        这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝，
        位置不合法时抛 [qwx.errors.InvalidLocationError]，不打上游。

        缓存键：`qwx:aq:v1:hourly:<lat>,<lon>` 加语言后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 [EndpointHourly] 覆盖。
        """
        return cast(HourlyForecast, await self._hourly_call(loc, opts))

    async def station(self, station_id: str, opts: Options | None = None) -> StationData:
        """查询单个监测站的污染物数据。

        调 GET /airquality/v1/stations/{locationId}。

        station_id 为空时抛 [qwx.errors.InvalidParameterError]，不打上游。

        上游警告：监测站的观测值仅供参考，可能延迟或缺失。

        缓存键：`qwx:aq:v1:station:<id>` 加语言后缀。

        默认 TTL 30 分钟，可用 TTLPolicy 按 [EndpointStation] 覆盖。
        """
        return cast(StationData, await self._station_call(station_id, opts))
