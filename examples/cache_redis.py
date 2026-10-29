"""Redis 缓存示例。

安装可选依赖：

    pip install "qwx[redis]"

运行前设置环境变量：

    QWX_API_KEY    控制台「设置」页里的 API KEY
    QWX_API_HOST   控制台「设置」页分配的专属 API Host（必填）
    QWX_REDIS_URL  Redis 连接串，如 redis://127.0.0.1:6379/0（可选，默认这个）

    python examples/cache_redis.py

为什么缓存值是原始 JSON bytes：

SDK 把上游响应体原样交给缓存，不重新序列化。缓存里存的是上游返回的
JSON 字节流，与 Go 版（github.com/KanoCifer/qwx + rediscache）存的东西
一模一样。键的字面量在两版里也一致（族前缀 + 位置段 + 参数段，见
docs/caching.md）。所以同一个 Redis 上，Go 版写入的条目 Python 版能直接
命中，反之亦然 —— 键和值都互通，混跑没问题。

一个前提：Redis 客户端不要开 `decode_responses=True`，否则读出来是 str，
值不再是原始 bytes，两版就不互通了。
"""

from __future__ import annotations

import os

import qwx
from qwx.redis_cache import RedisCache
from qwx.v1.weather import Options, WeatherService


def main() -> None:
    api_key = os.environ.get("QWX_API_KEY", "")
    api_host = os.environ.get("QWX_API_HOST", "")
    if not api_key:
        raise SystemExit("请设置环境变量 QWX_API_KEY")
    if not api_host:
        raise SystemExit("请设置环境变量 QWX_API_HOST（控制台设置页的专属 API Host）")

    redis_url = os.environ.get("QWX_REDIS_URL", "redis://127.0.0.1:6379/0")

    # RedisCache.from_url 用连接串建客户端；也可以自己建好 redis.Redis 再
    # 传给 RedisCache(client)。构造时不连 Redis，第一次读写时才建立连接。
    cache = RedisCache.from_url(redis_url)

    auth = qwx.APIKeyAuth(api_key)
    client = qwx.Client(auth, api_host, cache=cache)

    weather = WeatherService(client)

    # 北京的坐标。新一代接口只认坐标，纬度在前。
    loc = qwx.Location(lat=39.92, lon=116.41)
    opts = Options(lang=qwx.Lang.ZH, local_time=True)

    # 第一次打上游并写入 Redis，第二次命中缓存。
    first = weather.current(loc, opts)
    second = weather.current(loc, opts)

    print(f"天气：{first.condition.text}")
    print(f"温度：{first.temperature.value}{first.temperature.unit}")
    print(f"湿度：{first.humidity * 100:.0f}%")
    print(f"两次结果一致：{first == second}")

    # 缓存键的形状：族前缀 + 位置段 + 参数段。想在 Redis 里手动查：
    #   redis-cli KEYS 'qwx:v1:current:*'
    # 键的字面量已发布即不可变，改了会让已写入的条目全部失效。
    client.close()


if __name__ == "__main__":
    main()
