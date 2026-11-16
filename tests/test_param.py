"""跨端点族共用的参数格式校验。"""

from __future__ import annotations

import pytest

from qwx._param import is_digits, validate_date
from qwx.errors import InvalidParameterError


@pytest.mark.parametrize(
    ("date", "ok"),
    [
        ("20260101", True),
        ("20240229", True),
        ("20250229", False),
        ("20261301", False),
        ("20260132", False),
        ("202601", False),
        ("2026010a", False),
        ("", False),
    ],
)
def test_validate_date(date: str, ok: bool) -> None:
    """8 位数字且是真实日历日期才算合法。"""
    if ok:
        validate_date(date)
        return
    with pytest.raises(InvalidParameterError):
        validate_date(date)


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("", True),
        ("0123456789", True),
        ("12a", False),
        (" 12", False),
        ("1.2", False),
        ("１２", False),
    ],
)
def test_is_digits(value: str, ok: bool) -> None:
    """只认 ASCII 数字：全角数字不算。"""
    assert is_digits(value) is ok
