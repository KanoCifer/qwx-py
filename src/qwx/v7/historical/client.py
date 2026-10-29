"""旧一代历史天气接口（/v7/historical/weather）的调用入口。

这一代只认 LocationID：坐标对与地名上游都拒。数值与单位拼在一个字符串
里，时间是当地时间字符串，缓存键前缀是 `qwx:historical:`。

同步与异步共用同一套方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.location import Location
from qwx.request import Request
from qwx.v7.historical.types import Endpoint, Options, Result

__all__ = ["AsyncHistoricalService", "HistoricalService"]

CACHE_TTL = timedelta(seconds=86400)
"""历史天气的默认缓存时长：某一天的数据过去之后就不再变。"""


def _validate_date(date: str) -> None:
    """校验日期是 yyyyMMdd 形态的真实日历日期。

    日期范围（上游只给最近 10 天、不含今天）不在这里判断 —— 那要拿「今天」
    比，上游自己会回 400。
    """
    if len(date) != 8 or not date.isdigit():
        raise InvalidParameterError(f"qwx: date {date!r} must be in yyyyMMdd format")
    try:
        datetime.strptime(date, "%Y%m%d")
    except ValueError:
        raise InvalidParameterError(f"qwx: date {date!r} is not a valid calendar date") from None


class _HistoricalCalls(Service):
    """历史天气端点族的方法体。同步与异步共用。"""

    def _weather_call(self, loc: Location, date: str, opts: Options | None = None) -> Any:
        if not loc.id:
            raise InvalidLocationError("qwx: historical weather requires a LocationID")
        _validate_date(date)
        options = opts if opts is not None else Options()
        options.lang.validate()
        params = Params(lang=options.lang.api)
        query = params.query()
        query["location"] = loc.id
        query["date"] = date
        cache_key = str(Key(Family.HISTORICAL).path("weather", loc.id, date).params(params))
        return self._call(
            Request(
                method="GET",
                path="/v7/historical/weather",
                query=query,
                endpoint=Endpoint,
                cache_key=cache_key,
                ttl=CACHE_TTL,
                out=Result,
            )
        )


class HistoricalService(_HistoricalCalls):
    """同步历史天气服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = HistoricalService(client)
        result = service.weather(Location(id="101010100"), "20200725")
    """

    def weather(self, loc: Location, date: str, opts: Options | None = None) -> Result:
        """查询某一天的历史天气。

        调 GET /v7/historical/weather?location=...&date=yyyyMMdd&lang=...

        loc **只认 LocationID** —— 上游这个参数只接受 LocationID，坐标对与
        地名都会被拒。非 LocationID 的位置抛 InvalidLocationError，不打上游。
        LocationID 用 geo 包的检索换。

        date 必填，格式 "yyyyMMdd"。客户端只校验格式与日历合法性，日期范围
        交给上游判断：上游只给最近 10 天、**不含今天**的数据，超范围回 400。

        opts.lang 是语言，如 [qwx.Lang.ZH]；留空用上游默认。月相名称与逐小时
        天气描述随语言变，所以 lang 进缓存键。

        上游还有 unit 参数（"m" 公制 / "i" 英制），本包不暴露 —— 全库都用公制。

        缓存键：`qwx:historical:weather:<locationID>:<date>` 加语言后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。

        数值与单位拼在一个字符串里（"31.7°C" 这种形态），这里保持字符串。
        时间是当地时间字符串。
        """
        return cast(Result, self._weather_call(loc, date, opts))


class AsyncHistoricalService(_HistoricalCalls):
    """异步历史天气服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncHistoricalService(async_client)
        result = await service.weather(Location(id="101010100"), "20200725")
    """

    async def weather(self, loc: Location, date: str, opts: Options | None = None) -> Result:
        """查询某一天的历史天气。

        调 GET /v7/historical/weather?location=...&date=yyyyMMdd&lang=...

        loc **只认 LocationID** —— 坐标对与地名上游都拒。

        date 必填，格式 "yyyyMMdd"；上游只给最近 10 天、不含今天的数据。

        缓存键：`qwx:historical:weather:<locationID>:<date>` 加语言后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。
        """
        return cast(Result, await self._weather_call(loc, date, opts))
