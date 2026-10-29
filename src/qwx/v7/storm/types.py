"""旧一代台风数据接口（/v7/tropical/*）的结果类型、参数与端点常量。

台风数据至今只有旧一代版本，没有新一代。三个端点都不收位置参数：台风按
流域与台风 ID 检索，与查询地点无关。

旧一代的怪癖：数值与单位拼在一个字符串里（纬度是 "31.7" 而不是数字），
时间是本地时间字符串（如 "2021-07-27T20:00+08:00"），不是 UTC。

模型按依赖顺序排列：被引用的类型先定义。
"""

from __future__ import annotations

from pydantic import Field

from qwx._models import QwxModel
from qwx.refer import Refer
from qwx.ttl import Endpoint

__all__ = [
    "BasinNP",
    "EndpointForecast",
    "EndpointList",
    "EndpointTrack",
    "Forecast",
    "ForecastResult",
    "ListResult",
    "StormState",
    "StormSummary",
    "TrackPoint",
    "TrackResult",
    "WindRadius",
]

EndpointList = Endpoint("v7/tropical/storm-list")
"""台风列表端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""

EndpointForecast = Endpoint("v7/tropical/storm-forecast")
"""台风预报端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""

EndpointTrack = Endpoint("v7/tropical/storm-track")
"""台风实况和路径端点的标识，用于 TTLPolicy 按端点匹配缓存时长。"""

BasinNP = "NP"
"""西北太平洋流域代码（basin=NP）。

上游目前只支持这一个流域（"目前仅支持中国沿海地区，即 basin=NP"）。别的
流域代码上游不认，客户端在打上游之前就拒绝。
"""


class StormSummary(QwxModel):
    """一个台风的概要。"""

    id: str = ""
    """台风 ID，如 "NP2018"。"""

    name: str = ""
    """台风名称，如 "莫拉菲"。"""

    basin: str = ""
    """台风所处流域，如 "NP"。"""

    year: str = ""
    """台风所处年份。

    上游给的是字符串，这里保持字符串。
    """

    is_active: str = ""
    """活跃标记："1" 活跃台风，"0" 停编。

    上游给的是字符串，这里保持字符串，不转成 bool。
    """


class WindRadius(QwxModel):
    """一个风圈的四个方向半径。"""

    ne_radius: str = ""
    """东北半径。上游可能是空串。"""

    se_radius: str = ""
    """东南半径。上游可能是空串。"""

    sw_radius: str = ""
    """西南半径。上游可能是空串。"""

    nw_radius: str = ""
    """西北半径。上游可能是空串。"""


class StormState(QwxModel):
    """一个时刻的台风状态。

    上游把台风属性平铺在预报元素与轨迹元素里，这两组字段完全一样，所以
    收成一个类型内嵌进 [Forecast] 与 [TrackPoint] —— JSON 形状不变，字段
    访问也不变。
    """

    lat: str = ""
    """台风所处纬度。

    上游把数值包成字符串，这里保持字符串 —— 小数位数是上游的表达精度，
    转成浮点数会丢掉它。
    """

    lon: str = ""
    """台风所处经度。上游给的是字符串，这里保持字符串。"""

    type: str = ""
    """台风类型，如 "TS"、"TD"、"STS"。

    上游会新增类型，不要依赖枚举的完备性。
    """

    pressure: str = ""
    """台风中心气压。上游给的是字符串，这里保持字符串。"""

    wind_speed: str = ""
    """台风附近最大风速。上游给的是字符串，这里保持字符串。"""

    move_speed: str = ""
    """台风移动速度。上游给的是字符串，这里保持字符串。"""

    move_dir: str = ""
    """台风移动方位，如 "NE"。"""

    move360: str = ""
    """台风移动方位 360 度方向。上游可能是空串。"""

    wind_radius30: WindRadius | None = None
    """7 级风圈半径。台风等级不够时上游不给，这时是 None。"""

    wind_radius50: WindRadius | None = None
    """10 级风圈半径。台风等级不够时上游不给，这时是 None。"""

    wind_radius64: WindRadius | None = None
    """12 级风圈半径。台风等级不够时上游不给，这时是 None。"""


class Forecast(StormState):
    """一个预报时刻的台风状态。

    上游把台风属性平铺在预报元素里，这里按上游 JSON 一一对应，不做嵌套。
    """

    fx_time: str = ""
    """预报时刻。

    旧一代给的是本地时间字符串，如 "2021-07-27T20:00+08:00"，不是 UTC。
    """


class TrackPoint(StormState):
    """一个轨迹点的台风状态。

    上游把台风属性平铺在轨迹元素里，这里按上游 JSON 一一对应，不做嵌套。
    """

    pub_time: str = ""
    """实况发布时间。只有 "now" 元素有这个字段。

    旧一代给的是本地时间字符串，如 "2024-05-30T05:00+08:00"，不是 UTC。
    """

    time: str = ""
    """轨迹点时刻。只有 "track" 数组元素有这个字段。

    旧一代给的是本地时间字符串，如 "2024-05-29T05:00+08:00"，不是 UTC。
    """


class ListResult(QwxModel):
    """台风列表查询的结果。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。"""

    fx_link: str = ""
    """官网链接。"""

    storms: list[StormSummary] = Field(default_factory=list, alias="storm")
    """台风列表。

    上游的 "storm" 是数组，不是对象。长度不固定：一个年份里可能有几十个
    台风，也可能一个都没有。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时需要一并展示。
    """


class ForecastResult(QwxModel):
    """台风预报查询的结果。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。"""

    fx_link: str = ""
    """官网链接。"""

    forecast: list[Forecast] = Field(default_factory=list)
    """台风预报数据列表。

    台风已结束时上游返回空列表 —— 不是错误。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时需要一并展示。
    """


class TrackResult(QwxModel):
    """台风实况和路径查询的结果。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    update_time: str = ""
    """数据更新时间。"""

    fx_link: str = ""
    """官网链接。"""

    is_active: str = ""
    """活跃标记："1" 活跃台风，"0" 停编。

    上游给的是字符串，这里保持字符串，不转成 bool。
    """

    now: TrackPoint | None = None
    """当前台风实况。

    台风已结束时上游可能给 null，这时是 None。
    """

    track: list[TrackPoint] = Field(default_factory=list)
    """台风轨迹点列表。长度不固定。"""

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    上游在结果里带 refer 对象，展示这些数据时需要一并展示。
    """
