"""quick 组合层的联网冒烟测试。

打到真实上游，断言快速查询拿得到数据。

    pytest live -q

需要真实凭据（QWX_API_HOST + QWX_API_KEY 或 QWX_JWT_*）。缺凭据时整份
文件跳过，不会红。
"""

from __future__ import annotations

import pytest
from conftest import LOC, requires_credentials

import qwx
from qwx.quick import Options, Part, QuickService

pytestmark = [pytest.mark.live, requires_credentials]


def test_quick_by_coordinates(client: qwx.Client) -> None:
    """坐标查询：五块并发取，天气与预报必须拿到。"""
    report = QuickService(client).query(LOC, Options(lang=qwx.Lang.ZH, local_time=True))

    assert report.current is not None
    assert report.current.temperature.unit, "温度必须带单位"
    assert report.hourly is not None
    assert report.hourly.hours, "逐小时预报不应为空"
    assert report.daily is not None
    assert report.daily.days, "逐日预报不应为空"
    # 空气质量与预警看账号权限，允许失败；天气那块失败才算问题。
    assert all(error.part is not Part.CURRENT for error in report.errors)


def test_quick_by_city_name(client: qwx.Client) -> None:
    """地名查询：先查 GeoAPI 换坐标，再取数据。"""
    report = QuickService(client).query("北京", Options(lang=qwx.Lang.ZH))

    assert report.place is not None
    assert report.place.display_name()
    assert report.location.has_coordinates()
    assert report.current is not None


def test_quick_skips_parts(client: qwx.Client) -> None:
    """跳过空气质量与预警：这两块没权限也不影响其余。"""
    report = QuickService(client).query(
        LOC,
        Options(
            lang=qwx.Lang.ZH,
            skip=(Part.AIR_QUALITY, Part.ALERTS),
        ),
    )

    assert report.air_quality is None
    assert report.alerts is None
    assert report.current is not None
    assert report.errors == ()
