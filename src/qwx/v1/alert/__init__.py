"""预警接口（/weatheralert/v1/*）。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 会被上游拒绝。
要按 LocationID 或地名查预警，先用 geo 包换坐标。
"""

from __future__ import annotations

from qwx.v1.alert.client import AlertService, AsyncAlertService
from qwx.v1.alert.types import (
    Alert,
    Color,
    Endpoint,
    EventType,
    MessageType,
    Options,
    Result,
)

__all__ = [
    "Alert",
    "AlertService",
    "AsyncAlertService",
    "Color",
    "Endpoint",
    "EventType",
    "MessageType",
    "Options",
    "Result",
]
