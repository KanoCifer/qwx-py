"""缓存键的拼装规则。

键契约只有这一处定义：

- 族前缀的命名与代际隔离；
- 坐标的格式与顺序；
- 参数后缀的编码与顺序。

端点包只声明两件事：自己属于哪个族、有哪些影响结果的参数。同一份
`Params` 同时生成上游查询串与缓存键后缀，参数漏进键不会发生。

键的字面量在已发布版本里定死：改动会让已写入的缓存条目全部失效。
本模块只把分散的拼法收进一处，不改写任何已有键的字节。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from qwx._coord import format_coord
from qwx._upstream import (
    ADM,
    AZIMUTH,
    CITY,
    CREDENTIAL,
    EXTRA,
    INTERVAL,
    LANG,
    LOCAL_TIME,
    NUMBER,
    PROJECT,
    RADIUS,
    RANGE,
    TILT,
)

__all__ = [
    "ConsoleParams",
    "Family",
    "GeoParams",
    "Key",
    "Params",
    "SolarParams",
    "v1_params",
]


class Family(str, Enum):
    """一个资源族的键前缀根。

    两代与 GeoAPI 各用各的前缀，键不共：旧缓存不会被新解析器读到。

    前缀与包名不必对齐（潮汐族是 `qwx:tide:` 而不是 `qwx:ocean:`），
    这是已发布键字面量的约定，不要「顺手对齐」。
    """

    WEATHER = "qwx:v1:"
    AIR_QUALITY = "qwx:aq:v1:"
    ALERT = "qwx:alert:v1:"
    GEO = "qwx:geo:"
    TIDE = "qwx:tide:"
    INDICES = "qwx:indices:"
    MINUTELY = "qwx:minutely:"
    SOLAR_RADIATION = "qwx:solarradiation:v1:"
    STORM = "qwx:storm:"
    ASTRONOMY = "qwx:astronomy:"
    HISTORICAL = "qwx:historical:"
    CONSOLE = "qwx:console:"


@dataclass(frozen=True, slots=True)
class GeoParams:
    """GeoAPI 专有的查询参数。

    只有 GeoAPI 的检索端点认这几个参数。
    """

    radius: int | None = None
    """搜索半径（公里）。

    None 表示端点没有半径参数。非 None 时半径进键；半径为 0 时不发给
    上游（上游按自己的默认值处理），但仍然进键。
    """

    adm: str = ""
    """上级行政区划的 LocationID，如 "101010100"。"""

    range: str = ""
    """搜索范围，如 "cn"、"world"。"""

    city: str = ""
    """限定城市，如 "杭州"。"""


@dataclass(frozen=True, slots=True)
class SolarParams:
    """太阳辐射预报专有的查询参数。"""

    interval: int = 0
    """时间间隔分钟数，如 15、30、60。0 表示用上游默认。"""

    tilt: int | None = None
    """光伏系统的倾斜角，0~90。

    None 表示不传。非 None 时原样发给上游并进键，含 0 —— 0 是合法取值，
    不是「没传」。
    """

    azimuth: int | None = None
    """光伏系统的方位角，0~359，0 表示正北。

    None 表示不传。非 None 时原样发给上游并进键，0 是合法取值。
    """

    extra: str = ""
    """额外信息，如 "weather"、"poa"，多项用逗号分隔。"""


@dataclass(frozen=True, slots=True)
class ConsoleParams:
    """控制台专有的查询参数。"""

    project: str = ""
    """项目 ID。"""

    credential: str = ""
    """凭据 ID，与 project 互斥。"""


@dataclass(frozen=True, slots=True)
class Params:
    """一组影响结果的查询参数。

    同一份 Params 同时决定上游查询串与缓存键后缀：漏进键的参数不会出现，
    键里也不会多出上游没收到的参数。

    参数按归属分组：通用参数在顶层，只服务某个资源族的参数放进该族的
    子结构。加一个 GeoAPI 专有的参数时，动的是 `geo`，不是所有族共用的袋子。

    空值语义：

    - lang 为空：用上游默认，不上报也不进键。
    - local_time 为假：不请求当地时间，不上报也不进键。
    - number 为 0：用上游默认条数，不上报也不进键。
    """

    lang: str = ""
    local_time: bool = False
    number: int = 0
    geo: GeoParams = field(default_factory=GeoParams)
    solar: SolarParams = field(default_factory=SolarParams)
    console: ConsoleParams = field(default_factory=ConsoleParams)

    def query(self) -> dict[str, str]:
        """生成上游查询参数。"""
        out: dict[str, str] = {}
        if self.lang:
            out[LANG] = self.lang
        if self.local_time:
            out[LOCAL_TIME] = "true"
        if self.number > 0:
            out[NUMBER] = str(self.number)
        if self.geo.radius is not None and self.geo.radius > 0:
            out[RADIUS] = str(self.geo.radius)
        if self.geo.adm:
            out[ADM] = self.geo.adm
        if self.geo.range:
            out[RANGE] = self.geo.range
        if self.geo.city:
            out[CITY] = self.geo.city
        if self.solar.interval > 0:
            out[INTERVAL] = str(self.solar.interval)
        if self.solar.tilt is not None:
            out[TILT] = str(self.solar.tilt)
        if self.solar.azimuth is not None:
            out[AZIMUTH] = str(self.solar.azimuth)
        if self.solar.extra:
            out[EXTRA] = self.solar.extra
        if self.console.project:
            out[PROJECT] = self.console.project
        if self.console.credential:
            out[CREDENTIAL] = self.console.credential
        return out

    def suffix(self) -> str:
        """参数对缓存键的影响片段。

        顺序固定：语言 → 本地时间 → 条数 → 半径 → 行政区划 → 搜索范围 →
        城市 → 时间间隔 → 倾斜角 → 方位角 → 额外信息 → 项目 → 凭据。
        已发布的键字面量按这个顺序排，改动会让旧缓存条目失效。

        族专有的参数追加在通用参数之后：老调用方不设它们，键的字节与发布
        时完全一致。
        """
        parts: list[str] = []
        if self.lang:
            parts.append(f":{LANG}={self.lang}")
        if self.local_time:
            parts.append(f":{LOCAL_TIME}=1")
        if self.number > 0:
            parts.append(f":n={self.number}")
        if self.geo.radius is not None:
            parts.append(f":r={self.geo.radius}")
        if self.geo.adm:
            parts.append(f":{ADM}={self.geo.adm}")
        if self.geo.range:
            parts.append(f":{RANGE}={self.geo.range}")
        if self.geo.city:
            parts.append(f":{CITY}={self.geo.city}")
        if self.solar.interval > 0:
            parts.append(f":{INTERVAL}={self.solar.interval}")
        if self.solar.tilt is not None:
            parts.append(f":{TILT}={self.solar.tilt}")
        if self.solar.azimuth is not None:
            parts.append(f":{AZIMUTH}={self.solar.azimuth}")
        if self.solar.extra:
            parts.append(f":{EXTRA}={self.solar.extra}")
        if self.console.project:
            parts.append(f":{PROJECT}={self.console.project}")
        if self.console.credential:
            parts.append(f":{CREDENTIAL}={self.console.credential}")
        return "".join(parts)


def v1_params(lang: str, local_time: bool) -> Params:
    """构造新一代端点族共用的参数集。

    天气与预警两个端点族接受同一组可选参数：语言与当地时间。映射只在这里
    写一次 —— 新增第三个共用这组参数的端点族时也走这里。
    """
    return Params(lang=lang, local_time=local_time)


class Key:
    """拼装一个缓存键。

    形状固定：族前缀 + 位置段 + 参数段。位置段按追加顺序拼接，参数段
    固定排在最后，顺序由 `Params` 决定。
    """

    __slots__ = ("_family", "_params", "_segments")

    def __init__(self, family: Family) -> None:
        self._family = family
        self._segments: list[str] = []
        self._params = Params()

    def path(self, *segments: str) -> Key:
        """追加位置段，如端点名、地点 ID、站点 ID、日期。

        段之间用冒号连接，顺序按追加顺序。空串也是一段：不跳过，位置缺失
        时键里要留下同样的形状。
        """
        self._segments.extend(segments)
        return self

    def path_coord(self, lat: float, lon: float) -> Key:
        """追加坐标位置段，纬度在前。

        新一代（`/weather/v1/*` 等）的路径参数是纬度在前，写反了上游回 400。
        坐标统一两位小数，负零归一为 0.00。
        """
        self._segments.append(f"{format_coord(lat)},{format_coord(lon)}")
        return self

    def count(self, name: str, number: int) -> Key:
        """追加计数段，如 `h24`。

        计数总是进键：条数不同是不同数据，共键就是串味。计数段排在参数段之前。
        """
        self._segments.append(f"{name}{number}")
        return self

    def params(self, params: Params) -> Key:
        """追加影响结果的查询参数后缀。"""
        self._params = params
        return self

    def __str__(self) -> str:
        return self._family.value + ":".join(self._segments) + self._params.suffix()
