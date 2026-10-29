"""空气质量端点族的结果类型、参数与端点常量。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝。
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from qwx._models import QwxModel
from qwx.lang import Lang
from qwx.ttl import Endpoint
from qwx.v1.types import Metadata, Value

__all__ = [
    "Advice",
    "Color",
    "Current",
    "DailyForecast",
    "Day",
    "EndpointCurrent",
    "EndpointDaily",
    "EndpointHourly",
    "EndpointStation",
    "Health",
    "Hour",
    "HourlyForecast",
    "Index",
    "Options",
    "Pollutant",
    "PollutantBrief",
    "Station",
    "StationData",
    "SubIndex",
]

# 空气质量端点的标识，用于 TTLPolicy 按端点匹配缓存时长。
#
# 常量的值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置
# 静默失效。
EndpointCurrent = Endpoint("airquality/v1/current")
"""实时空气质量端点。"""

EndpointDaily = Endpoint("airquality/v1/daily")
"""逐日空气质量预报端点。"""

EndpointHourly = Endpoint("airquality/v1/hourly")
"""逐小时空气质量预报端点。"""

EndpointStation = Endpoint("airquality/v1/stations")
"""单个监测站端点。"""


@dataclass(frozen=True, slots=True)
class Options:
    """空气质量接口的可选参数。"""

    lang: Lang = Lang.UNSPECIFIED
    """语言，如 [qwx.Lang.ZH]。留空用上游默认。

    这一族不读当地时间参数：空气质量接口的时间字段不由查询方切换时区。
    """


class Color(QwxModel):
    """颜色。

    只有空气质量接口用这个形状，预警的预警颜色带 code 字段，两者是不同类型。

    四个分量是 rgba 四通道，不是十六进制色值。
    """

    red: int = 0
    """红通道。"""

    green: int = 0
    """绿通道。"""

    blue: int = 0
    """蓝通道。"""

    alpha: int = 0
    """透明度。"""


class PollutantBrief(QwxModel):
    """污染物的简要信息。"""

    code: str = ""
    """污染物代码，如 "pm2p5"。"""

    name: str = ""
    """名称，如 "PM 2.5"。"""

    full_name: str = ""
    """全称。"""


class Advice(QwxModel):
    """分人群建议。"""

    general_population: str = ""
    """普通人群的建议。"""

    sensitive_population: str = ""
    """敏感人群的建议。"""


class Health(QwxModel):
    """健康影响与建议。"""

    effect: str = ""
    """健康影响说明。"""

    advice: Advice = Field(default_factory=Advice)
    """分人群的活动建议。"""


class Index(QwxModel):
    """一个 AQI 指数条目。"""

    code: str = ""
    """标准代码，如 "us-epa"、"qaqi"。"""

    name: str = ""
    """标准名称，如 "AQI (US)"。"""

    aqi: float = 0.0
    """指数值。

    不同标准的量纲不同（QAQI 是 0~1，US EPA 是 0~500），不要跨标准比较。
    """

    aqi_display: str = ""
    """上游给的可读形式。"""

    level: str = ""
    """等级（"1" ~ "6"）。"""

    category: str = ""
    """等级描述，如 "Good"、"Excellent"。"""

    color: Color = Field(default_factory=Color)
    """等级对应的颜色。"""

    primary_pollutant: PollutantBrief | None = None
    """首要污染物。

    可能是 None（空气很好时无首要污染物）。
    """

    health: Health | None = None
    """健康建议。上游没给这一块时是 None。"""


class SubIndex(QwxModel):
    """一个污染物在某标准下的分指数。"""

    code: str = ""
    """标准代码。"""

    aqi: float = 0.0
    """分指数值。量纲随标准而变，规则同 [Index.aqi]。"""

    aqi_display: str = ""
    """可读形式。"""


class Pollutant(QwxModel):
    """一个污染物的实测数据。"""

    code: str = ""
    """污染物代码。"""

    name: str = ""
    """名称。"""

    full_name: str = ""
    """全称。"""

    concentration: Value = Field(default_factory=Value)
    """浓度值。数值与单位分离，单位看 [Value.unit]。"""

    sub_indexes: list[SubIndex] = Field(default_factory=list)
    """该污染物在各标准下的分指数。

    列表长度不假设：上游可能给得更少，也可能不给。
    """


class Station(QwxModel):
    """一个监测站。"""

    id: str = ""
    """站点 ID，如 "P51762"。"""

    name: str = ""
    """站点名称。"""


class Current(QwxModel):
    """实时空气质量。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    indexes: list[Index] = Field(default_factory=list)
    """各标准的 AQI 指数。

    列表长度不假设：上游按标准给，可能给得更少。
    """

    pollutants: list[Pollutant] = Field(default_factory=list)
    """各污染物的实测数据。列表长度不假设。"""

    stations: list[Station] = Field(default_factory=list)
    """附近的监测站。

    列表长度不假设：附近没有监测站时上游给空列表。
    """


class Day(QwxModel):
    """一天的空气质量预报。"""

    forecast_start_time: str = ""
    """预报起始时刻。字符串原样透传，不转 datetime。"""

    forecast_end_time: str = ""
    """预报结束时刻。字符串原样透传，不转 datetime。"""

    indexes: list[Index] = Field(default_factory=list)
    """各标准的 AQI 指数。列表长度不假设。"""

    pollutants: list[Pollutant] = Field(default_factory=list)
    """各污染物的预报浓度。列表长度不假设。"""


class DailyForecast(QwxModel):
    """逐日空气质量预报。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    days: list[Day] = Field(default_factory=list)
    """逐日预报。列表长度不假设：上游可能给得更少。"""


class Hour(QwxModel):
    """一小时的空气质量预报。"""

    forecast_time: str = ""
    """预报时刻。字符串原样透传，不转 datetime。"""

    indexes: list[Index] = Field(default_factory=list)
    """各标准的 AQI 指数。列表长度不假设。"""

    pollutants: list[Pollutant] = Field(default_factory=list)
    """各污染物的预报浓度。列表长度不假设。"""


class HourlyForecast(QwxModel):
    """逐小时空气质量预报。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    hours: list[Hour] = Field(default_factory=list)
    """逐小时预报。列表长度不假设：上游可能给得更少。"""


class StationData(QwxModel):
    """单个监测站的污染物数据。

    上游警告：监测站的观测值仅供参考，可能由于故障、移除、维护或当地法律
    法规等各种原因导致数据延迟或缺失，无法确保该数据的可用性。
    """

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    pollutants: list[Pollutant] = Field(default_factory=list)
    """各污染物的实测数据。列表长度不假设。"""
