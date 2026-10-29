"""旧一代生活指数接口（/v7/indices/{days}d）。

导出本族公开符号：模型、端点常量、类型常量与服务客户端。
"""

from __future__ import annotations

from qwx.v7.indices.client import AsyncIndicesService, IndicesService
from qwx.v7.indices.types import (
    MAX_TYPE,
    TYPE_ALL,
    TYPE_FISHING,
    DailyIndex,
    Endpoint,
    Result,
)

__all__ = [
    "MAX_TYPE",
    "TYPE_ALL",
    "TYPE_FISHING",
    "AsyncIndicesService",
    "DailyIndex",
    "Endpoint",
    "IndicesService",
    "Result",
]
