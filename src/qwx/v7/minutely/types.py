"""旧一代分钟级降水预报接口（/v7/minutely/5m）的结果类型、参数与常量。

分钟级降水至今只有 v7 版本，没有新一代。

这一代只认坐标（经度在前），且只覆盖中国区域。数值与单位拼在一个字符串
里，时间是当地时间字符串，缓存键前缀是 `qwx:minutely:`。
"""

from __future__ import annotations

from pydantic import Field

from qwx._models import QwxModel
from qwx.refer import Refer
from qwx.ttl import Endpoint as EndpointType

__all__ = [
    "Endpoint",
    "Minutely",
    "Result",
]

Endpoint = EndpointType("v7/minutely/5m")
"""分钟级降水端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

常量的值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置
静默失效。
"""


class Result(QwxModel):
    """分钟级降水预报的结果。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。"""

    fx_link: str = ""
    """官网链接。"""

    summary: str = ""
    """一句话摘要，如 "95分钟后雨就停了"。"""

    minutely: list[Minutely] = Field(default_factory=list)
    """逐 5 分钟的降水预报。

    列表长度不假设：上游给的是未来 2 小时、每 5 分钟一条。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时需要一并展示。
    """


class Minutely(QwxModel):
    """一条分钟级降水预报。"""

    fx_time: str = ""
    """预报时刻。"""

    precip: str = ""
    """降水量。

    上游给的是固定两位小数的字符串。这里保持字符串：空串表示「无此数据」，
    与 "0.00"（真的没下雨）不是一回事，转成数值会把两者压成同一个 0。
    """

    type: str = ""
    """降水类型："rain" / "snow"。

    上游会新增类型，只透传不写完备列表。
    """
