"""新一代天气预报接口（/weather/v1/*）的调用入口。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 塞进路径上游直接
404（body 为空）。用 LocationID 时先用 geo 包的检索换成坐标。

同步与异步共用同一套方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidParameterError
from qwx.location import Location
from qwx.request import Request
from qwx.v1.weather.types import (
    MAX_DAILY_DAYS,
    MAX_HOURLY_HOURS,
    CurrentWeather,
    DailyForecast,
    EndpointCurrent,
    EndpointDaily,
    EndpointHourly,
    HourlyForecast,
    Options,
)

__all__ = ["AsyncWeatherService", "WeatherService"]

CURRENT_CACHE_TTL = timedelta(seconds=600)
"""实时天气的默认缓存时长（上游约 10 分钟更新一次）。"""

FORECAST_CACHE_TTL = timedelta(seconds=3600)
"""逐时与逐日预报的默认缓存时长（上游约 1 小时更新一次）。"""


def _params(opts: Options) -> Params:
    """把可选参数转成缓存键与查询串共用的参数集。"""
    return Params(lang=opts.lang.api, local_time=opts.local_time)


class _WeatherCalls(Service):
    """天气端点族的方法体。同步与异步共用。"""

    def _current_call(self, loc: Location, opts: Options | None = None) -> Any:
        options = opts if opts is not None else Options()
        options.lang.validate()
        lat, lon = loc.path()
        params = _params(options)
        cache_key = str(
            Key(Family.WEATHER).path("current").path_coord(loc.lat, loc.lon).params(params)
        )
        return self._call(
            Request(
                method="GET",
                path=f"/weather/v1/current/{lat}/{lon}",
                query=params.query(),
                endpoint=EndpointCurrent,
                cache_key=cache_key,
                ttl=CURRENT_CACHE_TTL,
                out=CurrentWeather,
            )
        )

    def _hourly_call(self, loc: Location, hours: int, opts: Options | None = None) -> Any:
        if hours < 1 or hours > MAX_HOURLY_HOURS:
            raise InvalidParameterError(f"qwx: hours {hours} out of range [1,{MAX_HOURLY_HOURS}]")
        options = opts if opts is not None else Options()
        options.lang.validate()
        lat, lon = loc.path()
        params = _params(options)
        query = params.query()
        query["hours"] = str(hours)
        cache_key = str(
            Key(Family.WEATHER)
            .path("hourly")
            .path_coord(loc.lat, loc.lon)
            .count("h", hours)
            .params(params)
        )
        return self._call(
            Request(
                method="GET",
                path=f"/weather/v1/hourly/{lat}/{lon}",
                query=query,
                endpoint=EndpointHourly,
                cache_key=cache_key,
                ttl=FORECAST_CACHE_TTL,
                out=HourlyForecast,
            )
        )

    def _daily_call(self, loc: Location, days: int, opts: Options | None = None) -> Any:
        if days < 1 or days > MAX_DAILY_DAYS:
            raise InvalidParameterError(f"qwx: days {days} out of range [1,{MAX_DAILY_DAYS}]")
        options = opts if opts is not None else Options()
        options.lang.validate()
        lat, lon = loc.path()
        params = _params(options)
        query = params.query()
        query["days"] = str(days)
        cache_key = str(
            Key(Family.WEATHER)
            .path("daily")
            .path_coord(loc.lat, loc.lon)
            .count("d", days)
            .params(params)
        )
        return self._call(
            Request(
                method="GET",
                path=f"/weather/v1/daily/{lat}/{lon}",
                query=query,
                endpoint=EndpointDaily,
                cache_key=cache_key,
                ttl=FORECAST_CACHE_TTL,
                out=DailyForecast,
            )
        )


class WeatherService(_WeatherCalls):
    """同步天气服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = WeatherService(client)
        weather = service.current(Location(lat=39.92, lon=116.41))
    """

    def current(self, loc: Location, opts: Options | None = None) -> CurrentWeather:
        """查询实时天气。

        调 GET /weather/v1/current/{latitude}/{longitude}。

        loc 必须带坐标：新一代接口只认经纬度路径参数，**纬度在前**，
        写反了上游回 400。LocationID 塞进路径上游直接 404（body 为空）。
        用 LocationID 时先用 geo 包检索换成坐标。

        opts.lang 是语言，如 `Lang.ZH`；留空用上游默认。
        opts.local_time 为真时返回查询地点的当地时间 —— 新一代默认给
        UTC，时间会整整差 8 小时。

        缓存键：`qwx:v1:current:<lat>,<lon>` 加查询参数后缀。

        默认 TTL 10 分钟，可用 TTLPolicy 按 `EndpointCurrent` 覆盖。

        湿度与云量是 0~1 的比例，不是百分数。
        """
        return cast(CurrentWeather, self._current_call(loc, opts))

    def hourly(self, loc: Location, hours: int, opts: Options | None = None) -> HourlyForecast:
        """查询逐小时预报。

        调 GET /weather/v1/hourly/{latitude}/{longitude}?hours=N。

        loc 必须带坐标，**纬度在前**；LocationID 塞进路径上游直接 404。

        hours 取值 1~240，超出范围抛 InvalidParameterError，不打上游。

        opts.lang 是语言，如 `Lang.ZH`；留空用上游默认。opts.local_time
        为真时返回当地时间，默认是 UTC。

        缓存键：`qwx:v1:hourly:<lat>,<lon>:h<hours>` 加查询参数后缀。
        预报小时数进键：hours=24 与 hours=48 是两份不同的数据，共键会串。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointHourly` 覆盖。

        列表长度不假设：上游可能给得比请求的 hours 更少。
        """
        return cast(HourlyForecast, self._hourly_call(loc, hours, opts))

    def daily(self, loc: Location, days: int, opts: Options | None = None) -> DailyForecast:
        """查询逐日预报。

        调 GET /weather/v1/daily/{latitude}/{longitude}?days=N。

        loc 必须带坐标，**纬度在前**；LocationID 塞进路径上游直接 404。

        days 取值 1~10，超出范围抛 InvalidParameterError，不打上游。

        opts.lang 是语言，如 `Lang.ZH`；留空用上游默认。opts.local_time
        为真时返回当地时间，默认是 UTC。

        缓存键：`qwx:v1:daily:<lat>,<lon>:d<days>` 加查询参数后缀。
        预报天数进键：days=3 与 days=7 是两份不同的数据，共键会串。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointDaily` 覆盖。

        白天/夜间时段的降水没有 intensity 字段（`Precipitation.intensity`
        为 None），别把它当成强度 0。
        """
        return cast(DailyForecast, self._daily_call(loc, days, opts))


class AsyncWeatherService(_WeatherCalls):
    """异步天气服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncWeatherService(async_client)
        weather = await service.current(Location(lat=39.92, lon=116.41))
    """

    async def current(self, loc: Location, opts: Options | None = None) -> CurrentWeather:
        """查询实时天气。

        调 GET /weather/v1/current/{latitude}/{longitude}。

        loc 必须带坐标：新一代接口只认经纬度路径参数，**纬度在前**，
        写反了上游回 400。LocationID 塞进路径上游直接 404（body 为空）。

        opts.lang 是语言，如 `Lang.ZH`；留空用上游默认。
        opts.local_time 为真时返回当地时间，默认是 UTC。

        缓存键：`qwx:v1:current:<lat>,<lon>` 加查询参数后缀。

        默认 TTL 10 分钟，可用 TTLPolicy 按 `EndpointCurrent` 覆盖。
        """
        return cast(CurrentWeather, await self._current_call(loc, opts))

    async def hourly(
        self, loc: Location, hours: int, opts: Options | None = None
    ) -> HourlyForecast:
        """查询逐小时预报。

        调 GET /weather/v1/hourly/{latitude}/{longitude}?hours=N。

        loc 必须带坐标，**纬度在前**；LocationID 塞进路径上游直接 404。

        hours 取值 1~240，超出范围抛 InvalidParameterError，不打上游。

        缓存键：`qwx:v1:hourly:<lat>,<lon>:h<hours>` 加查询参数后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointHourly` 覆盖。
        """
        return cast(HourlyForecast, await self._hourly_call(loc, hours, opts))

    async def daily(self, loc: Location, days: int, opts: Options | None = None) -> DailyForecast:
        """查询逐日预报。

        调 GET /weather/v1/daily/{latitude}/{longitude}?days=N。

        loc 必须带坐标，**纬度在前**；LocationID 塞进路径上游直接 404。

        days 取值 1~10，超出范围抛 InvalidParameterError，不打上游。

        缓存键：`qwx:v1:daily:<lat>,<lon>:d<days>` 加查询参数后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointDaily` 覆盖。
        """
        return cast(DailyForecast, await self._daily_call(loc, days, opts))
