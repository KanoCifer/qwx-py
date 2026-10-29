"""版本号与安装元数据一致。"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import pytest

import qwx


def test_version_matches_installed_metadata() -> None:
    """__version__ 从安装元数据取，不该另写一份。"""
    try:
        installed = version("qwx")
    except PackageNotFoundError:  # pragma: no cover - 源码树里没装
        pytest.skip("qwx 没有安装元数据")
    assert qwx.__version__ == installed


def test_version_is_not_empty() -> None:
    """版本号不能是空串。"""
    assert qwx.__version__
