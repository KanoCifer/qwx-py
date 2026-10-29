"""GeoAPI 端点族（/geo/v2/*）的结果类型、参数与端点常量。

GeoAPI 是唯一认地名的接口族：坐标对、LocationID、地名三种位置形态都收。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import Field

from qwx._models import QwxModel
from qwx.lang import Lang
from qwx.location import parse_location
from qwx.refer import Refer
from qwx.ttl import Endpoint

__all__ = [
    "CityResult",
    "EndpointCity",
    "EndpointPOI",
    "EndpointPOIRange",
    "EndpointTopCities",
    "Options",
    "POIRangeOptions",
    "POIResult",
    "POIType",
    "Place",
    "RangeResult",
    "TopCityResult",
]

# GeoAPI 端点的标识，用于 TTLPolicy 按端点匹配缓存时长。
#
# 常量的值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置
# 静默失效。
EndpointCity = Endpoint("geo/v2/city/lookup")
"""城市检索端点。"""

EndpointPOI = Endpoint("geo/v2/poi/lookup")
"""POI 检索端点。"""

EndpointPOIRange = Endpoint("geo/v2/poi/range")
"""POI 范围检索端点。"""

EndpointTopCities = Endpoint("geo/v2/city/top")
"""热门城市端点。"""


@dataclass(frozen=True, slots=True)
class Options:
    """GeoAPI 的可选参数。

    四个检索端点接受的参数子集不同，各端点只上报自己认的参数：行政区划
    只有城市检索认，搜索范围城市检索与热门城市认，限定城市只有 POI 检索认。
    """

    lang: Lang = Lang.UNSPECIFIED
    """语言，如 [qwx.Lang.ZH]。留空用上游默认。"""

    number: int = 0
    """返回条数上限。0 用上游默认（10）。

    上游可以给更少，SDK 不补齐。
    """

    adm: str = ""
    """上级行政区划的 LocationID，如 "101010100"。

    用于排除重名城市或过滤结果。只有城市检索认这个参数。
    """

    range: str = ""
    """搜索范围，用 ISO 3166 国家代码，如 "cn"、"world"。

    留空时上游在所有城市里搜，"world" 才能查到境外城市。城市检索与热门城市
    认这个参数。
    """

    city: str = ""
    """限定 POI 所在城市，城市名或 LocationID，如 "101010100"。

    城市名是精准匹配，匹配不上上游返回空。只有 POI 检索认这个参数。
    """


@dataclass(frozen=True, slots=True)
class POIRangeOptions:
    """POI 范围检索的可选参数。"""

    lang: Lang = Lang.UNSPECIFIED
    """语言，如 [qwx.Lang.ZH]。留空用上游默认。"""

    number: int = 0
    """返回条数上限。0 用上游默认（10）。上游可以给更少。"""

    radius: int = 0
    """搜索半径（公里）。0 用上游默认（5）。

    半径总是进缓存键：0 只进键、不上报，上游按自己的默认值处理。
    """


class POIType(str, Enum):
    """POI 检索的类型。

    闭集：传闭集外的类型抛 [qwx.errors.InvalidParameterError]，不打上游。
    上游查询串与缓存键都发代码本身。
    """

    SCENIC = "scenic"
    """景点。"""

    CSTA = "CSTA"
    """综合观测站。"""

    TSTA = "TSTA"
    """潮汐观测站。"""


class Place(QwxModel):
    """一个地点条目。

    GeoAPI 的几个检索接口（城市检索、POI 检索、热门城市）返回的条目结构
    一致，用同一个类型。

    上游把 lat/lon 给成字符串，这里原样保留，不转数字。
    """

    id: str = ""
    """LocationID。"""

    name: str = ""
    """地名（如 "东城"）。"""

    lat: str = ""
    """纬度。"""

    lon: str = ""
    """经度。"""

    adm1: str = ""
    """一级行政区（省/直辖市），如 "北京市"。"""

    adm2: str = ""
    """二级行政区（城市），如 "北京"。"""

    country: str = ""
    """国家，如 "中国"。"""

    tz: str = ""
    """时区，如 "Asia/Shanghai"。"""

    utc_offset: str = ""
    """UTC 偏移，如 "+08:00"。"""

    is_dst: str = ""
    """是否夏令时（"0" / "1"）。"""

    type: str = ""
    """地点类型，如 "city"、"scenic"。"""

    rank: str = ""
    """地点排名，数字越小越重要。"""

    fx_link: str = ""
    """该地点在和风天气官网的链接。"""

    def display_name(self) -> str:
        """拼出"城市 + 区县"形式的地点名。

        上游的字段分工是 **name=区县、adm2=城市、adm1=省/直辖市**，所以
        "城市+区县" 就是 adm2 + name —— "北京东城"、"杭州西湖"、"舟山定海"。

        城市级条目（LocationID 101010100 这类）name 与 adm2 同名，这时只留
        一份，否则会拼出"北京北京"。
        """
        name = self.name.strip()
        adm2 = self.adm2.strip()
        if not name:
            return adm2
        if not adm2:
            return name
        if name == adm2:
            return name
        if len(name) > len(adm2) and name[: len(adm2)] == adm2:
            # name 已经带上市名，不重复拼。
            return name
        return adm2 + name

    def coordinates(self) -> tuple[float, float]:
        """解析条目里的经纬度，返回 (纬度, 经度)。

        上游把 lat/lon 给成字符串，这里转成 float。字段缺失或不是数字时抛
        [qwx.errors.InvalidLocationError]。
        """
        loc = parse_location(f"{self.lon},{self.lat}")
        return loc.lat, loc.lon


class CityResult(QwxModel):
    """城市检索的结果。"""

    code: str = ""
    """上游状态码，"200" 为成功。"""

    locations: list[Place] = Field(default_factory=list, alias="location")
    """匹配到的地点。

    上游在附近没有数据时回 400 "No Such Location"，不是空列表。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。

    展示 GeoAPI 数据时要一并展示来源与许可声明。
    """


class POIResult(QwxModel):
    """POI 检索的结果。"""

    code: str = ""
    """上游状态码。"""

    pois: list[Place] = Field(default_factory=list, alias="poi")
    """匹配到的 POI。

    上游在该类型附近没有数据时回 400 "No Such Location"，不是空列表。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。"""


class RangeResult(QwxModel):
    """POI 范围检索的结果。"""

    code: str = ""
    """上游状态码。"""

    pois: list[Place] = Field(default_factory=list, alias="poi")
    """范围内的 POI。

    上游在该类型附近没有数据时回 400 "No Such Location"，不是空列表。
    """

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。"""


class TopCityResult(QwxModel):
    """热门城市检索的结果。"""

    code: str = ""
    """上游状态码。"""

    cities: list[Place] = Field(default_factory=list, alias="topCityList")
    """热门城市列表。列表长度不假设：上游可以给更少。"""

    refer: Refer = Field(default_factory=Refer)
    """数据来源与许可信息。"""
