"""新一代接口（/weather/v1/*、/airquality/v1/*、/weatheralert/v1/*、
/solarradiation/v1/*）的共享类型。

端点族在各自的子包里：qwx.v1.weather、qwx.v1.airquality、qwx.v1.alert、
qwx.v1.solarradiation。
"""

from __future__ import annotations

from qwx.v1.types import Metadata, Options, Value

__all__ = ["Metadata", "Options", "Value"]
