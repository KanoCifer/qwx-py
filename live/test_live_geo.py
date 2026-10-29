"""GeoAPI 端点族的联网冒烟测试。

打真实上游，覆盖 /geo/v2/* 的四个端点：城市检索、POI 检索、POI 范围检索、
热门城市；外加地名检索 —— GeoAPI 是唯一认地名的接口族，单独验。

需要真实凭据，跑法：

    pytest live -q

POI 两个端点在内陆城市附近可能没有数据，上游回 400 "No Such Location"
而不是空列表，这种情况 skip，不算失败。
"""

from __future__ import annotations

import pytest
from conftest import LOC, requires_credentials

import qwx
from qwx.geo import GeoService, Options, POIRangeOptions, POIType

pytestmark = [pytest.mark.live, requires_credentials]

# 北京的行政区划 LocationID。
BEIJING_ID = "101010100"


@pytest.fixture(scope="module")
def geo(client: qwx.Client) -> GeoService:
    """GeoAPI 的同步服务客户端。"""
    return GeoService(client)


def _skip_no_poi(exc: qwx.UpstreamRejectedError) -> None:
    """上游在该类型附近没有 POI 时回 400，skip 掉这个用例。

    实测行为：内陆城市（如北京）查景点、观测站、潮汐站都可能 400，沿海
    城市才查得到。查不到不等于调用失败，按上游的实际语义跳过。
    """
    pytest.skip(f"该坐标附近没有 POI，上游拒绝：{exc}")


def test_lookup_city_by_location_id(geo: GeoService) -> None:
    """按 LocationID 检索城市。

    断言检索到地点，且第一条的 id 与地名都非空 —— 只断言列表非空时，
    上游回一堆字段全空的条目也能过。
    """
    result = geo.lookup_city(qwx.Location(id=BEIJING_ID), Options(lang=qwx.Lang.ZH))

    assert result.locations is not None
    assert len(result.locations) > 0, "按 LocationID 检索城市没有返回任何地点"

    first = result.locations[0]
    assert first.id, "第一条地点的 LocationID 为空"
    assert first.name, "第一条地点的地名为空"
    assert first.lat and first.lon, "第一条地点缺少坐标"


def test_lookup_city_by_name(geo: GeoService) -> None:
    """按地名检索城市。

    GeoAPI 是唯一认地名的接口族：新一代与 v7 都只收坐标对与 LocationID。
    所以这条单独验，且断言结果里确实有"北京"，防止地名被静默忽略后
    退化成别的检索。
    """
    result = geo.lookup_city(qwx.Location(name="北京"), Options(lang=qwx.Lang.ZH))

    assert result.locations is not None
    assert len(result.locations) > 0, "按地名检索城市没有返回任何地点"

    first = result.locations[0]
    assert first.id, "第一条地点的 LocationID 为空"
    assert "北京" in (first.name + first.adm2), f"结果里没有北京：{first.name}/{first.adm2}"


def test_lookup_poi(geo: GeoService) -> None:
    """按坐标检索景点 POI。

    上游在附近没有该类型的 POI 时回 400，不是空列表，这种情况下 skip。
    """
    try:
        result = geo.lookup_poi(LOC, POIType.SCENIC, Options(lang=qwx.Lang.ZH))
    except qwx.UpstreamRejectedError as exc:
        _skip_no_poi(exc)
        return

    assert result.pois is not None
    assert len(result.pois) > 0, "检索景点 POI 没有返回任何条目"

    first = result.pois[0]
    assert first.id, "第一条 POI 的 LocationID 为空"
    assert first.name, "第一条 POI 的名称为空"


def test_poi_range(geo: GeoService) -> None:
    """按坐标检索附近的景点 POI，半径 20 公里。

    与检索 POI 一样，附近没有该类型时上游回 400，这种情况下 skip。
    """
    try:
        result = geo.poi_range(LOC, POIType.SCENIC, POIRangeOptions(lang=qwx.Lang.ZH, radius=20))
    except qwx.UpstreamRejectedError as exc:
        _skip_no_poi(exc)
        return

    assert result.pois is not None
    assert len(result.pois) > 0, "范围检索景点 POI 没有返回任何条目"

    first = result.pois[0]
    assert first.id, "第一条 POI 的 LocationID 为空"
    assert first.name, "第一条 POI 的名称为空"


def test_top_cities(geo: GeoService) -> None:
    """检索热门城市。"""
    result = geo.top_cities(Options(lang=qwx.Lang.ZH))

    assert result.cities is not None
    assert len(result.cities) > 0, "热门城市列表为空"

    first = result.cities[0]
    assert first.id, "第一条热门城市的 LocationID 为空"
    assert first.name, "第一条热门城市的名称为空"
