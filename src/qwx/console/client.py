"""控制台 API（/finance/v1/summary、/metrics/v1/stats）的调用入口。

控制台 API 查的是帐号自己的财务与请求量，不是天气数据：它不认位置，没有
位置参数。凭据默认没有权限访问这两个端点，帐号所有者要在控制台的
「项目管理 - 凭据 - 控制台权限」里单独开通，否则上游拒绝。

同步与异步共用同一套方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.console.types import (
    EndpointFinance,
    EndpointStats,
    FinanceResult,
    StatsOptions,
    StatsResult,
)
from qwx.errors import InvalidParameterError
from qwx.request import Request

__all__ = ["AsyncConsoleService", "ConsoleService"]

CONSOLE_CACHE_TTL = timedelta(seconds=3600)
"""控制台端点的默认缓存时长。

上游的数据截止至上一个小时或更晚，缓存一小时刚好对齐它的更新节奏。
"""


def _stats_params(opts: StatsOptions) -> Params:
    """把可选参数转成缓存键与查询串共用的参数集。"""
    return Params(project=opts.project, credential=opts.credential)


class _ConsoleCalls(Service):
    """控制台端点族的方法体。同步与异步共用。"""

    def _finance_call(self) -> Any:
        cache_key = str(Key(Family.CONSOLE).path("finance"))
        return self._call(
            Request(
                method="GET",
                path="/finance/v1/summary",
                query={},
                endpoint=EndpointFinance,
                cache_key=cache_key,
                ttl=CONSOLE_CACHE_TTL,
                out=FinanceResult,
            )
        )

    def _stats_call(self, opts: StatsOptions | None = None) -> Any:
        options = opts if opts is not None else StatsOptions()
        if options.project and options.credential:
            raise InvalidParameterError("qwx: project and credential are mutually exclusive")
        params = _stats_params(options)
        cache_key = str(Key(Family.CONSOLE).path("stats").params(params))
        return self._call(
            Request(
                method="GET",
                path="/metrics/v1/stats",
                query=params.query(),
                endpoint=EndpointStats,
                cache_key=cache_key,
                ttl=CONSOLE_CACHE_TTL,
                out=StatsResult,
            )
        )


class ConsoleService(_ConsoleCalls):
    """同步控制台服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = ConsoleService(client)
        finance = service.finance()
    """

    def finance(self) -> FinanceResult:
        """查询财务与计费的汇总信息。

        调 GET /finance/v1/summary。

        凭据默认没有权限访问这个端点：帐号所有者要在控制台的
        「项目管理 - 凭据 - 控制台权限」里勾选「允许访问财务汇总数据」，
        否则上游拒绝。

        返回的数据截止至上一个小时或更早，与控制台网页上显示的可能有 1 小时
        或更长的延迟，以 `FinanceResult.as_of` 为准。

        缓存键：`qwx:console:finance`。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointFinance` 覆盖。
        """
        return cast(FinanceResult, self._finance_call())

    def stats(self, opts: StatsOptions | None = None) -> StatsResult:
        """查询最近 24 小时的 API 请求量统计。

        调 GET /metrics/v1/stats。

        opts.project 与 opts.credential 互斥，都留空时统计帐号下所有项目与
        凭据。两个都填会在客户端被挡下，抛 InvalidParameterError，不打上游。

        凭据默认没有权限访问这个端点：帐号所有者要在控制台的
        「项目管理 - 凭据 - 控制台权限」里勾选对应的权限，否则上游拒绝。

        返回的数据截止至上一个小时或更早，以 `StatsResult.as_of` 为准。

        缓存键：`qwx:console:stats` 加查询参数后缀（项目或凭据 ID）。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointStats` 覆盖。
        """
        return cast(StatsResult, self._stats_call(opts))


class AsyncConsoleService(_ConsoleCalls):
    """异步控制台服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncConsoleService(async_client)
        finance = await service.finance()
    """

    async def finance(self) -> FinanceResult:
        """查询财务与计费的汇总信息。

        调 GET /finance/v1/summary。

        凭据默认没有权限访问这个端点：帐号所有者要在控制台的
        「项目管理 - 凭据 - 控制台权限」里勾选「允许访问财务汇总数据」，
        否则上游拒绝。

        返回的数据截止至上一个小时或更早，与控制台网页上显示的可能有 1 小时
        或更长的延迟，以 `FinanceResult.as_of` 为准。

        缓存键：`qwx:console:finance`。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointFinance` 覆盖。
        """
        return cast(FinanceResult, await self._finance_call())

    async def stats(self, opts: StatsOptions | None = None) -> StatsResult:
        """查询最近 24 小时的 API 请求量统计。

        调 GET /metrics/v1/stats。

        opts.project 与 opts.credential 互斥，都留空时统计帐号下所有项目与
        凭据。两个都填会在客户端被挡下，抛 InvalidParameterError，不打上游。

        凭据默认没有权限访问这个端点：帐号所有者要在控制台的
        「项目管理 - 凭据 - 控制台权限」里勾选对应的权限，否则上游拒绝。

        返回的数据截止至上一个小时或更晚，以 `StatsResult.as_of` 为准。

        缓存键：`qwx:console:stats` 加查询参数后缀（项目或凭据 ID）。

        默认 TTL 1 小时，可用 TTLPolicy 按 `EndpointStats` 覆盖。
        """
        return cast(StatsResult, await self._stats_call(opts))
