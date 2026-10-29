"""端点标识与缓存时长策略。

TTL 优先级：单次覆盖 > TTLPolicy > 端点内置默认时长。与 Go 版一致。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta
from typing import Protocol, runtime_checkable

__all__ = [
    "Endpoint",
    "TTLMap",
    "TTLPolicy",
    "TTLPolicyFunc",
    "current_ttl_override",
    "override_ttl",
]


class Endpoint(str):
    """标识一个 API 端点。

    各端点包导出自己的端点常量，用户用它们作为 TTLPolicy 的键。取值
    发布后不再变更。

    值形如 weather/v1/current，与上游路径一致但不含前导斜杠。
    """

    __slots__ = ()


@runtime_checkable
class TTLPolicy(Protocol):
    """按端点决定缓存时长。

    返回值 <= 0 表示该端点本次不缓存；正数是缓存时长。fallback 是端点
    内置的默认时长，策略对该端点没有意见时原样返回即可。

    实现必须并发安全：同一个客户端会被多个线程或协程共享。
    """

    def ttl(self, endpoint: Endpoint, fallback: timedelta) -> timedelta:
        """返回该端点本次请求使用的缓存时长。"""
        ...


class TTLPolicyFunc:
    """把普通函数适配成 TTLPolicy。"""

    def __init__(self, func: Callable[[Endpoint, timedelta], timedelta]) -> None:
        self._func = func

    def ttl(self, endpoint: Endpoint, fallback: timedelta) -> timedelta:
        """返回该端点本次请求使用的缓存时长。"""
        return self._func(endpoint, fallback)


class TTLMap(dict[Endpoint, timedelta]):
    """字典形态的 TTLPolicy：键是端点，值是缓存时长。

    键不存在时沿用端点内置的默认时长；值为 0 表示该端点不缓存。
    """

    def ttl(self, endpoint: Endpoint, fallback: timedelta) -> timedelta:
        """返回该端点本次请求使用的缓存时长。"""
        return self.get(endpoint, fallback)


_ttl_override: ContextVar[timedelta | None] = ContextVar("qwx_ttl_override", default=None)


@contextmanager
def override_ttl(ttl: timedelta) -> Iterator[None]:
    """单次缓存时长覆盖，作用于 with 块内的所有请求。

    覆盖优先级高于 TTLPolicy 与端点内置的默认时长。ttl <= 0 表示这一次
    不读也不写缓存。

    用 contextvars 实现，同步与异步都适用：异步任务里各自持有独立的
    覆盖值，不会互相串。
    """
    token = _ttl_override.set(ttl)
    try:
        yield
    finally:
        _ttl_override.reset(token)


def current_ttl_override() -> timedelta | None:
    """取出当前的单次 TTL 覆盖，没有覆盖时返回 None。"""
    return _ttl_override.get()
