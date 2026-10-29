"""Redis 缓存适配。

实现 [qwx.cache.Cache] 协议，把 SDK 的响应缓存放进 Redis：

    from qwx.redis_cache import RedisCache

    cache = RedisCache.from_url("redis://127.0.0.1:6379/0")
    client = qwx.Client(auth, host, cache=cache)

redis-py 是可选依赖（`pip install "qwx[redis]"`），本模块在函数内部才
`import redis`：没装 redis 时 `import qwx` 与 `import qwx.redis_cache` 都
不报错，只有真正构造客户端时才会失败。

缓存值的口径：**原始 JSON bytes**。SDK 交给我们的是上游响应体本身，
这里原样存、不重新序列化，所以与 Go 版共享同一个 Redis 时键和值都互通：
键的字面量在两版里一致，值都是上游返回的原始 JSON。

ttl 的口径：SDK 给的是相对时长（[datetime.timedelta]），Redis 的 `ex=`
只收整数秒，这里向上取整（不足 1 秒按 1 秒算），过期时间不会比请求的更短。
"""

from __future__ import annotations

import importlib
import math
from datetime import timedelta
from typing import Any, Protocol, cast

from qwx.cache import Cache
from qwx.errors import InvalidParameterError

__all__ = ["RedisCache", "RedisLike"]


class RedisLike(Protocol):
    """redis-py 客户端用到的最小接口。

    只要有 `get` 与 `set` 两个方法就能用，不必是 redis.Redis 本身。
    """

    def get(self, name: str) -> bytes | None:
        """读取一个键。键不存在时返回 None。"""
        ...

    def set(self, name: str, value: bytes, ex: int) -> object:
        """写入一个键，过期时间用整数秒。"""
        ...


class RedisCache:
    """基于 Redis 的 [qwx.cache.Cache] 实现。

    读写失败直接抛异常：SDK 会吞掉缓存异常并降级为直连上游，业务不受
    缓存故障影响。调用方想自己感知故障可以自己捕获。

    **不要给客户端开 `decode_responses=True`**：缓存值按原始 bytes 存取，
    开了之后读到的是 str，与 Go 版共享 Redis 时值不再互通。
    """

    def __init__(self, client: Any) -> None:
        """构造 RedisCache。

        client 是 redis-py 的客户端（`redis.Redis`）或任何有 `get` 与
        `set` 方法的对象。构造时不连接 Redis：连接在第一次读写时建立。

        客户端由调用方持有，需要释放时自行关闭（`client.close()`）。
        """
        self._client = cast(RedisLike, client)

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> RedisCache:
        """用 URL 构造 RedisCache。

        url 是 redis-py 的连接串，如 "redis://127.0.0.1:6379/0"。
        其余关键字参数原样传给 `redis.from_url`。

        需要装了 redis-py，没装时抛 ImportError。
        """
        try:
            module = importlib.import_module("redis")
        except ImportError as exc:
            raise ImportError(
                "qwx: 使用 Redis 缓存需要 redis-py，请执行 pip install 'qwx[redis]'"
            ) from exc
        # redis 不是硬依赖，mypy 看不到它的类型：from_url 的签名用 Any 放行。
        factory = cast(Any, module).from_url
        client = factory(url, **kwargs)
        return cls(client)

    def get(self, key: str) -> bytes | None:
        """读取缓存，未命中返回 None。"""
        return self._client.get(key)

    def set(self, key: str, data: bytes, ttl: timedelta) -> None:
        """写入缓存，ttl 是相对时长。

        ttl 换算成 Redis 的 `ex=`（整数秒，向上取整）。ttl 非正数时抛
        [qwx.errors.InvalidParameterError]：不带过期时间的条目会一直留着，
        天气数据会一直是旧的。
        """
        self._client.set(key, data, ex=_ttl_seconds(ttl))

    def __repr__(self) -> str:
        """调试用表示。"""
        return f"{type(self).__name__}()"


def _ttl_seconds(ttl: timedelta) -> int:
    """把相对时长换算成 Redis 的整数秒。"""
    if ttl <= timedelta(0):
        raise InvalidParameterError(f"qwx: cache ttl must be positive, got {ttl}")
    return max(1, math.ceil(ttl.total_seconds()))


# 编译期断言：RedisCache 满足 Cache 协议。
_: type[Cache] = RedisCache
