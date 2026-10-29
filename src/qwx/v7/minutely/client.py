"""旧一代分钟级降水预报接口（/v7/minutely/5m）的调用入口。

这一代只认坐标，且只覆盖中国区域。数值与单位拼在一个字符串里，时间是
当地时间字符串，缓存键前缀是 `qwx:minutely:`。

同步与异步共用同一套方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidLocationError
from qwx.lang import Lang
from qwx.location import Location
from qwx.request import Request
from qwx.v7.minutely.types import Endpoint, Result

__all__ = ["AsyncMinutelyService", "MinutelyService"]

CACHE_TTL = timedelta(seconds=300)
"""分钟级降水的默认缓存时长：上游 5 分钟更新一次。"""


class _MinutelyCalls(Service):
    """分钟级降水端点族的方法体。同步与异步共用。"""

    def _minutely_call(self, loc: Location, lang: Lang | None = None) -> Any:
        if not loc.has_coordinates():
            raise InvalidLocationError("qwx: minutely forecast requires coordinates")
        language = lang if lang is not None else Lang.UNSPECIFIED
        language.validate()
        params = Params(lang=language.api)
        query = params.query()
        query["location"] = loc.query()
        cache_key = str(Key(Family.MINUTELY).path(loc.query()).params(params))
        return self._call(
            Request(
                method="GET",
                path="/v7/minutely/5m",
                query=query,
                endpoint=Endpoint,
                cache_key=cache_key,
                ttl=CACHE_TTL,
                out=Result,
            )
        )


class MinutelyService(_MinutelyCalls):
    """同步分钟级降水服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = MinutelyService(client)
        result = service.minutely(Location(lat=39.92, lon=116.41))
    """

    def minutely(self, loc: Location, lang: Lang | None = None) -> Result:
        """查询分钟级降水预报。

        调 GET /v7/minutely/5m?location=...

        三条硬约束（官方文档 + 实测）：

        1. **只认坐标**：location 必须是 "经度,纬度"，不认 LocationID 也不认
           地名。缺坐标抛 InvalidLocationError，不打上游。
        2. **只覆盖中国区域**：境外坐标上游没有数据。
        3. **粒度是 5 分钟**：未来 2 小时共 24 条，上游每 5 分钟更新一次。

        lang 是语言，如 [qwx.Lang.ZH]；留空用上游默认。

        缓存键：`qwx:minutely:<lon>,<lat>` 加语言后缀。

        默认 TTL 5 分钟，可用 TTLPolicy 按 [Endpoint] 覆盖。

        数值与单位拼在一个字符串里，这里保持字符串。时间是当地时间字符串。
        """
        return cast(Result, self._minutely_call(loc, lang))


class AsyncMinutelyService(_MinutelyCalls):
    """异步分钟级降水服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncMinutelyService(async_client)
        result = await service.minutely(Location(lat=39.92, lon=116.41))
    """

    async def minutely(self, loc: Location, lang: Lang | None = None) -> Result:
        """查询分钟级降水预报。

        调 GET /v7/minutely/5m?location=...

        只认坐标（经度在前），且只覆盖中国区域：境外坐标上游没有数据。

        缓存键：`qwx:minutely:<lon>,<lat>` 加语言后缀。

        默认 TTL 5 分钟，可用 TTLPolicy 按 [Endpoint] 覆盖。
        """
        return cast(Result, await self._minutely_call(loc, lang))
