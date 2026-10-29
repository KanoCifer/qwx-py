"""旧一代天文数据接口（/v7/astronomy/*）的结果类型、参数与端点常量。

日出日落、月升月落与太阳高度角至今只有 v7 版本。

这一代的形态与新一代不同：

- 位置用查询参数 `location=经度,纬度`（经度在前），不是路径参数；
- 数值与单位不分离 —— v7 把数值与单位拼在一个字符串里；
- 时间是**本地时间**字符串（如 "05:12"），不是 UTC；
- 响应里带 refer 对象，展示数据时要一并展示来源与许可声明。

上游「不要假设」：字段可能缺失、枚举会新增、列表长度不固定，所以可选
字段一律用 None 表达，缺失与零值可区分。
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from qwx._models import QwxModel
from qwx.lang import Lang
from qwx.refer import Refer
from qwx.ttl import Endpoint

__all__ = [
    "AngleResult",
    "EndpointAngle",
    "EndpointMoon",
    "EndpointSun",
    "MoonPhase",
    "MoonResult",
    "Options",
    "SunResult",
]

EndpointSun = Endpoint("v7/astronomy/sun")
"""日出日落端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""

EndpointMoon = Endpoint("v7/astronomy/moon")
"""月升月落与月相端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""

EndpointAngle = Endpoint("v7/astronomy/solar-elevation-angle")
"""太阳高度角端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""


@dataclass(frozen=True, slots=True)
class Options:
    """月相端点的可选参数。

    只有月相端点认语言参数 —— 日出日落与太阳高度角不带语言。
    """

    lang: Lang = Lang.UNSPECIFIED
    """语言，如 [qwx.Lang.ZH]。留空用上游默认。

    月相名称与图标随语言变，所以语言进缓存键。
    """


class SunResult(QwxModel):
    """日出日落数据。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。"""

    fx_link: str = ""
    """官网链接。"""

    sunrise: str | None = None
    """日出时间。

    上游在高纬度地区可能给 null（极昼极夜没有日出日落），用 None 区分
    「没有日出」与「空串」。
    """

    sunset: str | None = None
    """日落时间。

    同 [SunResult.sunrise]：极昼极夜地区可能为空。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时要一并展示。
    """


class MoonPhase(QwxModel):
    """一小时的月相。"""

    fx_time: str = ""
    """月相预报时间。"""

    value: str = ""
    """月相数值。"""

    name: str = ""
    """月相名称，如 "新月"、"满月"。

    名称随语言变，上游的取值也不止一种，这里只透传不写完备列表。
    """

    illumination: str = ""
    """月亮照明度，百分比数值。

    上游给的是字符串，这里保持字符串 —— 转成浮点会丢掉它的表达精度。
    """

    icon: str = ""
    """月相图标代码。"""


class MoonResult(QwxModel):
    """月升月落和月相数据。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。"""

    fx_link: str = ""
    """官网链接。"""

    moonrise: str | None = None
    """当天月升时间。

    上游说可能为空，用 None 区分「没有月升」与「空串」。
    """

    moonset: str | None = None
    """当天月落时间。

    同 [MoonResult.moonrise]：可能为空。
    """

    moon_phase: list[MoonPhase] = Field(default_factory=list)
    """逐小时月相。

    列表长度不固定，不假设 —— 上游可能给得更少。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时要一并展示。
    """


class AngleResult(QwxModel):
    """太阳高度角数据。

    上游这个端点的响应里没有 updateTime 与 fxLink，本类型也没有这两个字段。
    """

    code: str = ""
    """上游状态码，"200" 为成功。"""

    solar_elevation_angle: str = ""
    """太阳高度角（度）。

    上游给的是字符串，这里保持字符串 —— 转成浮点会丢掉它的表达精度。
    """

    solar_azimuth_angle: str = ""
    """太阳方位角（度），0 度为正北。

    上游给的是字符串，这里保持字符串。
    """

    solar_hour: str = ""
    """太阳时，"HHmm" 格式。"""

    hour_angle: str = ""
    """时角。"""

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时要一并展示。
    """
