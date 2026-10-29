"""旧一代生活指数接口（/v7/indices/{days}d）的结果类型、参数与常量。

生活指数至今只有 v7 版本，没有新一代（实测 /weather/v1/indices/* 与
/v1/indices/* 全部 404）。

这一代只认坐标对（查询参数经度在前），数值与单位拼在一个字符串里，
时间是当地时间字符串，缓存键前缀是 `qwx:indices:`。

模型按依赖顺序排列：被引用的类型先定义。
"""

from __future__ import annotations

from pydantic import Field

from qwx._models import QwxModel
from qwx.refer import Refer
from qwx.ttl import Endpoint as EndpointType

__all__ = [
    "MAX_TYPE",
    "TYPE_ALL",
    "TYPE_FISHING",
    "DailyIndex",
    "Endpoint",
    "Result",
]

Endpoint = EndpointType("v7/indices")
"""生活指数端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

单类型与多类型两个方法共用这一个端点。

常量的值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置
静默失效。
"""

TYPE_ALL = 0
"""取全部生活指数（type=0）。

0 不能与其它类型同时出现 —— 上游不认这种组合，客户端在打上游之前就拒绝。
"""

TYPE_FISHING = 4
"""钓鱼指数（type=4）。"""

MAX_TYPE = 16
"""最大的指数类型代码。类型取值是 0~16 的闭集，越界上游不认。"""


class DailyIndex(QwxModel):
    """一天的生活指数。"""

    date: str = ""
    """日期，"YYYY-MM-DD"。"""

    type: str = ""
    """指数类型代码。

    上游给的是字符串，这里保持字符串。取值 0~16，具体含义见官方「天气
    指数」文档。
    """

    name: str = ""
    """指数名称，如 "运动指数"。"""

    level: str = ""
    """等级。上游给的是字符串，这里保持字符串。"""

    category: str = ""
    """等级描述，如 "较不宜"。"""

    text: str = ""
    """详细说明。"""


class Result(QwxModel):
    """生活指数查询的结果。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。

    v7 给的是当地时间字符串（如 "2021-12-16T18:35+08:00"），不是 UTC。
    """

    fx_link: str = ""
    """官网链接。"""

    daily: list[DailyIndex] = Field(default_factory=list)
    """逐日指数。

    列表长度不假设：请求的天数与类型决定上游给多少条，上游可能给得更少。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时需要一并展示。
    """
