"""旧一代生活指数接口（/v7/indices/{days}d）的调用入口。

生活指数至今只有 v7 版本 —— 实测 /weather/v1/indices/* 与 /v1/indices/*
全部 404。

这一代只认坐标对（查询参数经度在前），数值与单位拼在一个字符串里，
时间是当地时间字符串，缓存键前缀是 `qwx:indices:`。

同步与异步共用同一套端点方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.lang import Lang
from qwx.location import Location
from qwx.request import Request

from .types import (
    MAX_TYPE,
    TYPE_ALL,
    Endpoint,
    Result,
)

__all__ = ["AsyncIndicesService", "IndicesService"]

CACHE_TTL = timedelta(seconds=3600)
"""生活指数的默认缓存时长：上游一天更新几次，缓存一小时。"""


def _type_segment(types: Sequence[int]) -> str:
    """拼出 type 参数与缓存键里的类型段。

    多个类型用逗号连接：上游的 type 参数与键里的类型段共用这个形状。
    单类型时是 "0" 到 "16"，与单类型调用完全一致。
    """
    if len(types) == 1:
        return str(types[0])
    return ",".join(str(typ) for typ in types)


class _IndicesCalls(Service):
    """生活指数端点族的方法体。同步与异步共用。"""

    def _indices_multi_call(
        self,
        loc: Location,
        types: Sequence[int],
        days: int,
        lang: Lang | None = None,
    ) -> Any:
        """生活指数的请求参数与发送。

        单类型调用也走这里，types 只有一个元素。
        """
        if not types:
            raise InvalidParameterError("qwx: indices types must not be empty")
        for typ in types:
            if typ < TYPE_ALL or typ > MAX_TYPE:
                raise InvalidParameterError(
                    f"qwx: indices type {typ} is out of range [{TYPE_ALL},{MAX_TYPE}]"
                )
        if len(types) > 1:
            for typ in types:
                if typ == TYPE_ALL:
                    raise InvalidParameterError(
                        f"qwx: indices type {typ} cannot be combined with other types"
                    )
        if days != 1 and days != 3:
            raise InvalidParameterError(f"qwx: indices days {days} is not supported (only 1 and 3)")
        if not loc.has_coordinates():
            raise InvalidLocationError("qwx: indices requires coordinates")
        language = lang if lang is not None else Lang.UNSPECIFIED
        language.validate()
        type_segment = _type_segment(types)
        params = Params(lang=language.api)
        query = params.query()
        query["location"] = loc.query()
        query["type"] = type_segment
        cache_key = str(
            Key(Family.INDICES)
            .path(loc.query(), f"t{type_segment}")
            .count("d", days)
            .params(params)
        )
        return self._call(
            Request(
                method="GET",
                path=f"/v7/indices/{days}d",
                query=query,
                endpoint=Endpoint,
                cache_key=cache_key,
                ttl=CACHE_TTL,
                out=Result,
            )
        )


class IndicesService(_IndicesCalls):
    """同步生活指数服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = IndicesService(client)
        result = service.indices(Location(lat=39.92, lon=116.41), TYPE_ALL, 1)
    """

    def indices(
        self,
        loc: Location,
        typ: int,
        days: int,
        lang: Lang | None = None,
    ) -> Result:
        """查询生活指数。

        调 GET /v7/indices/{days}d?type={type}&location=...

        上游至今只有 v7 版本，没有新一代（实测 /weather/v1/indices/* 与
        /v1/indices/* 均 404）。

        loc **只认坐标对**：上游对裸经度（如 "121.47"）一律回 400，缺坐标
        抛 [qwx.errors.InvalidLocationError]，不打上游。

        days 只支持 1 与 3 —— 实测 2d / 7d / 10d / 15d / 30d 全部 404，其它
        值抛 [qwx.errors.InvalidParameterError]。

        typ 取 0~16，0 表示全部（[TYPE_ALL]），越界抛
        [qwx.errors.InvalidParameterError]。

        lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。

        缓存键：`qwx:indices:<location>:t<type>:d<days>` 加语言后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。
        """
        return cast(Result, self._indices_multi_call(loc, (typ,), days, lang))

    def indices_multi(
        self,
        loc: Location,
        types: Sequence[int],
        days: int,
        lang: Lang | None = None,
    ) -> Result:
        """查询多种生活指数。

        调 GET /v7/indices/{days}d?type={type1,type2}&location=...

        上游的 type 接受逗号分隔的多个类型（"3,5"），一次请求拿多种指数。

        loc **只认坐标对**，days 只支持 1 与 3 —— 规则同
        [IndicesService.indices]。

        types 每项取值 0~16，不能为空列表；取全部（[TYPE_ALL]）时不能再带
        其他类型，否则抛 [qwx.errors.InvalidParameterError]。

        lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。

        缓存键：`qwx:indices:<location>:t<types>:d<days>` 加语言后缀，
        多个类型用逗号连接（"t3,5"）。

        默认 TTL 1 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。
        """
        return cast(Result, self._indices_multi_call(loc, types, days, lang))


class AsyncIndicesService(_IndicesCalls):
    """异步生活指数服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncIndicesService(async_client)
        result = await service.indices(Location(lat=39.92, lon=116.41), TYPE_ALL, 1)
    """

    async def indices(
        self,
        loc: Location,
        typ: int,
        days: int,
        lang: Lang | None = None,
    ) -> Result:
        """查询生活指数。

        调 GET /v7/indices/{days}d?type={type}&location=...

        loc 只认坐标对；days 只支持 1 与 3；typ 取 0~16。越界在打上游之前
        抛 [qwx.errors.InvalidParameterError]，位置形态不对抛
        [qwx.errors.InvalidLocationError]。

        缓存键：`qwx:indices:<location>:t<type>:d<days>` 加语言后缀。

        默认 TTL 1 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。
        """
        return cast(Result, await self._indices_multi_call(loc, (typ,), days, lang))

    async def indices_multi(
        self,
        loc: Location,
        types: Sequence[int],
        days: int,
        lang: Lang | None = None,
    ) -> Result:
        """查询多种生活指数。

        调 GET /v7/indices/{days}d?type={type1,type2}&location=...

        loc 只认坐标对；days 只支持 1 与 3；types 每项取值 0~16 且不能为
        空列表，取全部时不能与其它类型混用。越界在打上游之前抛
        [qwx.errors.InvalidParameterError]。

        缓存键：`qwx:indices:<location>:t<types>:d<days>` 加语言后缀，
        多个类型用逗号连接。

        默认 TTL 1 小时，可用 TTLPolicy 按 [Endpoint] 覆盖。
        """
        return cast(Result, await self._indices_multi_call(loc, types, days, lang))
