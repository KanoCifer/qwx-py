"""联网冒烟测试的共用装置。

各端点族的冒烟文件从这里取凭据、Host 与客户端装置；凭据不全时整份文件
skip —— CI 没凭据也不会红。

    pytest live -q

需要真实凭据，两种认证任选其一：

    # API KEY
    QWX_API_KEY=xxx
    QWX_API_HOST=abcxyz.qweatherapi.com

    # 或者 JWT（私钥是 PEM 内容，也接受含字面量反斜杠 n 转义的写法）
    QWX_JWT_PRIVATE_KEY="$(cat ed25519-private.pem)"
    QWX_KEY_ID=...
    QWX_PROJECT_ID=...
    QWX_DEVELOPER_ID=...
    QWX_API_HOST=abcxyz.qweatherapi.com
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

import qwx

API_KEY = os.environ.get("QWX_API_KEY", "")
API_HOST = os.environ.get("QWX_API_HOST", "")
JWT_PRIVATE_KEY = os.environ.get("QWX_JWT_PRIVATE_KEY", "")
JWT_KEY_ID = os.environ.get("QWX_KEY_ID", "")
JWT_PROJECT_ID = os.environ.get("QWX_PROJECT_ID", "")
JWT_DEVELOPER_ID = os.environ.get("QWX_DEVELOPER_ID", "")

# 北京的坐标。新一代接口只认经纬度路径参数，纬度在前。
LOC = qwx.Location(lat=39.92, lon=116.41)


def has_jwt() -> bool:
    """JWT 凭据是否齐全。"""
    return bool(JWT_PRIVATE_KEY and JWT_KEY_ID and JWT_PROJECT_ID and JWT_DEVELOPER_ID)


def has_api_key() -> bool:
    """API KEY 凭据是否齐全。"""
    return bool(API_KEY)


def credentials_ready() -> bool:
    """Host 与至少一种认证是否就绪。"""
    return bool(API_HOST) and (has_jwt() or has_api_key())


def build_auth() -> qwx.Auth:
    """按环境变量挑一种认证。JWT 齐全就用 JWT，否则用 API KEY。"""
    if has_jwt():
        return qwx.JWTAuth(
            private_key_pem=JWT_PRIVATE_KEY,
            key_id=JWT_KEY_ID,
            project_id=JWT_PROJECT_ID,
            developer_id=JWT_DEVELOPER_ID,
        )
    return qwx.APIKeyAuth(API_KEY)


# 缺 Host 或两种认证都没配齐就跳过整份文件。
requires_credentials = pytest.mark.skipif(
    not credentials_ready(),
    reason="缺少联网冒烟凭据（QWX_API_HOST + QWX_API_KEY 或 QWX_JWT_*）",
)


@pytest.fixture(scope="module")
def client() -> Iterator[qwx.Client]:
    """连真实上游的同步客户端。"""
    base = qwx.Client(build_auth(), API_HOST)
    yield base
    base.close()
