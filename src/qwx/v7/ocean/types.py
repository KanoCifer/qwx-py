"""旧一代海洋接口（/v7/ocean/*）的结果类型、参数与端点常量。

潮汐至今只有 v7 版本 —— 实测 `/ocean/v1/tide/*` 全 404，官方文档也仍是
v7 路径。

这一代的形态与新一代不同：

- 位置是**潮汐站 ID**（如 "P2352"），不是坐标、也不是 LocationID；
- 数值与单位不分离 —— v7 把数值与单位拼在一个字符串里；
- 时间是**当地时间**字符串（如 "2021-02-06T03:48+08:00"），不是 UTC；
- 缓存键前缀是 `qwx:tide:`（不是 `qwx:ocean:`），键字面量已发布，不可改。

上游「不要假设」：字段可能缺失、枚举会新增、列表长度不固定，所以列表
一律用空列表兜底。
"""

from __future__ import annotations

from pydantic import Field

from qwx._models import QwxModel
from qwx.refer import Refer
from qwx.ttl import Endpoint as EndpointType

__all__ = [
    "Endpoint",
    "Result",
    "Tide",
    "TideHourly",
]

Endpoint = EndpointType("v7/ocean/tide")
"""潮汐端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

常量的值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置
静默失效。
"""


class Tide(QwxModel):
    """一个潮汐时刻（高低潮）。"""

    fx_time: str = ""
    """潮汐时刻。

    上游给的是站点当地时间字符串（如 "2021-02-06T03:48+08:00"），不是 UTC。
    """

    height: str = ""
    """潮位高度（米）。

    上游给的是字符串，这里保持字符串 —— 小数位数是上游的表达精度，
    转成 float 会丢掉它。
    """

    type: str = ""
    """潮汐类型："H"（高潮）/ "L"（低潮）。

    上游的取值不止这两种，只透传不写完备列表。
    """


class TideHourly(QwxModel):
    """一个小时的潮位。"""

    fx_time: str = ""
    """时刻。

    上游给的是站点当地时间字符串，不是 UTC。
    """

    height: str = ""
    """潮位高度（米）。

    上游给的是字符串，这里保持字符串 —— 小数位数是上游的表达精度。
    """


class Result(QwxModel):
    """潮汐数据。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。"""

    fx_link: str = ""
    """官网链接。"""

    tide_table: list[Tide] = Field(default_factory=list)
    """潮汐表（高低潮）。

    列表长度不假设 —— 上游可能给得更少。
    """

    tide_hourly: list[TideHourly] = Field(default_factory=list)
    """逐小时潮位。

    列表长度不假设 —— 上游可能给得更少。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时要一并展示。
    """
