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

from dataclasses import dataclass
from enum import Enum

from qwx._coord import format_coord


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


@dataclass(frozen=True)
class Params:
    """一组影响结果的查询参数。

    同一份 Params 同时决定上游查询串与缓存键后缀：漏进键的参数不会出现，
    键里也不会多出上游没收到的参数。

    空值语义：

    - lang 为空：用上游默认，不上报也不进键。
    - local_time 为假：不请求当地时间，不上报也不进键。
    - number 为 0：用上游默认条数，不上报也不进键。
    - radius 为 None：端点没有半径参数。非 None 时半径进键；半径为 0
      只进键、不上报，上游按自己的默认值处理。
    - tilt 与 azimuth 为 None：端点没有这两个参数。非 None 时进键并上报，
      含 0 —— 0 是合法取值，不是「没传」。
    """

    lang: str = ""
    local_time: bool = False
    number: int = 0
    radius: int | None = None
    adm: str = ""
    range: str = ""
    city: str = ""
    interval: int = 0
    tilt: int | None = None
    azimuth: int | None = None
    extra: str = ""
    project: str = ""
    credential: str = ""

    def query(self) -> dict[str, str]:
        """生成上游查询参数。"""
        out: dict[str, str] = {}
        if self.lang:
            out["lang"] = self.lang
        if self.local_time:
            out["localTime"] = "true"
        if self.number > 0:
            out["number"] = str(self.number)
        if self.radius is not None and self.radius > 0:
            out["radius"] = str(self.radius)
        if self.adm:
            out["adm"] = self.adm
        if self.range:
            out["range"] = self.range
        if self.city:
            out["city"] = self.city
        if self.interval > 0:
            out["interval"] = str(self.interval)
        if self.tilt is not None:
            out["tilt"] = str(self.tilt)
        if self.azimuth is not None:
            out["azimuth"] = str(self.azimuth)
        if self.extra:
            out["extra"] = self.extra
        if self.project:
            out["project"] = self.project
        if self.credential:
            out["credential"] = self.credential
        return out

    def suffix(self) -> str:
        """参数对缓存键的影响片段。

        顺序固定：语言 → 本地时间 → 条数 → 半径 → 行政区划 → 搜索范围 →
        城市 → 时间间隔 → 倾斜角 → 方位角 → 额外信息 → 项目 → 凭据。
        已发布的键字面量按这个顺序排，改动会让旧缓存条目失效。
        """
        parts: list[str] = []
        if self.lang:
            parts.append(f":lang={self.lang}")
        if self.local_time:
            parts.append(":localTime=1")
        if self.number > 0:
            parts.append(f":n={self.number}")
        if self.radius is not None:
            parts.append(f":r={self.radius}")
        if self.adm:
            parts.append(f":adm={self.adm}")
        if self.range:
            parts.append(f":range={self.range}")
        if self.city:
            parts.append(f":city={self.city}")
        if self.interval > 0:
            parts.append(f":interval={self.interval}")
        if self.tilt is not None:
            parts.append(f":tilt={self.tilt}")
        if self.azimuth is not None:
            parts.append(f":azimuth={self.azimuth}")
        if self.extra:
            parts.append(f":extra={self.extra}")
        if self.project:
            parts.append(f":project={self.project}")
        if self.credential:
            parts.append(f":credential={self.credential}")
        return "".join(parts)


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
