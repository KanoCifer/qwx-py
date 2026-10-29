"""Redis 缓存适配。

用假客户端断言调用参数与 ttl 换算，不连真 Redis。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from qwx.cache import Cache
from qwx.errors import InvalidParameterError
from qwx.redis_cache import RedisCache


class FakeRedis:
    """记录调用的假 redis 客户端。"""

    def __init__(self, store: dict[str, bytes] | None = None) -> None:
        """构造假客户端。store 是预置的键值。"""
        self.store: dict[str, bytes] = store if store is not None else {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, bytes, int]] = []
        self.get_error: Exception | None = None
        self.set_error: Exception | None = None

    def get(self, name: str) -> bytes | None:
        """读取一个键。"""
        self.get_calls.append(name)
        if self.get_error is not None:
            raise self.get_error
        return self.store.get(name)

    def set(self, name: str, value: bytes, ex: int) -> Any:
        """写入一个键，记录过期秒数。"""
        self.set_calls.append((name, value, ex))
        if self.set_error is not None:
            raise self.set_error
        self.store[name] = value
        return True


def test_satisfies_cache_protocol() -> None:
    assert isinstance(RedisCache(FakeRedis()), Cache)


def test_get_returns_bytes() -> None:
    client = FakeRedis({"qwx:v1:current:39.92,116.41": b'{"code":"200"}'})
    cache = RedisCache(client)
    assert cache.get("qwx:v1:current:39.92,116.41") == b'{"code":"200"}'


def test_get_miss_returns_none() -> None:
    client = FakeRedis()
    cache = RedisCache(client)
    assert cache.get("missing") is None
    assert client.get_calls == ["missing"]


def test_set_writes_bytes_with_ex_seconds() -> None:
    client = FakeRedis()
    cache = RedisCache(client)
    cache.set("k", b'{"a":1}', timedelta(seconds=600))
    assert client.set_calls == [("k", b'{"a":1}', 600)]
    assert client.store["k"] == b'{"a":1}'


def test_set_ttl_rounds_up_to_whole_seconds() -> None:
    client = FakeRedis()
    cache = RedisCache(client)
    # 90.5 秒向上取整成 91，过期时间不会比请求的更短。
    cache.set("k", b"v", timedelta(milliseconds=90500))
    assert client.set_calls[0][2] == 91


def test_set_sub_second_ttl_becomes_one_second() -> None:
    client = FakeRedis()
    cache = RedisCache(client)
    cache.set("k", b"v", timedelta(milliseconds=100))
    assert client.set_calls[0][2] == 1


def test_set_rejects_non_positive_ttl() -> None:
    client = FakeRedis()
    cache = RedisCache(client)
    with pytest.raises(InvalidParameterError):
        cache.set("k", b"v", timedelta(0))
    with pytest.raises(InvalidParameterError):
        cache.set("k", b"v", timedelta(seconds=-1))
    # 校验没过就不该写进 Redis。
    assert client.set_calls == []
    assert client.store == {}


def test_get_error_propagates() -> None:
    client = FakeRedis()
    client.get_error = RuntimeError("connection reset")
    cache = RedisCache(client)
    with pytest.raises(RuntimeError, match="connection reset"):
        cache.get("k")


def test_set_error_propagates() -> None:
    client = FakeRedis()
    client.set_error = RuntimeError("connection reset")
    cache = RedisCache(client)
    with pytest.raises(RuntimeError, match="connection reset"):
        cache.set("k", b"v", timedelta(seconds=60))


def test_from_url_requires_redis_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """没装 redis-py 时 from_url 抛 ImportError，且错误信息指明怎么装。"""
    import sys

    # sys.modules 里放 None 等价于「这个包不可导入」。
    monkeypatch.setitem(sys.modules, "redis", None)
    with pytest.raises(ImportError, match=r"qwx\[redis\]"):
        RedisCache.from_url("redis://127.0.0.1:6379/0")


def test_from_url_builds_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """装了 redis-py 时 from_url 用传入的 URL 建客户端。"""
    import sys
    import types

    created: dict[str, Any] = {}

    module = types.ModuleType("redis")

    def from_url(url: str, **kwargs: Any) -> FakeRedis:
        created["url"] = url
        created["kwargs"] = kwargs
        return FakeRedis()

    module.from_url = from_url  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "redis", module)

    cache = RedisCache.from_url("redis://127.0.0.1:6379/0", socket_timeout=3)
    assert created["url"] == "redis://127.0.0.1:6379/0"
    assert created["kwargs"] == {"socket_timeout": 3}
    assert isinstance(cache, RedisCache)
