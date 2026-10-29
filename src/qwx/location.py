"""查询位置。

和风天气的位置有三种形态，收敛到这一个类型：

- 坐标对：116.41,39.92（经度在前）
- LocationID：101010100（行政区划）、10101010012A（POI）、P2352（潮汐站）
- 地名：仅 GeoAPI 认

两代的位置形态不同：新一代接口用 path()，纬度在前；v7 与 GeoAPI 用
query()，经度在前。写反了上游直接回 400。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from qwx._coord import format_coord, round_coord
from qwx.errors import InvalidLocationError

__all__ = ["LOCATION_ID_RE", "Location", "parse_location"]

# LocationID 的形态：行政区划是 9~10 位纯数字（101010100），POI 是数字
# 加字母后缀（10101010012A），潮汐站点是字母 P 打头（P2352）。
#
# 不含小数点：裸经度（121.47）三种形态都不沾，上游直接回 400。
LOCATION_ID_RE = re.compile(r"^[A-Za-z]?[0-9]{4,}[A-Za-z]?$")


@dataclass(frozen=True, slots=True)
class Location:
    """一个查询位置。

    id 与 lat/lon 二选一。name 只被 GeoAPI 的城市与 POI 检索认。
    """

    id: str = ""
    name: str = ""
    lat: float = 0.0
    lon: float = 0.0

    def has_coordinates(self) -> bool:
        """该位置是否带坐标。"""
        return self.lat != 0 or self.lon != 0

    def is_zero(self) -> bool:
        """该位置是否为空。"""
        return self.id == "" and self.name == "" and not self.has_coordinates()

    def query(self) -> str:
        """v7 与 GeoAPI 的 location 查询参数形态：经度在前。

        优先用坐标，其次 LocationID，最后地名。都没有时返回空串。
        """
        if self.has_coordinates():
            return f"{format_coord(self.lon)},{format_coord(self.lat)}"
        if self.id:
            return self.id
        return self.name

    def coordinates(self) -> tuple[float, float]:
        """归一化后的坐标（两位小数），返回 (纬度, 经度)。"""
        if not self.has_coordinates():
            raise InvalidLocationError("qwx: location has no coordinates")
        return round_coord(self.lat), round_coord(self.lon)

    def path(self) -> tuple[str, str]:
        """新一代接口路径里的坐标分量，返回 (纬度, 经度)。

        这是和风天气接入最容易踩的坑：旧接口用经度,纬度 查询参数，新接口
        是 {latitude}/{longitude} 路径参数。写反了上游回 400
        invalidParams:["longitude","latitude"]，不会静默返回别处。
        """
        lat, lon = self.coordinates()
        return format_coord(lat), format_coord(lon)


def parse_location(raw: str) -> Location:
    """解析 location 字符串，识别坐标对与 LocationID。

    识别不了形态时抛 InvalidLocationError。
    """
    text = raw.strip()
    if not text:
        raise InvalidLocationError("qwx: empty location")
    if "," in text:
        lat, lon = _parse_coordinate_pair(text)
        return Location(lat=lat, lon=lon)
    if LOCATION_ID_RE.match(text):
        return Location(id=text)
    raise InvalidLocationError(f"qwx: {raw!r} is neither a coordinate pair nor a LocationID")


def _parse_coordinate_pair(text: str) -> tuple[float, float]:
    """解析 经度,纬度 并做范围校验，返回 (纬度, 经度)。"""
    parts = text.split(",")
    if len(parts) != 2:
        raise InvalidLocationError(f"qwx: {text!r} is not a coordinate pair")
    try:
        lon = float(parts[0].strip())
    except ValueError:
        raise InvalidLocationError(f"qwx: {text!r} has a non-numeric longitude") from None
    try:
        lat = float(parts[1].strip())
    except ValueError:
        raise InvalidLocationError(f"qwx: {text!r} has a non-numeric latitude") from None
    # float 接受 nan 与 inf，它们能过范围比较（nan 的任何比较都是 False），
    # 落到上游就是又一次 400，这里显式挡掉。
    if math.isnan(lon) or math.isnan(lat) or math.isinf(lon) or math.isinf(lat):
        raise InvalidLocationError(f"qwx: {text!r} contains NaN or Inf")
    if lon < -180 or lon > 180:
        raise InvalidLocationError(f"qwx: longitude {lon} out of range [-180,180]")
    if lat < -90 or lat > 90:
        raise InvalidLocationError(f"qwx: latitude {lat} out of range [-90,90]")
    return lat, lon
