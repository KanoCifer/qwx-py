"""快速查询层（组合层）的类型。

quick 不是上游资源族：它把 GeoAPI 城市检索、新一代天气、空气质量与预警
几个端点组合成一次查询，按位置一次取齐数据。

与 Go 版（https://github.com/KanoCifer/qwx）的 quick 包语义对等。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from qwx.errors import QwxError
from qwx.geo.types import Place
from qwx.lang import Lang
from qwx.location import Location
from qwx.ttl import Endpoint
from qwx.v1.airquality.types import Current as AirQualityCurrent
from qwx.v1.alert.types import Result as AlertResult
from qwx.v1.weather.types import CurrentWeather, DailyForecast, HourlyForecast

__all__ = [
    "DEFAULT_DAYS",
    "DEFAULT_HOURS",
    "EndpointError",
    "Options",
    "Part",
    "Report",
]

DEFAULT_HOURS = 24
"""逐小时预报的默认小时数。"""

DEFAULT_DAYS = 3
"""逐日预报的默认天数。"""


class Part(str, Enum):
    """报告里的一块数据。

    用它跳过不关心的部分：一次快速查询默认取齐五块，账号没开通某项权限
    时也可以直接跳过。
    """

    CURRENT = "current"
    """实时天气。"""

    HOURLY = "hourly"
    """逐小时预报。"""

    DAILY = "daily"
    """逐日预报。"""

    AIR_QUALITY = "airquality"
    """实时空气质量。"""

    ALERTS = "alerts"
    """预警。"""


@dataclass(frozen=True, slots=True)
class Options:
    """快速查询的可选参数。

    它把各端点各自的参数收在一处：语言对五块数据都生效，当地时间只对天气
    与预警生效（上游的空气质量没有当地时间参数），逐时逐日的条数只对预报
    生效，行政区划与搜索范围只对地名解析生效。
    """

    lang: Lang = Lang.UNSPECIFIED
    """语言，如 [qwx.Lang.ZH]。留空用上游默认。"""

    local_time: bool = False
    """是否返回查询地点的当地时间。

    新一代接口默认给 UTC，不传本地时间会整整差 8 小时。

    只对天气与预警生效：上游的空气质量接口没有当地时间参数，
    [Report.air_quality] 的时间始终是 UTC。
    """

    hours: int = 0
    """逐小时预报的小时数。0 用 [DEFAULT_HOURS]。

    取值 1~240，超出范围抛 [qwx.errors.InvalidParameterError]，不打上游。
    """

    days: int = 0
    """逐日预报的天数。0 用 [DEFAULT_DAYS]。

    取值 1~10，超出范围抛 [qwx.errors.InvalidParameterError]，不打上游。
    """

    number: int = 0
    """城市检索返回条数上限。0 用上游默认（10）。

    只在位置是地名或 LocationID 时起作用。
    """

    adm: str = ""
    """上级行政区划的 LocationID，如 "101010100"。

    用于排除重名城市。只在位置是地名或 LocationID 时起作用。
    """

    range: str = ""
    """城市检索的搜索范围，用 ISO 3166 国家代码，如 "cn"、"world"。

    留空时上游在所有城市里搜，"world" 才能查到境外城市。只在位置是地名或
    LocationID 时起作用。
    """

    skip: tuple[Part, ...] = ()
    """要跳过的数据块。留空表示五块全取。

    写未知的数据块抛 [qwx.errors.InvalidParameterError]，不打上游。
    """

    strict: bool = False
    """是否遇到任何一块失败就整体失败。

    默认 False：失败的那块记进 [Report.errors]，其余照常返回 —— 账号没开通
    空气质量权限时，预警和天气仍然拿得到。开了之后第一块失败就抛异常，
    报告拿不到。
    """


class EndpointError(QwxError):
    """某一块数据的失败原因。

    严格模式（[Options.strict]）或全部取回失败时抛出。原始异常在
    [EndpointError.error]，异常链（__cause__）也指向它 —— 用 isinstance
    判断类别，不要去解析错误字符串。
    """

    def __init__(self, part: Part, endpoint: Endpoint, error: BaseException) -> None:
        self.part = part
        """失败的数据块。"""

        self.endpoint = endpoint
        """失败的上游端点标识，如 [qwx.Endpoint]。"""

        self.error = error
        """原始异常。"""

        super().__init__(f"qwx: quick {part.value} endpoint {endpoint} failed: {error}")
        self.__cause__ = error


@dataclass(frozen=True, slots=True)
class Report:
    """一次快速查询的结果。

    取到的每一块各自独立：某块失败不影响其他块，失败原因在
    [Report.errors]。没取到的块对应字段为 None。
    """

    location: Location
    """最终查询用的坐标位置。

    传坐标时就是它本身；传地名或 LocationID 时是解析出来的坐标。
    """

    place: Place | None = None
    """地名解析的结果。传坐标时为 None。"""

    current: CurrentWeather | None = None
    """实时天气。没取到时为 None。"""

    hourly: HourlyForecast | None = None
    """逐小时预报。没取到时为 None。"""

    daily: DailyForecast | None = None
    """逐日预报。没取到时为 None。"""

    air_quality: AirQualityCurrent | None = None
    """实时空气质量。没取到时为 None。"""

    alerts: AlertResult | None = None
    """预警。没取到时为 None。

    查得到但没有预警时是空列表，不是 None。
    """

    errors: tuple[EndpointError, ...] = ()
    """失败的数据块。

    严格模式（[Options.strict]）下它恒为空 —— 失败会直接抛异常。
    """
