"""预警接口（/weatheralert/v1/*）的结果类型。

这一代只认坐标：位置必须是经纬度路径参数，LocationID 塞进路径上游直接
404。要按 LocationID 或地名查预警，先用 geo 包换坐标。

官方文档强调「不要假设」：预警的字段多半可空，缺失与零值必须能区分，
所以可选字段一律是 `X | None = None`。
"""

from __future__ import annotations

from pydantic import Field

from qwx._models import QwxModel
from qwx.ttl import Endpoint as EndpointType
from qwx.v1.types import Metadata, Options

__all__ = [
    "Alert",
    "Color",
    "Endpoint",
    "EventType",
    "MessageType",
    "Options",
    "Result",
]

Endpoint = EndpointType("weatheralert/v1/current")
"""预警实况端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

取值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置
静默失效。
"""


class MessageType(QwxModel):
    """预警消息类型。"""

    code: str = ""
    """消息类型代码，如 "update"、"alert"。"""

    supersedes: list[str] = Field(default_factory=list)
    """本条预警更新/替代的历史预警 ID。

    上游可能给多个，也可能一个都不给（首次发布的预警没有前身）。
    """


class EventType(QwxModel):
    """预警事件类型。"""

    name: str = ""
    """事件名称，如 "大风"。"""

    code: str = ""
    """事件代码，如 "1006"。

    官方会新增代码，不要依赖枚举的完备性。
    """


class Color(QwxModel):
    """预警颜色。

    颜色是 RGBA 四分量：红、绿、蓝三个通道加一个透明度。
    """

    code: str = ""
    """颜色名，如 "blue"。"""

    red: int = 0
    """红通道。"""

    green: int = 0
    """绿通道。"""

    blue: int = 0
    """蓝通道。"""

    alpha: int = 0
    """透明度。"""


class Alert(QwxModel):
    """一条预警。

    除 urgency、severity、certainty 三个字段外，其余字段上游都会给；
    但字段本身可能整个缺失，缺失时是空值，不代表上游说它是空。
    """

    id: str = ""
    """预警 ID。"""

    sender_name: str = ""
    """发布机构，如 "临桂区气象台"。"""

    issued_time: str = ""
    """发布时间。

    时间字段保持字符串，不转 datetime：上游给的时间串带时区偏移，
    解析交给 [qwx.parse_qtime]。
    """

    message_type: MessageType = Field(default_factory=MessageType)
    """消息类型。

    是对象不是字符串：里面有 code 与被替代的历史预警 ID。
    """

    event_type: EventType = Field(default_factory=EventType)
    """事件类型。

    是对象不是字符串：里面有事件名称与事件代码。
    """

    urgency: str | None = None
    """紧急程度。可能缺失。"""

    severity: str | None = None
    """严重程度。可能缺失。"""

    certainty: str | None = None
    """确定性。可能缺失。"""

    icon: str = ""
    """预警图标代码。"""

    color: Color = Field(default_factory=Color)
    """预警颜色。"""

    effective_time: str = ""
    """生效时间。字符串，见 issued_time。"""

    onset_time: str = ""
    """开始时间。字符串，见 issued_time。"""

    expire_time: str = ""
    """失效时间。字符串，见 issued_time。"""

    headline: str = ""
    """预警标题。"""

    description: str = ""
    """预警描述全文。"""

    criteria: str = ""
    """预警的触发标准。"""

    response_types: list[str] = Field(default_factory=list)
    """建议的响应措施。"""

    instruction: str = ""
    """防御指南。"""


class Result(QwxModel):
    """预警查询的结果。"""

    metadata: Metadata = Field(default_factory=Metadata)
    """元数据。"""

    alerts: list[Alert] = Field(default_factory=list)
    """预警列表。

    没有预警时上游返回空列表（metadata.zero_result 为 true），不是 null。
    """
