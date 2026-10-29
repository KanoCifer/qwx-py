"""响应缓存。

本包不绑定任何具体的缓存实现（Redis、内存、文件均可）。未注入缓存时
每次请求都会打到上游。

实现约定：

- get 命中时返回字节，未命中返回 None。
- 读写失败抛异常。缓存故障不应中断业务，SDK 会降级为直接请求上游，
  因此实现方可以放心地抛错。
- set 的 ttl 是相对时长。
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import timedelta
from typing import Protocol, runtime_checkable

__all__ = ["Cache", "MemoryCache"]


@runtime_checkable
class Cache(Protocol):
    """响应缓存接口，由调用方注入。"""

    def get(self, key: str) -> bytes | None:
        """读取缓存，未命中返回 None。"""
        ...

    def set(self, key: str, data: bytes, ttl: timedelta) -> None:
        """写入缓存，ttl 是过期时长。"""
        ...


class MemoryCache:
    """进程内的 Cache 实现。

    **不建议用于生产环境。** 它没有后台清理：过期条目只在被 get 命中时
    顺手删除，没被再次访问的过期条目会一直留在字典里，长期运行的进程
    内存占用只增不减。

    生产环境用共享缓存实现 Cache：redis 适配在 qwx[redis] extra 里，也可
    自行实现带清理的缓存。多实例部署同样需要共享缓存，否则各实例的缓存
    命中率互相摊薄。

    它只适合测试替身与单实例的临时缓存。内部有锁，可并发使用。
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        """构造 MemoryCache。

        clock 是单调时钟的替代，供测试断言过期行为。
        """
        self._entries: dict[str, tuple[bytes, float]] = {}
        self._lock = threading.Lock()
        self._clock = clock if clock is not None else time.monotonic

    def get(self, key: str) -> bytes | None:
        """读取缓存。过期条目按未命中处理并顺手删除。"""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            data, expires = entry
            if self._clock() > expires:
                del self._entries[key]
                return None
            return data

    def set(self, key: str, data: bytes, ttl: timedelta) -> None:
        """写入缓存。"""
        with self._lock:
            self._entries[key] = (data, self._clock() + ttl.total_seconds())

    def __len__(self) -> int:
        """当前缓存的条目数（含已过期但未被清理的条目）。"""
        with self._lock:
            return len(self._entries)
