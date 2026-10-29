"""旧一代台风数据接口（/v7/tropical/*）的调用入口。

三个端点都不收位置参数：台风按流域与台风 ID 检索，与查询地点无关。

旧一代与新一代在字段单位、时间基准、错误体与缓存键上都不同，本包不与
v1 下的包混用任何逻辑。

同步与异步共用同一套端点方法体，只有发送层不同。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key
from qwx._service import Service
from qwx.errors import InvalidParameterError
from qwx.request import Request

from .types import (
    BasinNP,
    EndpointForecast,
    EndpointList,
    EndpointTrack,
    ForecastResult,
    ListResult,
    TrackResult,
)

__all__ = ["AsyncStormService", "StormService"]

LIST_CACHE_TTL = timedelta(seconds=86400)
"""台风列表的默认缓存时长（台风列表一天内基本不变）。"""

FORECAST_CACHE_TTL = timedelta(seconds=3600)
"""台风预报的默认缓存时长（上游几小时更新一次）。"""

TRACK_CACHE_TTL = timedelta(seconds=3600)
"""台风实况和路径的默认缓存时长（上游几小时更新一次）。"""


class _StormCalls(Service):
    """台风端点族的方法体。同步与异步共用。"""

    def _list_call(self, basin: str, year: int) -> Any:
        """台风列表的请求参数与发送。"""
        if basin != BasinNP:
            raise InvalidParameterError(
                f"qwx: storm basin {basin!r} is not supported (only {BasinNP!r})"
            )
        if year <= 0:
            raise InvalidParameterError(f"qwx: storm year {year} must be positive")
        return self._call(
            Request(
                method="GET",
                path="/v7/tropical/storm-list",
                query={"basin": basin, "year": str(year)},
                endpoint=EndpointList,
                cache_key=str(Key(Family.STORM).path("list", basin, str(year))),
                ttl=LIST_CACHE_TTL,
                out=ListResult,
            )
        )

    def _forecast_call(self, storm_id: str) -> Any:
        """台风预报的请求参数与发送。"""
        if not storm_id:
            raise InvalidParameterError("qwx: storm forecast requires a storm id")
        return self._call(
            Request(
                method="GET",
                path="/v7/tropical/storm-forecast",
                query={"stormid": storm_id},
                endpoint=EndpointForecast,
                cache_key=str(Key(Family.STORM).path("forecast", storm_id)),
                ttl=FORECAST_CACHE_TTL,
                out=ForecastResult,
            )
        )

    def _track_call(self, storm_id: str) -> Any:
        """台风实况和路径的请求参数与发送。"""
        if not storm_id:
            raise InvalidParameterError("qwx: storm track requires a storm id")
        return self._call(
            Request(
                method="GET",
                path="/v7/tropical/storm-track",
                query={"stormid": storm_id},
                endpoint=EndpointTrack,
                cache_key=str(Key(Family.STORM).path("track", storm_id)),
                ttl=TRACK_CACHE_TTL,
                out=TrackResult,
            )
        )


class StormService(_StormCalls):
    """同步台风服务客户端。

    用基础客户端构造，无状态，可并发共享。
    """

    def list(self, basin: str, year: int) -> ListResult:
        """查询台风列表。

        调 GET /v7/tropical/storm-list?basin=NP&year=2026。

        本端点不收位置参数：列表按流域与年份检索，与查询地点无关。

        basin 只接受 "NP"（西北太平洋）—— 上游明确说"目前仅支持中国沿海
        地区，即 basin=NP"，别的流域代码上游不认，客户端在打上游之前就抛
        [qwx.errors.InvalidParameterError]。year 必须大于 0，上游只保证支持
        本年度与上一年度，更早的年份能不能查到由上游判断。

        缓存键：`qwx:storm:list:NP:2026`。

        默认 TTL 24 小时（台风列表一天内基本不变），可用 TTLPolicy 按
        [EndpointList] 覆盖。
        """
        return cast(ListResult, self._list_call(basin, year))

    def forecast(self, storm_id: str) -> ForecastResult:
        """查询台风预报。

        调 GET /v7/tropical/storm-forecast?stormid=NP2018。

        本端点不收位置参数：预报按台风 ID 检索，与查询地点无关。

        storm_id 必填且不能为空串，空串抛
        [qwx.errors.InvalidParameterError]，不打上游。ID 从
        [StormService.list] 的结果里取。

        缓存键：`qwx:storm:forecast:NP2018`。

        默认 TTL 1 小时（上游几小时更新一次），可用 TTLPolicy 按
        [EndpointForecast] 覆盖。

        **上游怪癖：查询的台风已经结束时，返回的 forecast 列表是空的 ——
        不是错误。** 要先调 [StormService.list] 拿台风状态，再决定要不要
        查预报。
        """
        return cast(ForecastResult, self._forecast_call(storm_id))

    def track(self, storm_id: str) -> TrackResult:
        """查询台风实况和路径。

        调 GET /v7/tropical/storm-track?stormid=NP2018。

        本端点不收位置参数：实况与路径按台风 ID 检索，与查询地点无关。

        storm_id 必填且不能为空串，空串抛
        [qwx.errors.InvalidParameterError]，不打上游。ID 从
        [StormService.list] 的结果里取。

        缓存键：`qwx:storm:track:NP2018`。

        默认 TTL 1 小时（上游几小时更新一次），可用 TTLPolicy 按
        [EndpointTrack] 覆盖。

        上游怪癖：now 字段是当前实况，台风已结束时上游可能给 null，这时
        [TrackResult.now] 是 None。台风是否活跃看 is_active（"1" 活跃，
        "0" 停编）。
        """
        return cast(TrackResult, self._track_call(storm_id))


class AsyncStormService(_StormCalls):
    """异步台风服务客户端。

    用异步基础客户端构造，无状态，可并发共享。
    """

    async def list(self, basin: str, year: int) -> ListResult:
        """查询台风列表。

        调 GET /v7/tropical/storm-list?basin=NP&year=2026。

        basin 只接受 "NP"，其它值抛
        [qwx.errors.InvalidParameterError]，不打上游。year 必须大于 0。

        缓存键：`qwx:storm:list:NP:2026`。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointList] 覆盖。
        """
        return cast(ListResult, await self._list_call(basin, year))

    async def forecast(self, storm_id: str) -> ForecastResult:
        """查询台风预报。

        调 GET /v7/tropical/storm-forecast?stormid=NP2018。

        storm_id 必填且不能为空串，空串抛
        [qwx.errors.InvalidParameterError]，不打上游。

        台风已结束时上游返回空的 forecast 列表，不是错误。

        缓存键：`qwx:storm:forecast:NP2018`。

        默认 TTL 1 小时，可用 TTLPolicy 按 [EndpointForecast] 覆盖。
        """
        return cast(ForecastResult, await self._forecast_call(storm_id))

    async def track(self, storm_id: str) -> TrackResult:
        """查询台风实况和路径。

        调 GET /v7/tropical/storm-track?stormid=NP2018。

        storm_id 必填且不能为空串，空串抛
        [qwx.errors.InvalidParameterError]，不打上游。

        台风已结束时上游可能给 now=null，这时 [TrackResult.now] 是 None。

        缓存键：`qwx:storm:track:NP2018`。

        默认 TTL 1 小时，可用 TTLPolicy 按 [EndpointTrack] 覆盖。
        """
        return cast(TrackResult, await self._track_call(storm_id))
