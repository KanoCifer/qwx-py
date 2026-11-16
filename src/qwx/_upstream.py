"""上游查询参数名。

上游查询参数名的唯一真源：端点包用它拼查询参数，缓存键拼装用它生成参数
段。上游改名时只改这里。

零依赖：不 import 其它模块，谁都能用。
"""

from __future__ import annotations

__all__ = [
    "ADM",
    "ALTITUDE",
    "AZIMUTH",
    "BASIN",
    "CITY",
    "CREDENTIAL",
    "DATE",
    "DAYS",
    "EXTRA",
    "HOURS",
    "INTERVAL",
    "LANG",
    "LOCAL_TIME",
    "LOCATION",
    "NUMBER",
    "PROJECT",
    "RADIUS",
    "RANGE",
    "STORM_ID",
    "TILT",
    "TIME",
    "TIMEZONE",
    "TYPE",
    "YEAR",
]

LANG = "lang"
"""语言代码，如 "zh"、"en"。"""

LOCAL_TIME = "localTime"
"""是否请求当地时间。"""

NUMBER = "number"
"""返回条数上限。"""

RADIUS = "radius"
"""搜索半径（公里）。"""

ADM = "adm"
"""上级行政区划的 LocationID。"""

RANGE = "range"
"""搜索范围，如 "cn"、"world"。"""

CITY = "city"
"""限定城市。"""

INTERVAL = "interval"
"""时间间隔分钟数。"""

TILT = "tilt"
"""光伏系统的倾斜角。"""

AZIMUTH = "azimuth"
"""光伏系统的方位角。"""

EXTRA = "extra"
"""额外信息，如 "weather"、"poa"。"""

PROJECT = "project"
"""项目 ID。"""

CREDENTIAL = "credential"
"""凭据 ID。"""

LOCATION = "location"
"""位置，取值如 "116.41,39.92"、"101010100"、"P2352"。"""

DATE = "date"
"""日期，格式 yyyyMMdd。"""

TYPE = "type"
"""类型，取值随端点族而异。"""

HOURS = "hours"
"""预报小时数。"""

DAYS = "days"
"""预报天数。"""

TIME = "time"
"""时刻，格式 HHmm。"""

TIMEZONE = "tz"
"""时区偏移，格式 HHmm。"""

ALTITUDE = "alt"
"""海拔高度（米）。"""

BASIN = "basin"
"""台风流域代码。"""

YEAR = "year"
"""年份。"""

STORM_ID = "stormid"
"""台风 ID。"""
