"""坐标格式化的 golden 测试。

期望值抄自 Go 版 `internal/coord` 的测试。
"""

from __future__ import annotations

import pytest

from qwx._coord import format_coord, round_coord


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (39.92, "39.92"),
        (116.41876, "116.42"),
        (0, "0.00"),
        (-1.005, "-1.00"),
    ],
)
def test_format(value: float, expected: str) -> None:
    """坐标保留两位小数。"""
    assert format_coord(value) == expected


def test_format_normalizes_negative_zero() -> None:
    """负零不能进缓存键，否则同一坐标会出两个键。"""
    assert format_coord(-0.0) == "0.00"


def test_round() -> None:
    """规整后保留两位小数。"""
    lat, lon = round_coord(39.91755), round_coord(116.41876)
    assert (lat, lon) == (39.92, 116.42)
