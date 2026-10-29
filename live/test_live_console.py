"""控制台 API 的联网冒烟测试。

打真实上游，覆盖两个端点：

- GET /finance/v1/summary —— 财务与计费汇总
- GET /metrics/v1/stats —— 最近 24 小时的 API 请求量统计

控制台端点默认没有权限：帐号所有者要在控制台的「项目管理 - 凭据 - 控制台
权限」里单独开通，上游未开通时回 403。这类情况按「跳过」处理，不是失败 ——
与 Go 版遇到 ErrUnauthorized 时 t.Skip 的口径一致。

    pytest live -q
"""

from __future__ import annotations

import os

import pytest
from conftest import requires_credentials

import qwx
from qwx.console import ConsoleService, StatsOptions

pytestmark = [pytest.mark.live, requires_credentials]

SKIP_NO_CONSOLE_PERMISSION = "凭据未开通控制台权限"


def test_console_finance(client: qwx.Client) -> None:
    """财务汇总：拿到币种与数据截止时间。

    断言 currency 与 as_of 非空 —— 模型各字段都有默认值，字段全空时这两个
    断言能把问题暴露出来。
    """
    try:
        result = ConsoleService(client).finance()
    except qwx.UnauthorizedError:
        pytest.skip(SKIP_NO_CONSOLE_PERMISSION)

    assert result.currency != "", f"币种为空：{result!r}"
    assert result.as_of != "", f"数据截止时间为空：{result!r}"


def test_console_stats(client: qwx.Client) -> None:
    """请求量统计：不带过滤条件。

    as_of 非空；success 与 errors 必须是列表。上游可能一条统计都不给，
    所以不断言列表非空。
    """
    try:
        result = ConsoleService(client).stats()
    except qwx.UnauthorizedError:
        pytest.skip(SKIP_NO_CONSOLE_PERMISSION)

    assert result.as_of != "", f"数据截止时间为空：{result!r}"
    assert result.success is not None
    assert result.errors is not None


def test_console_stats_by_project(client: qwx.Client) -> None:
    """请求量统计：只统计一个项目。

    项目 ID 来自 QWX_PROJECT_ID，没配就跳过 —— 拿不到真实 ID 时不该打上游。
    """
    project = os.environ.get("QWX_PROJECT_ID", "")
    if not project:
        pytest.skip("未设置 QWX_PROJECT_ID，跳过按项目过滤的统计")

    try:
        result = ConsoleService(client).stats(StatsOptions(project=project))
    except qwx.UnauthorizedError:
        pytest.skip(SKIP_NO_CONSOLE_PERMISSION)

    assert result.as_of != "", f"数据截止时间为空：{result!r}"
    assert result.success is not None
    assert result.errors is not None


def test_console_stats_by_credential(client: qwx.Client) -> None:
    """请求量统计：只统计一个凭据。

    凭据 ID 来自 QWX_CREDENTIAL_ID，没配就跳过。与 project 互斥，这里
    只传 credential。
    """
    credential = os.environ.get("QWX_CREDENTIAL_ID", "")
    if not credential:
        pytest.skip("未设置 QWX_CREDENTIAL_ID，跳过按凭据过滤的统计")

    try:
        result = ConsoleService(client).stats(StatsOptions(credential=credential))
    except qwx.UnauthorizedError:
        pytest.skip(SKIP_NO_CONSOLE_PERMISSION)

    assert result.as_of != "", f"数据截止时间为空：{result!r}"
    assert result.success is not None
    assert result.errors is not None
