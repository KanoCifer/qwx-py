"""太阳辐射预报接口（/solarradiation/v1/forecast）的结果类型、参数与常量。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝。
这一族没有 lang 参数 —— 上游的太阳辐射预报不返回文字描述，多传上游会 400。

数值与单位分离（DNI/DHI/GHI 走 `Value`），但湿度是**百分数**（0~100），
与新一代天气端点的 0~1 比例不同。

官方文档强调「不要假设」：字段可能缺失，枚举值可能新增，所以可选字段一律
用 None 表达，缺失与零值可区分。
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from qwx._models import QwxModel
from qwx.ttl import Endpoint as _Endpoint
from qwx.v1.types import Metadata, Value

__all__ = [
    "MAX_FORECAST_HOURS",
    "MIN_FORECAST_HOURS",
    "POA",
    "Endpoint",
    "Forecast",
    "Options",
    "Result",
    "SolarAngle",
    "Weather",
]

MIN_FORECAST_HOURS = 1
"""预报小时数下限。"""

MAX_FORECAST_HOURS = 72
"""预报小时数上限。

以官方文档页为准：页面写「最多支持未来72小时预报」，参数表也写「可选1-72」。
同一份 OpenAPI 的 schema 写 maximum: 60 —— 那是整份 spec 里唯一的
maximum: 60，与同一条参数自己的 description 也自相矛盾。
"""

Endpoint = _Endpoint("solarradiation/v1/forecast")
"""太阳辐射预报端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

取值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置静默
失效。
"""


@dataclass(frozen=True, slots=True)
class Options:
    """太阳辐射预报接口的可选参数。

    这一族没有 lang 参数：上游不返回文字描述，多传上游会 400。
    """

    local_time: bool = False
    """是否返回查询地点的当地时间。

    新一代接口默认给 UTC，不传 localTime 时间会整整差 8 小时。
    """

    interval: int = 0
    """预报数据的时间间隔分钟数，只能是 15、30、60。

    0 表示不传，用上游默认（60 分钟）。
    """

    tilt: int | None = None
    """光伏系统的倾斜角，0~90。

    None 表示不传。用 None 区分「没有这个参数」与「倾斜角为 0」——
    平铺的光伏板倾斜角就是 0，0 是合法取值。
    """

    azimuth: int | None = None
    """光伏系统的方位角，0~359，0 表示正北。

    None 表示不传，0 是合法取值。
    """

    extra: str = ""
    """额外信息，如 "weather"、"poa"，多项用逗号分隔。

    只认 "weather" 与 "poa"，重复项与未知取值都会被拒。

    extra 含 "poa" 时上游要求 tilt 与 azimuth 都传，缺一个会被拒绝。

    取值原样进缓存键，所以 "poa,weather" 与 "weather,poa" 是两个键。
    """


class SolarAngle(QwxModel):
    """太阳角度。"""

    azimuth: float = 0.0
    """太阳方位角，0~359，正北为 0 度。"""

    elevation: float = 0.0
    """太阳高度角。"""


class Weather(QwxModel):
    """太阳辐射预报附带的基本天气数据。"""

    temperature: Value = Field(default_factory=Value)
    """温度。"""

    wind_speed: Value = Field(default_factory=Value)
    """风速。"""

    humidity: float = 0.0
    """相对湿度，单位是**百分数**（0~100）。

    与新一代天气端点不同：那边给的是 0~1 的比例，这边给的是百分数。
    """


class POA(QwxModel):
    """阵列平面辐照度（Plane of Array）。"""

    global_: Value = Field(default_factory=Value)
    """阵列平面总辐照度。

    `global` 是 Python 关键字，字段名只能写成 `global_`；别名生成器
    to_camel("global_") 恰好给出上游的 "global"。
    """

    direct: Value = Field(default_factory=Value)
    """阵列平面直接辐照度。"""

    diffuse: Value = Field(default_factory=Value)
    """阵列平面散射辐照度。"""

    reflected: Value = Field(default_factory=Value)
    """阵列平面反射辐照度。"""


class Forecast(QwxModel):
    """一个时刻的太阳辐射预报。"""

    forecast_time: str = ""
    """预报时刻。

    默认是 UTC，要当地时间用 `Options(local_time=True)`。
    """

    solar_angle: SolarAngle = Field(default_factory=SolarAngle)
    """太阳角度。"""

    dni: Value = Field(default_factory=Value)
    """法向直接辐照。"""

    dhi: Value = Field(default_factory=Value)
    """散射水平面辐照。"""

    ghi: Value = Field(default_factory=Value)
    """总水平面辐照。"""

    weather: Weather | None = None
    """基本天气数据。

    上游只在请求了 extra=weather 时返回这个对象，其他情况为 None。
    """

    poa: POA | None = None
    """阵列平面辐照度。

    上游只在请求了 extra=poa 时返回这个对象，其他情况为 None。
    """


class Result(QwxModel):
    """太阳辐射预报查询的结果。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    forecasts: list[Forecast] = Field(default_factory=list)
    """太阳辐照预报数据列表。

    条数由请求的 hours 与 interval 决定，但上游可能给得更少 ——
    不要假设长度。
    """
