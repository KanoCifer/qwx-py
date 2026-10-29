"""联网冒烟测试：打真实上游。

默认不参与 `pytest tests/`：测试路径只含 tests/，这里要显式跑：

    pytest live -q

需要真实凭据。两种认证任选其一：

    # API KEY
    QWX_API_KEY=xxx
    QWX_API_HOST=abcxyz.qweatherapi.com

    # 或者 JWT（私钥是 PEM 内容，也接受含字面量 \\n 转义的写法）
    QWX_JWT_PRIVATE_KEY="$(cat ed25519-private.pem)"
    QWX_KEY_ID=...
    QWX_PROJECT_ID=...
    QWX_DEVELOPER_ID=...
    QWX_API_HOST=abcxyz.qweatherapi.com

凭据不全时整个模块 skip —— CI 没凭据也不会红。
"""

from __future__ import annotations

import os

import pytest

import qwx
from qwx.geo import GeoService
from qwx.v1.airquality import AirQualityService
from qwx.v1.alert import AlertService
from qwx.v1.weather import Options, WeatherService

API_KEY = os.environ.get("QWX_API_KEY", "")
API_HOST = os.environ.get("QWX_API_HOST", "")
JWT_PRIVATE_KEY = os.environ.get("QWX_JWT_PRIVATE_KEY", "")
JWT_KEY_ID = os.environ.get("QWX_KEY_ID", "")
JWT_PROJECT_ID = os.environ.get("QWX_PROJECT_ID", "")
JWT_DEVELOPER_ID = os.environ.get("QWX_DEVELOPER_ID", "")

# 北京的坐标。新一代接口只认经纬度路径参数，纬度在前。
LOC = qwx.Location(lat=39.92, lon=116.41)


def _has_jwt() -> bool:
    """JWT 凭据是否齐全。"""
    return bool(JWT_PRIVATE_KEY and JWT_KEY_ID and JWT_PROJECT_ID and JWT_DEVELOPER_ID)


def _has_api_key() -> bool:
    """API KEY 凭据是否齐全。"""
    return bool(API_KEY)


# 缺 Host 或两种认证都没配齐就跳过整个模块。
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not API_HOST or not (_has_jwt() or _has_api_key()),
        reason="缺少联网冒烟凭据（QWX_API_HOST + QWX_API_KEY 或 QWX_JWT_*）",
    ),
]


def _auth() -> qwx.Auth:
    """按环境变量挑一种认证。JWT 齐全就用 JWT，否则用 API KEY。"""
    if _has_jwt():
        return qwx.JWTAuth(
            private_key_pem=JWT_PRIVATE_KEY,
            key_id=JWT_KEY_ID,
            project_id=JWT_PROJECT_ID,
            developer_id=JWT_DEVELOPER_ID,
        )
    return qwx.APIKeyAuth(API_KEY)


@pytest.fixture(scope="module")
def client() -> qwx.Client:
    """建一个连真实上游的客户端。"""
    base = qwx.Client(_auth(), API_HOST)
    yield base
    base.close()


def test_current_weather(client: qwx.Client) -> None:
    """实时天气。"""
    result = WeatherService(client).current(LOC, Options(lang=qwx.Lang.ZH, local_time=True))

    # 断言拿到的是模型而不是空值。
    assert result.temperature.unit != ""
    assert result.condition.text != ""
    assert 0.0 <= result.humidity <= 1.0


def test_air_quality(client: qwx.Client) -> None:
    """实时空气质量。"""
    result = AirQualityService(client).current(LOC)

    # 列表长度不假设：上游可能给得更少，但不该是 None。
    assert result.indexes is not None
    assert result.pollutants is not None


def test_geo_city_lookup(client: qwx.Client) -> None:
    """GeoAPI 城市检索（认地名）。"""
    result = GeoService(client).lookup_city(
        qwx.Location(name="北京"),
    )

    assert result.locations
    assert result.locations[0].id != ""


def test_alert(client: qwx.Client) -> None:
    """预警实况。"""
    result = AlertService(client).current(LOC)

    # 没有预警时上游给空列表，不是 null。
    assert result.alerts is not None
