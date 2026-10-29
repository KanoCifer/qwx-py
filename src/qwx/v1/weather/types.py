"""新一代天气预报接口（/weather/v1/*）的结果类型、参数与常量。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 塞进路径上游直接
404。数值与单位分离，湿度、云量、降水概率是 0~1 的比例而不是百分数。
时间默认 UTC，要当地时间传 `Options(local_time=True)`。

官方文档强调「不要假设」：字段可能缺失，枚举值可能新增，所以可选字段一律
用 None 表达，缺失与零值可区分。

模型按依赖顺序排列：被引用的类型先定义。
"""

from __future__ import annotations

from pydantic import Field

from qwx._models import QwxModel
from qwx.ttl import Endpoint
from qwx.v1.types import Metadata, Options, Value

__all__ = [
    "MAX_DAILY_DAYS",
    "MAX_HOURLY_HOURS",
    "Astro",
    "Condition",
    "CurrentWeather",
    "Daily",
    "DailyForecast",
    "DayNight",
    "DewPoint",
    "EndpointCurrent",
    "EndpointDaily",
    "EndpointHourly",
    "Hourly",
    "HourlyForecast",
    "Options",
    "Precipitation",
    "Pressure",
    "Visibility",
    "Wind",
    "WindDirection",
    "WindGust",
]

MAX_HOURLY_HOURS = 240
"""逐小时预报最多 240 小时。"""

MAX_DAILY_DAYS = 10
"""每日预报最多 10 天。"""

EndpointCurrent = Endpoint("weather/v1/current")
"""实时天气端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""

EndpointHourly = Endpoint("weather/v1/hourly")
"""逐小时预报端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""

EndpointDaily = Endpoint("weather/v1/daily")
"""逐日预报端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""


class Condition(QwxModel):
    """天气现象。"""

    text: str = ""
    """天气现象的文字描述，随 lang 变化。"""

    code: str = ""
    """天气现象代码，如 "100"（晴）、"300"（小雨）。

    官方会新增代码，不要依赖枚举的完备性。
    """


class WindDirection(QwxModel):
    """风向。"""

    degree: float = 0.0
    """风向角度（0~360，0 为北）。"""

    compass: str = ""
    """16 方位英文代码（如 "sw"、"wnw"），不是中文。"""


class Wind(QwxModel):
    """风速与风向。"""

    direction: WindDirection = Field(default_factory=WindDirection)
    """风向。"""

    speed: Value = Field(default_factory=Value)
    """风速。"""

    scale: float = 0.0
    """风力等级（蒲福风级）。"""


class WindGust(QwxModel):
    """阵风。"""

    value: float = 0.0
    """阵风风速。"""

    unit: str = ""
    """单位。"""


class Precipitation(QwxModel):
    """降水情况。"""

    amount: Value = Field(default_factory=Value)
    """降水量。"""

    intensity: Value | None = None
    """降水强度。

    实况与逐时预报有这个字段，逐日预报的白天/夜间时段没有 —— 用 None
    区分「没有」与「强度为 0」。
    """

    probability: float | None = None
    """降水概率（0~1 的比例，不是百分数）。

    实时天气接口没有这个字段，逐小时预报与逐日预报的白天/夜间时段才有。
    用 None 区分「没有」与「概率为 0」。
    """

    type: str = ""
    """降水类型代码，如 "rain"、"snow"、"none"。

    上游会新增类型，不要依赖枚举的完备性。
    """


class Pressure(QwxModel):
    """气压。"""

    value: float = 0.0
    """气压值。"""

    unit: str = ""
    """单位（hPa）。"""


class Visibility(QwxModel):
    """能见度。"""

    value: float = 0.0
    """能见度值。"""

    unit: str = ""
    """单位（m）。"""


class DewPoint(QwxModel):
    """露点温度。"""

    value: float = 0.0
    """露点温度。"""

    unit: str = ""
    """单位（°C）。"""


class Astro(QwxModel):
    """天文信息。"""

    sunrise: str = ""
    """日出时刻。"""

    sunset: str = ""
    """日落时刻。"""

    astronomical_dawn: str = ""
    """天文曙光开始时刻。"""

    nautical_dawn: str = ""
    """航海曙光开始时刻。"""

    civil_dawn: str = ""
    """民用曙光开始时刻。"""

    astronomical_dusk: str = ""
    """天文暮光结束时刻。"""

    nautical_dusk: str = ""
    """航海暮光结束时刻。"""

    civil_dusk: str = ""
    """民用暮光结束时刻。"""

    solar_noon: str = ""
    """正午时刻。"""

    solar_midnight: str = ""
    """子夜时刻。"""

    moonrise: str = ""
    """月出时刻。"""

    moonset: str = ""
    """月落时刻。"""

    moon_transit: str = ""
    """月过中天时刻。"""

    moon_underfoot: str = ""
    """月球位于天顶的时刻。"""

    moon_phase: str = ""
    """月相代码，如 "waxing-gibbous"。"""


class DayNight(QwxModel):
    """白天或夜间时段的天气。"""

    forecast_start_time: str = ""
    """时段起始时刻。"""

    forecast_end_time: str = ""
    """时段结束时刻。"""

    condition: Condition = Field(default_factory=Condition)
    """天气现象。"""

    temperature_max: Value = Field(default_factory=Value)
    """最高气温。"""

    temperature_min: Value = Field(default_factory=Value)
    """最低气温。"""

    wind: Wind = Field(default_factory=Wind)
    """风。"""

    wind_gust_max: WindGust = Field(default_factory=WindGust)
    """时段内的最大阵风。

    上游 daily 端点的白天/夜间时段用 windGustMax，与 current、hourly 端点的
    windGust 不是同一个键。
    """

    precipitation: Precipitation = Field(default_factory=Precipitation)
    """降水情况。

    逐日预报的白天/夜间时段上游没有 intensity 字段，别把缺失当成强度 0。
    """

    humidity: float = 0.0
    """相对湿度，0~1 的比例。"""

    cloud_cover: float = 0.0
    """云量，0~1 的比例。"""


class Daily(QwxModel):
    """一天的预报。"""

    forecast_start_time: str = ""
    """预报起始时刻。"""

    forecast_end_time: str = ""
    """预报结束时刻。"""

    astro: Astro | None = None
    """天文信息（日出日落、月相等）。

    高纬度地区可能没有日出日落 —— 该字段可能缺失，用 None 表达。
    """

    temperature_max: Value = Field(default_factory=Value)
    """最高气温。"""

    temperature_min: Value = Field(default_factory=Value)
    """最低气温。"""

    temperature_avg: Value = Field(default_factory=Value)
    """平均气温。"""

    uv_index_max: float = 0.0
    """最大紫外线指数。"""

    daytime: DayNight = Field(default_factory=DayNight)
    """白天时段（v7 时代是一天一条，新一代拆成白天/夜间两段）。"""

    nighttime: DayNight = Field(default_factory=DayNight)
    """夜间时段。"""


class CurrentWeather(QwxModel):
    """实时天气。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    condition: Condition = Field(default_factory=Condition)
    """天气现象。"""

    temperature: Value = Field(default_factory=Value)
    """气温。"""

    feels_like: Value = Field(default_factory=Value)
    """体感温度。"""

    humidity: float = 0.0
    """相对湿度，**0~1 的比例**（不是百分数）。

    上游给 0.69 就是 69%，直接当百分数展示会错。
    """

    wind: Wind = Field(default_factory=Wind)
    """风。"""

    wind_gust: WindGust = Field(default_factory=WindGust)
    """阵风。"""

    precipitation: Precipitation = Field(default_factory=Precipitation)
    """降水情况。"""

    pressure: Pressure = Field(default_factory=Pressure)
    """气压。"""

    visibility: Visibility = Field(default_factory=Visibility)
    """能见度。"""

    dew_point: DewPoint = Field(default_factory=DewPoint)
    """露点。"""

    cloud_cover: float = 0.0
    """云量，**0~1 的比例**。"""

    uv_index: float = 0.0
    """紫外线指数。"""


class Hourly(QwxModel):
    """一个小时的预报。"""

    forecast_time: str = ""
    """预报时刻。"""

    condition: Condition = Field(default_factory=Condition)
    """天气现象。"""

    temperature: Value = Field(default_factory=Value)
    """气温。"""

    feels_like: Value = Field(default_factory=Value)
    """体感温度。"""

    humidity: float = 0.0
    """相对湿度，0~1 的比例。"""

    wind: Wind = Field(default_factory=Wind)
    """风。"""

    wind_gust: WindGust = Field(default_factory=WindGust)
    """阵风。"""

    precipitation: Precipitation = Field(default_factory=Precipitation)
    """降水情况，含概率。"""

    pressure: Pressure = Field(default_factory=Pressure)
    """气压。"""

    visibility: Visibility = Field(default_factory=Visibility)
    """能见度。"""

    dew_point: DewPoint = Field(default_factory=DewPoint)
    """露点。"""

    cloud_cover: float = 0.0
    """云量，0~1 的比例。"""

    uv_index: float = 0.0
    """紫外线指数。"""


class HourlyForecast(QwxModel):
    """逐小时预报。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    hours: list[Hourly] = Field(default_factory=list)
    """逐小时预报列表。

    条数由请求的 hours 决定，但上游可能给得更少 —— 不要假设长度。
    """


class DailyForecast(QwxModel):
    """逐日预报。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    days: list[Daily] = Field(default_factory=list)
    """逐日预报列表。"""
