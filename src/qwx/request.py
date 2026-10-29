"""一次上游请求的描述。

端点族用它构造请求：Client.do 负责缓存读写、发送与错误归类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Protocol, runtime_checkable

from qwx.ttl import Endpoint

__all__ = ["AsyncDoer", "Doer", "Request"]


@dataclass(frozen=True, slots=True)
class Request:
    """一次上游请求。

    method 留空按 GET 处理；cache_key 留空表示不缓存；endpoint 留空表示
    不参与 TTLPolicy 匹配，此时缓存时长只由 ttl 决定；ttl 小于等于 0
    表示不缓存。
    """

    method: str = "GET"
    path: str = ""
    query: dict[str, str] = field(default_factory=dict)
    cache_key: str = ""
    endpoint: Endpoint = field(default=Endpoint(""))
    ttl: timedelta = timedelta(0)
    out: type[Any] | None = None


@runtime_checkable
class Doer(Protocol):
    """同步请求发送器。Client 实现该接口。"""

    def do(self, request: Request) -> Any:
        """发送请求并把响应解析到 request.out 指定的模型。"""
        ...


@runtime_checkable
class AsyncDoer(Protocol):
    """异步请求发送器。AsyncClient 实现该接口。"""

    async def do(self, request: Request) -> Any:
        """发送请求并把响应解析到 request.out 指定的模型。"""
        ...
