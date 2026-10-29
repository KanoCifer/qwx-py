"""异步用法示例：API KEY 认证 → 并发查实时天气与空气质量。

与同步版语义对等，只是传输层是异步的：把 Client 换成 AsyncClient，把
接口族的同步类换成 Async* 类，方法变成协程，调用方 await 即可。

运行前设置环境变量：

    QWX_API_KEY    控制台「设置」页里的 API KEY
    QWX_API_HOST   控制台「设置」页分配的专属 API Host（必填）

    python examples/basic_async.py
"""

from __future__ import annotations

import asyncio
import os

import qwx
from qwx.v1.airquality import AsyncAirQualityService
from qwx.v1.weather import AsyncWeatherService, Options


async def main() -> None:
    api_key = os.environ.get("QWX_API_KEY", "")
    api_host = os.environ.get("QWX_API_HOST", "")
    if not api_key:
        raise SystemExit("请设置环境变量 QWX_API_KEY")
    if not api_host:
        raise SystemExit("请设置环境变量 QWX_API_HOST（控制台设置页的专属 API Host）")

    auth = qwx.APIKeyAuth(api_key)

    # 异步客户端用 async with 管理连接关闭。
    async with qwx.AsyncClient(auth, api_host, cache=qwx.MemoryCache()) as client:
        weather = AsyncWeatherService(client)
        air = AsyncAirQualityService(client)

        # 北京的坐标。新一代接口只认坐标，纬度在前。
        loc = qwx.Location(lat=39.92, lon=116.41)

        # 两个请求并发发出，总耗时接近较慢的那一个。
        current, quality = await asyncio.gather(
            weather.current(loc, Options(lang=qwx.Lang.ZH, local_time=True)),
            air.current(loc),
        )

        print(f"天气：{current.condition.text}")
        print(f"温度：{current.temperature.value}{current.temperature.unit}")
        print(f"风：{current.wind.speed.value}{current.wind.speed.unit}")
        print(f"风向：{current.wind.direction.compass}")
        print(f"湿度：{current.humidity * 100:.0f}%")

        # 空气质量按标准给指数，列表长度不假设：上游可能给得比请求的更少。
        for index in quality.indexes:
            print(f"空气质量 {index.name}：{index.aqi_display}（等级 {index.level}）")


if __name__ == "__main__":
    asyncio.run(main())
