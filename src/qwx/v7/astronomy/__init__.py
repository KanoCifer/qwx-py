"""旧一代天文数据接口（/v7/astronomy/*）。

导出本族公开符号：模型、端点常量与服务客户端。
"""

from __future__ import annotations

from qwx.v7.astronomy.client import AstronomyService, AsyncAstronomyService
from qwx.v7.astronomy.types import (
    AngleResult,
    EndpointAngle,
    EndpointMoon,
    EndpointSun,
    MoonPhase,
    MoonResult,
    Options,
    SunResult,
)

__all__ = [
    "AngleResult",
    "AstronomyService",
    "AsyncAstronomyService",
    "EndpointAngle",
    "EndpointMoon",
    "EndpointSun",
    "MoonPhase",
    "MoonResult",
    "Options",
    "SunResult",
]
