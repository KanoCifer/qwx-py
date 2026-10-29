"""旧一代 v7 六个端点族的联网冒烟测试。

打真实上游，默认不参与 `pytest tests/`，要显式跑：

    pytest live -q

覆盖天文、历史天气、生活指数、分钟级降水、台风、潮汐六族，每族一个用例。

上游怪癖在本文件里被显式处理：

- 天文的日期最多接受未来 60 天（含今天），今天一定在范围内。
- 历史天气只给最近 10 天、**不含今天**的数据，所以查昨天。
- 生活指数的 days 只支持 1 与 3。
- 分钟级降水只覆盖中国区域，境外坐标上游没有数据，所以用北京坐标。
- 台风列表可能是一个空列表，不能断言非空。
- 潮汐的 date 必须是**站点当地当天**。用 UTC 日期在北京时间 00:00–08:00
  会落到「昨天」，上游回 400；潮汐窗口未开放时上游也回 400。这种情况
  跳过本用例，不让整个套件变红。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from conftest import LOC, requires_credentials

import qwx
from qwx.v7.astronomy import AstronomyService
from qwx.v7.historical import HistoricalService
from qwx.v7.indices import IndicesService
from qwx.v7.minutely import MinutelyService
from qwx.v7.ocean import OceanService
from qwx.v7.storm import StormService

pytestmark = [pytest.mark.live, requires_credentials]

SHANGHAI = ZoneInfo("Asia/Shanghai")
"""站点与生活指数所在时区。用它算「今天」，不用 UTC 日期。"""

TIDE_STATION = "P2352"
"""潮汐站 ID。潮汐端点只认站 ID，不认坐标、不认 LocationID。"""

HISTORICAL_LOCATION_ID = "101010100"
"""北京的城市 LocationID。历史天气端点只认 LocationID。"""


def today() -> str:
    """北京当地的今天，"yyyyMMdd"。"""
    return datetime.now(SHANGHAI).strftime("%Y%m%d")


def yesterday() -> str:
    """北京当地的昨天，"yyyyMMdd"。"""
    return (datetime.now(SHANGHAI) - timedelta(days=1)).strftime("%Y%m%d")


def current_year() -> int:
    """北京当地的当前年份。"""
    return datetime.now(SHANGHAI).year


def test_astronomy(client: qwx.Client) -> None:
    """天文三端点：日出日落、月升月落、太阳高度角。"""
    service = AstronomyService(client)
    date = today()

    sun = service.sun(LOC, date)
    assert sun.code == "200"
    # 高纬度与极昼极夜地区上游给 null：日出与日落要么都有值，要么都是 None。
    assert (sun.sunrise is None) == (sun.sunset is None)
    if sun.sunrise is not None:
        assert sun.sunrise
        assert sun.sunset

    moon = service.moon(LOC, date)
    assert moon.code == "200"
    assert moon.moon_phase is not None
    # 月升月落同样可能为空，但两者要么都有要么都无。
    assert (moon.moonrise is None) == (moon.moonset is None)

    angle = service.solar_elevation_angle(LOC, date, "1200", "0800", 43)
    assert angle.code == "200"
    # 角度字段必须真能解析成数值，空串说明上游没给数据。
    assert angle.solar_elevation_angle
    float(angle.solar_elevation_angle)
    assert angle.solar_azimuth_angle
    float(angle.solar_azimuth_angle)


def test_historical(client: qwx.Client) -> None:
    """历史天气：查昨天，只认 LocationID。"""
    service = HistoricalService(client)
    result = service.weather(qwx.Location(id=HISTORICAL_LOCATION_ID), yesterday())
    assert result.code == "200"
    assert result.daily is not None
    assert result.daily.date
    assert result.hourly is not None


def test_indices(client: qwx.Client) -> None:
    """生活指数：单类型与多类型，days 只支持 1 与 3。"""
    service = IndicesService(client)

    single = service.indices(LOC, 4, 1)
    assert single.code == "200"
    assert single.daily is not None

    multi = service.indices_multi(LOC, [3, 4], 3)
    assert multi.code == "200"
    assert multi.daily is not None


def test_minutely(client: qwx.Client) -> None:
    """分钟级降水：只覆盖中国区域，用北京坐标。"""
    service = MinutelyService(client)
    result = service.minutely(LOC)
    assert result.code == "200"
    assert result.minutely is not None
    # 列表长度不假设：上游可能给 0 条，也可能给满 24 条。
    for item in result.minutely:
        assert item.fx_time


def test_storm(client: qwx.Client) -> None:
    """台风列表：按流域与年份检索，与查询地点无关。"""
    service = StormService(client)
    result = service.list("NP", current_year())
    assert result.code == "200"
    # 台风列表可能一个都没有，不能断言非空。
    assert result.storms is not None


def test_ocean(client: qwx.Client) -> None:
    """潮汐：站点当地当天。窗口未开放或日期落在昨天时上游回 400，跳过。"""
    service = OceanService(client)
    date = today()
    try:
        result = service.tide(TIDE_STATION, date)
    except qwx.UpstreamRejectedError:
        pytest.skip("潮汐窗口未开放或站点当地日期与 UTC 不一致")
    except qwx.UpstreamError as exc:
        if exc.status_code == 400:
            pytest.skip("潮汐窗口未开放或站点当地日期与 UTC 不一致")
        raise

    assert result.code == "200"
    assert result.tide_table is not None
    assert result.tide_hourly is not None
    for tide in result.tide_table:
        assert tide.fx_time
        assert tide.height
