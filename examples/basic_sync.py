"""同步用法示例：API KEY 认证 → 实时天气。

运行前设置两个环境变量：

    QWX_API_KEY    控制台「设置」页里的 API KEY
    QWX_API_HOST   控制台「设置」页分配的专属 API Host（必填，没有默认值）

    python examples/basic_sync.py

公共域名（devapi.qweather.com 等）已陆续停服，必须用控制台分配的专属 Host。
"""

from __future__ import annotations

import os

import qwx
from qwx.v1.weather import Options, WeatherService


def main() -> None:
    api_key = os.environ.get("QWX_API_KEY", "")
    api_host = os.environ.get("QWX_API_HOST", "")
    if not api_key:
        raise SystemExit("请设置环境变量 QWX_API_KEY")
    if not api_host:
        raise SystemExit("请设置环境变量 QWX_API_HOST（控制台设置页的专属 API Host）")

    # 认证方式二选一：API KEY 用 APIKeyAuth，JWT 用 JWTAuth（见 jwt_auth.py）。
    # 两种认证不能同时使用。
    auth = qwx.APIKeyAuth(api_key)

    # 注入内置内存缓存：它没有后台清理，只适合开发调试，不要带到生产。
    # 生产环境接 Redis，见 examples/cache_redis.py。
    #
    # 不注入 logger 时 SDK 完全静默；这里挂一个标准库 logger，方便看请求链路。
    client = qwx.Client(auth, api_host, cache=qwx.MemoryCache())

    # 各接口族用基础客户端构造自己的服务客户端。
    weather = WeatherService(client)

    # 北京的坐标。新一代接口只认经纬度路径参数，纬度在前 —— SDK 内部按
    # 上游的形态拼，写反了上游回 400。
    loc = qwx.Location(lat=39.92, lon=116.41)

    # lang 指定返回语言；local_time=True 要当地时间，不传就是 UTC。
    current = weather.current(loc, Options(lang=qwx.Lang.ZH, local_time=True))

    # 湿度是 0~1 的比例，不是百分数 —— 展示时自己乘 100。
    print(f"天气：{current.condition.text}")
    print(f"温度：{current.temperature.value}{current.temperature.unit}")
    print(f"风：{current.wind.speed.value}{current.wind.speed.unit}")
    print(f"风向：{current.wind.direction.compass}")
    print(f"湿度：{current.humidity * 100:.0f}%")
    print(f"气压：{current.pressure.value}{current.pressure.unit}")

    client.close()


if __name__ == "__main__":
    main()
