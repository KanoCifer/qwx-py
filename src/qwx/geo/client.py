"""GeoAPI 端点族的服务客户端（/geo/v2/*）。

同步与异步共用同一套端点方法体，只有发送层不同。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.location import Location
from qwx.request import Request

from .types import (
    CityResult,
    EndpointCity,
    EndpointPOI,
    EndpointPOIRange,
    EndpointTopCities,
    Options,
    POIRangeOptions,
    POIResult,
    POIType,
    RangeResult,
    TopCityResult,
)

__all__ = ["AsyncGeoService", "GeoService"]

CACHE_TTL = timedelta(hours=24)
"""GeoAPI 的默认缓存时长：地理信息几乎不变，缓存久一点。"""

_POI_TYPE_VALUES = frozenset(item.value for item in POIType)


def _poi_type_value(typ: POIType | str) -> str:
    """把 POI 类型归一成上游与缓存键都用的代码。

    闭集外的类型抛 InvalidParameterError，不打上游。
    """
    value = typ.value if isinstance(typ, POIType) else str(typ)
    if value not in _POI_TYPE_VALUES:
        raise InvalidParameterError(f"qwx: unsupported POI type {value!r}")
    return value


class _GeoCalls(Service):
    """GeoAPI 端点族的方法体。同步与异步共用。"""

    def _lookup_city_call(self, loc: Location, opts: Options | None = None) -> Any:
        """城市检索的请求参数与发送。"""
        options = opts if opts is not None else Options()
        options.lang.validate()
        params = Params(
            lang=options.lang.api,
            number=options.number,
            adm=options.adm,
            range=options.range,
        )
        query = params.query()
        query["location"] = loc.query()
        return self._call(
            Request(
                method="GET",
                path="/geo/v2/city/lookup",
                query=query,
                endpoint=EndpointCity,
                cache_key=str(Key(Family.GEO).path("city", loc.query()).params(params)),
                ttl=CACHE_TTL,
                out=CityResult,
            )
        )

    def _lookup_poi_call(
        self,
        loc: Location,
        typ: POIType | str,
        opts: Options | None = None,
    ) -> Any:
        """POI 检索的请求参数与发送。"""
        type_code = _poi_type_value(typ)
        options = opts if opts is not None else Options()
        options.lang.validate()
        params = Params(
            lang=options.lang.api,
            number=options.number,
            city=options.city,
        )
        query = params.query()
        query["location"] = loc.query()
        query["type"] = type_code
        return self._call(
            Request(
                method="GET",
                path="/geo/v2/poi/lookup",
                query=query,
                endpoint=EndpointPOI,
                cache_key=str(Key(Family.GEO).path("poi", type_code, loc.query()).params(params)),
                ttl=CACHE_TTL,
                out=POIResult,
            )
        )

    def _poi_range_call(
        self,
        loc: Location,
        typ: POIType | str,
        opts: POIRangeOptions | None = None,
    ) -> Any:
        """POI 范围检索的请求参数与发送。"""
        type_code = _poi_type_value(typ)
        if not loc.has_coordinates():
            raise InvalidLocationError("qwx: POI range requires coordinates")
        options = opts if opts is not None else POIRangeOptions()
        options.lang.validate()
        params = Params(
            lang=options.lang.api,
            number=options.number,
            radius=options.radius,
        )
        query = params.query()
        query["location"] = loc.query()
        query["type"] = type_code
        return self._call(
            Request(
                method="GET",
                path="/geo/v2/poi/range",
                query=query,
                endpoint=EndpointPOIRange,
                cache_key=str(
                    Key(Family.GEO).path("poirange", type_code, loc.query()).params(params)
                ),
                ttl=CACHE_TTL,
                out=RangeResult,
            )
        )

    def _top_cities_call(self, opts: Options | None = None) -> Any:
        """热门城市检索的请求参数与发送。"""
        options = opts if opts is not None else Options()
        options.lang.validate()
        params = Params(
            lang=options.lang.api,
            number=options.number,
            range=options.range,
        )
        return self._call(
            Request(
                method="GET",
                path="/geo/v2/city/top",
                query=params.query(),
                endpoint=EndpointTopCities,
                cache_key=str(Key(Family.GEO).path("topcity").params(params)),
                ttl=CACHE_TTL,
                out=TopCityResult,
            )
        )


class GeoService(_GeoCalls):
    """同步 GeoAPI 服务客户端。

    用基础客户端构造，无状态，可并发共享。
    """

    def lookup_city(self, loc: Location, opts: Options | None = None) -> CityResult:
        """检索城市。

        调 GET /geo/v2/city/lookup?location=...。

        loc 可以是坐标对、LocationID 或地名 —— 这是唯一认地名的接口。也支持
        坐标反查（传 "经度,纬度" 拿该点所在的城市）。

        opts.adm 限定上级行政区划（排除重名城市），opts.range 限定搜索范围，
        用 ISO 3166 国家代码，如 "cn"、"world"。留空时上游在所有城市里搜，
        查境外城市要传 "world"。

        opts.lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。

        缓存键：`qwx:geo:city:<location>` 加查询参数后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointCity] 覆盖。
        """
        return cast(CityResult, self._lookup_city_call(loc, opts))

    def lookup_poi(
        self,
        loc: Location,
        typ: POIType | str,
        opts: Options | None = None,
    ) -> POIResult:
        """检索 POI。

        调 GET /geo/v2/poi/lookup?location=...&type=...。

        loc 可以是坐标对、LocationID 或地名。typ 必填，闭集外抛
        [qwx.errors.InvalidParameterError]，不打上游。

        opts.city 限定 POI 所在城市，城市名或 LocationID。城市名是精准匹配，
        匹配不上上游返回空。

        opts.lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。

        **上游在该类型附近没有数据时回 400 "No Such Location"，而不是空列表**
        —— 这是实测行为：内陆城市（如北京）查 TSTA（潮汐站）与 CSTA（观测站）
        都会 400，沿海城市（如舟山 P2419、高雄）才查得到。调用方要按错误处理，
        不能假设"查不到就是空"。

        缓存键：`qwx:geo:poi:<type>:<location>` 加查询参数后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointPOI] 覆盖。
        """
        return cast(POIResult, self._lookup_poi_call(loc, typ, opts))

    def poi_range(
        self,
        loc: Location,
        typ: POIType | str,
        opts: POIRangeOptions | None = None,
    ) -> RangeResult:
        """检索指定坐标附近的 POI。

        调 GET /geo/v2/poi/range?location=...&type=...&radius=...。

        loc 必须是坐标对 —— 范围检索以点为中心，不认 LocationID。缺坐标时抛
        [qwx.errors.InvalidLocationError]，不打上游。

        与 [GeoService.lookup_poi] 一样，上游在该类型附近无数据时回 400
        "No Such Location"，不是空列表。

        opts.lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。

        缓存键：`qwx:geo:poirange:<type>:<location>` 加查询参数后缀（含半径）。
        半径为 0 时键里保留 `:r=0`，请求里不发 radius。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointPOIRange] 覆盖。
        """
        return cast(RangeResult, self._poi_range_call(loc, typ, opts))

    def top_cities(self, opts: Options | None = None) -> TopCityResult:
        """检索热门城市。

        调 GET /geo/v2/city/top。

        opts.range 限定搜索范围，用 ISO 3166 国家代码，如 "cn"、"world"。

        opts.lang 是语言，如 [qwx.Lang.ZH]。留空用上游默认。

        缓存键：`qwx:geo:topcity` 加查询参数后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointTopCities] 覆盖。
        """
        return cast(TopCityResult, self._top_cities_call(opts))


class AsyncGeoService(_GeoCalls):
    """异步 GeoAPI 服务客户端。

    用异步基础客户端构造，无状态，可并发共享。
    """

    async def lookup_city(self, loc: Location, opts: Options | None = None) -> CityResult:
        """检索城市。

        调 GET /geo/v2/city/lookup?location=...。

        loc 可以是坐标对、LocationID 或地名。也支持坐标反查（传
        "经度,纬度" 拿该点所在的城市）。

        缓存键：`qwx:geo:city:<location>` 加查询参数后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointCity] 覆盖。
        """
        return cast(CityResult, await self._lookup_city_call(loc, opts))

    async def lookup_poi(
        self,
        loc: Location,
        typ: POIType | str,
        opts: Options | None = None,
    ) -> POIResult:
        """检索 POI。

        调 GET /geo/v2/poi/lookup?location=...&type=...。

        typ 闭集外抛 [qwx.errors.InvalidParameterError]，不打上游。

        上游在该类型附近没有数据时回 400 "No Such Location"，不是空列表。

        缓存键：`qwx:geo:poi:<type>:<location>` 加查询参数后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointPOI] 覆盖。
        """
        return cast(POIResult, await self._lookup_poi_call(loc, typ, opts))

    async def poi_range(
        self,
        loc: Location,
        typ: POIType | str,
        opts: POIRangeOptions | None = None,
    ) -> RangeResult:
        """检索指定坐标附近的 POI。

        调 GET /geo/v2/poi/range?location=...&type=...&radius=...。

        loc 必须是坐标对，缺坐标时抛 [qwx.errors.InvalidLocationError]。

        缓存键：`qwx:geo:poirange:<type>:<location>` 加查询参数后缀（含半径）。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointPOIRange] 覆盖。
        """
        return cast(RangeResult, await self._poi_range_call(loc, typ, opts))

    async def top_cities(self, opts: Options | None = None) -> TopCityResult:
        """检索热门城市。

        调 GET /geo/v2/city/top。

        缓存键：`qwx:geo:topcity` 加查询参数后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 [EndpointTopCities] 覆盖。
        """
        return cast(TopCityResult, await self._top_cities_call(opts))
