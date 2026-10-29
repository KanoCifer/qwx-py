"""GeoAPI 城市/POI 检索端点族（/geo/v2/*）。

GeoAPI 是唯一认地名的接口族：坐标对、LocationID、地名三种位置形态都收。
"""

from __future__ import annotations

from .client import AsyncGeoService, GeoService
from .types import (
    CityResult,
    EndpointCity,
    EndpointPOI,
    EndpointPOIRange,
    EndpointTopCities,
    Options,
    Place,
    POIRangeOptions,
    POIResult,
    POIType,
    RangeResult,
    TopCityResult,
)

__all__ = [
    "AsyncGeoService",
    "CityResult",
    "EndpointCity",
    "EndpointPOI",
    "EndpointPOIRange",
    "EndpointTopCities",
    "GeoService",
    "Options",
    "POIRangeOptions",
    "POIResult",
    "POIType",
    "Place",
    "RangeResult",
    "TopCityResult",
]
