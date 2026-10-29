"""旧一代海洋接口（/v7/ocean/*）的调用入口。

潮汐至今只有 v7 版本 —— 实测 `/ocean/v1/tide/*` 全 404，官方文档也仍是
v7 路径。

这一代的位置是**潮汐站 ID**（如 "P2352"），不是坐标、不是 LocationID；
数值与单位拼在一个字符串里，时间是当地时间字符串，缓存键前缀是
`qwx:tide:`（不是 `qwx:ocean:`）。

同步与异步共用同一套端点方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key
from qwx._service import Service
from qwx.errors import InvalidParameterError
from qwx.request import Request

from .types import Endpoint, Result

__all__ = ["AsyncOceanService", "OceanService"]

CACHE_TTL = timedelta(seconds=3600)
"""潮汐接口的默认缓存时长：上游一天更新几次，缓存一小时。"""


def _validate_date(date: str) -> None:
    """校验日期格式为 YYYYMMDD。

    只校验 8 位数字，不校验日历合法性 —— 与 Go 版口径一致：非法日期
    （如 20211301）交给上游回 400，客户端不抢判。

    潮汐窗口下界是站点当地当天，所以「今天」由调用方按站点当地时间算，
    这里不判断日期范围 —— 那要拿「今天」比，上游自己会回 400。
    """
    if len(date) != 8 or not date.isdigit():
        raise InvalidParameterError(f"qwx: date {date!r} must be in YYYYMMDD format")


class _OceanCalls(Service):
    """潮汐端点族的方法体。同步与异步共用。"""

    def _tide_call(self, station_id: str, date: str) -> Any:
        """潮汐的请求参数与发送。"""
        if not station_id:
            raise InvalidParameterError("qwx: empty tide station ID")
        _validate_date(date)
        return self._call(
            Request(
                method="GET",
                path="/v7/ocean/tide",
                query={"location": station_id, "date": date},
                endpoint=Endpoint,
                cache_key=str(Key(Family.TIDE).path(station_id, date)),
                ttl=CACHE_TTL,
                out=Result,
            )
        )


class OceanService(_OceanCalls):
    """同步潮汐服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = OceanService(client)
        tide = service.tide("P2352", "20210206")
    """

    def tide(self, station_id: str, date: str) -> Result:
        """查询潮汐。

        调 GET /v7/ocean/tide?location=...&date=YYYYMMDD。

        station_id 是**潮汐站 ID**（如 "P2352"），不是坐标、不是 LocationID。
        用 geo 包的 LookupPOI 配 POITSTA 可以检索到本站点。

        date 是潮汐站**当地日期**，格式 "YYYYMMDD"，客户端校验它是合法
        日历日期。

        **日期必须是潮汐站当地的当天**：潮汐窗口的下界是当地当天，用
        UTC 日期会在北京时间 00:00–08:00 要到「昨天」，上游会回 400。

        缓存键：`qwx:tide:<station_id>:<date>`。

        键前缀是 `qwx:tide:` 而不是 `qwx:ocean:` —— 键字面量在已发布版本
        里定死，改了会让已写入的缓存条目全部失效，不要「顺手对齐」。

        默认 TTL 1 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。

        数值与单位拼在一个字符串里，这里保持字符串。时间是站点当地时间
        字符串，不是 UTC。展示上游数据时要一并展示 refer 里的来源与许可。
        """
        return cast(Result, self._tide_call(station_id, date))


class AsyncOceanService(_OceanCalls):
    """异步潮汐服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncOceanService(async_client)
        tide = await service.tide("P2352", "20210206")
    """

    async def tide(self, station_id: str, date: str) -> Result:
        """查询潮汐。

        调 GET /v7/ocean/tide?location=...&date=YYYYMMDD。

        station_id 是潮汐站 ID（如 "P2352"），不是坐标、不是 LocationID。

        date 是潮汐站当地日期，格式 "YYYYMMDD"，且**必须是当地当天** ——
        潮汐窗口下界是当地当天，北京时间 00:00–08:00 会落到「昨天」，
        上游会回 400。

        缓存键：`qwx:tide:<station_id>:<date>`。

        默认 TTL 1 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。
        """
        return cast(Result, await self._tide_call(station_id, date))
