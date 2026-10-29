"""坐标的格式化与规整。

内部模块：坐标只在 SDK 内流转，不对外暴露。
"""

from __future__ import annotations

DECIMALS = 2


def format_coord(value: float) -> str:
    """格式化坐标分量，保留两位小数，负零归一成零。

    归一负零是为了不让 `-0.00` 这种怪值进缓存键。
    """
    text = f"{value:.{DECIMALS}f}"
    if text == "-0.00":
        return "0.00"
    return text


def round_coord(value: float) -> float:
    """把坐标规整到两位小数。"""
    return float(format_coord(value))
