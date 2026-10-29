"""旧一代历史天气接口（/v7/historical/weather）的结果类型、参数与常量。

这一代与新一代的差异都在这里：只认 LocationID，数值与单位拼在一个字符串
里，时间是当地时间字符串。历史天气（上游叫「天气时光机」）至今只有 v7
版本，没有新一代。

上游响应里的两块字段名是 `weatherDaily` 与 `weatherHourly`，不是
`daily`/`hourly`，所以这两处必须显式写 alias。
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from qwx._models import QwxModel
from qwx.lang import Lang
from qwx.refer import Refer
from qwx.ttl import Endpoint as EndpointType

__all__ = [
    "Daily",
    "Endpoint",
    "Hourly",
    "Options",
    "Result",
]

Endpoint = EndpointType("v7/historical/weather")
"""历史天气端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

常量的值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置
静默失效。
"""


@dataclass(frozen=True, slots=True)
class Options:
    """历史天气端点的可选参数。"""

    lang: Lang = Lang.UNSPECIFIED
    """语言，如 [qwx.Lang.ZH]。留空用上游默认。

    月相名称与逐小时天气描述随语言变，所以 lang 进缓存键。
    """


class Result(QwxModel):
    """历史天气查询的结果。

    上游这个端点的响应里没有 updateTime 与 fxLink 之外的元信息块，本类型
    也没有对应的字段。
    """

    code: str = ""
    """上游状态码，"200" 为成功。"""

    fx_link: str = ""
    """官网链接。"""

    daily: Daily | None = Field(default=None, alias="weatherDaily")
    """当天的天气汇总。

    上游用对象给这一天的汇总数据，不是数组。上游没给这一块时是 None。

    注意上游的键是 `weatherDaily`，不是 `daily`。
    """

    hourly: list[Hourly] = Field(default_factory=list, alias="weatherHourly")
    """当天的逐小时历史天气。

    列表长度不假设：上游可能给少于 24 条。

    注意上游的键是 `weatherHourly`，不是 `hourly`。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时需要一并展示。
    """


class Daily(QwxModel):
    """一天的历史天气汇总。

    上游把数值都包成字符串，这里保持字符串 —— 小数位数是上游的表达精度，
    转成 float 会丢掉它。
    """

    date: str = ""
    """日期，"YYYY-MM-DD"。"""

    sunrise: str | None = None
    """日出时间。

    高纬度地区上游可能不给（null），用 None 区分「没有日出」与「空串」。
    """

    sunset: str | None = None
    """日落时间。

    同 [Daily.sunrise]：极昼极夜地区可能不给。
    """

    moonrise: str | None = None
    """月升时间。上游可能不给。"""

    moonset: str | None = None
    """月落时间。上游可能不给。"""

    moon_phase: str = ""
    """月相名称，如 "峨眉月"。

    名称随语言变，上游的取值也不止一种，这里只透传不写完备列表。
    """

    temp_max: str = ""
    """当天最高温度。"""

    temp_min: str = ""
    """当天最低温度。"""

    humidity: str = ""
    """当天相对湿度，百分比数值。"""

    precip: str = ""
    """当天总降水量，默认单位毫米。

    空串表示「无此数据」，与 "0.0"（真的没下雨）不是一回事。
    """

    pressure: str = ""
    """站点气压，默认单位百帕。"""


class Hourly(QwxModel):
    """一小时的历史天气。

    上游把数值都包成字符串，这里保持字符串 —— 小数位数是上游的表达精度，
    转成 float 会丢掉它。

    上游个别小时可能不带风向与风速字段，缺失时是空串。
    """

    time: str = ""
    """时刻，"YYYY-MM-DD HH:mm"。"""

    temp: str = ""
    """该小时的温度，默认单位摄氏度。"""

    icon: str = ""
    """天气状况的图标代码。"""

    text: str = ""
    """天气状况的文字描述，如 "晴"。

    描述随语言变，上游的取值也不止一种，这里只透传不写完备列表。
    """

    wind360: str = ""
    """风向 360 度角度。"""

    wind_dir: str = ""
    """风向，如 "西南风"。"""

    wind_scale: str = ""
    """风力等级。"""

    wind_speed: str = ""
    """风速，默认单位公里/小时。"""

    humidity: str = ""
    """该小时的相对湿度，百分比数值。"""

    precip: str = ""
    """该小时的降水量，默认单位毫米。

    空串表示「无此数据」，与 "0.0"（真的没下雨）不是一回事。
    """

    pressure: str = ""
    """站点气压，默认单位百帕。"""
