"""预警接口（/weatheralert/v1/*）的调用入口。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝。
要按 LocationID 或地名查预警，先用 geo 包换坐标。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._coord import format_coord
from qwx._service import Service
from qwx.location import Location
from qwx.request import Request
from qwx.v1.alert.types import Endpoint, Result
from qwx.v1.types import Options

__all__ = ["AlertService", "AsyncAlertService"]

CACHE_TTL = timedelta(seconds=300)
"""预警接口的默认缓存时长：上游 5 分钟更新一次预警。"""


def _params(opts: Options) -> Params:
    """把可选参数换成影响结果的查询参数。

    同一份参数既生成上游查询串，也生成缓存键后缀 —— 新增参数时不会漏进键。
    """
    return Params(lang=opts.lang.api, local_time=opts.local_time)


class _AlertCalls(Service):
    """预警端点族的方法体。同步与异步共用。"""

    def _current_call(self, loc: Location, opts: Options | None = None) -> Any:
        options = opts if opts is not None else Options()
        options.lang.validate()
        lat, lon = loc.coordinates()
        lat_part, lon_part = format_coord(lat), format_coord(lon)
        p = _params(options)
        request = Request(
            method="GET",
            path=f"/weatheralert/v1/current/{lat_part}/{lon_part}",
            query=p.query(),
            endpoint=Endpoint,
            cache_key=str(Key(Family.ALERT).path_coord(lat, lon).params(p)),
            ttl=CACHE_TTL,
            out=Result,
        )
        return self._call(request)


class AlertService(_AlertCalls):
    """同步预警服务客户端。"""

    def current(self, loc: Location, opts: Options | None = None) -> Result:
        """查询坐标点上的预警。

        调 GET /weatheralert/v1/current/{latitude}/{longitude}。

        这一代只认坐标：传 LocationID 或地名上游直接拒绝（404）。要按
        LocationID 或地名查，先用 geo 包换坐标。

        opts.lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。
        opts.local_time 为真时返回查询地点的当地时间，否则是 UTC。

        缓存键：`qwx:alert:v1:<lat>,<lon>` 加查询参数后缀。

        默认 TTL 5 分钟，可用 TTLPolicy 按 [Endpoint] 覆盖。

        没有预警时上游返回空列表，不是 null。
        """
        return cast(Result, self._current_call(loc, opts))


class AsyncAlertService(_AlertCalls):
    """异步预警服务客户端。"""

    async def current(self, loc: Location, opts: Options | None = None) -> Result:
        """查询坐标点上的预警。

        调 GET /weatheralert/v1/current/{latitude}/{longitude}。

        这一代只认坐标：传 LocationID 或地名上游直接拒绝（404）。要按
        LocationID 或地名查，先用 geo 包换坐标。

        opts.lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。
        opts.local_time 为真时返回查询地点的当地时间，否则是 UTC。

        缓存键：`qwx:alert:v1:<lat>,<lon>` 加查询参数后缀。

        默认 TTL 5 分钟，可用 TTLPolicy 按 [Endpoint] 覆盖。

        没有预警时上游返回空列表，不是 null。
        """
        return cast(Result, await self._current_call(loc, opts))
