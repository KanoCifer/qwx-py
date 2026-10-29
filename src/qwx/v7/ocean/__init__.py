"""旧一代海洋接口（/v7/ocean/*）。

导出本族公开符号：模型、端点常量与服务客户端。
"""

from __future__ import annotations

from qwx.v7.ocean.client import AsyncOceanService, OceanService
from qwx.v7.ocean.types import (
    Endpoint,
    Result,
    Tide,
    TideHourly,
)

__all__ = [
    "AsyncOceanService",
    "Endpoint",
    "OceanService",
    "Result",
    "Tide",
    "TideHourly",
]
