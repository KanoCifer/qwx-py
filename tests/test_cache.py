"""内存缓存。"""

from __future__ import annotations

from datetime import timedelta

from qwx.cache import Cache, MemoryCache


def test_missing_key_misses() -> None:
    cache = MemoryCache()
    assert cache.get("missing") is None


def test_set_then_get() -> None:
    cache = MemoryCache()
    cache.set("k", b"v", timedelta(minutes=1))
    assert cache.get("k") == b"v"


def test_expired_entry_misses_and_is_dropped() -> None:
    now = [0.0]
    cache = MemoryCache(clock=lambda: now[0])
    cache.set("k", b"v", timedelta(minutes=1))
    now[0] = 120.0
    assert cache.get("k") is None
    assert len(cache) == 0


def test_memory_cache_satisfies_the_cache_protocol() -> None:
    assert isinstance(MemoryCache(), Cache)
