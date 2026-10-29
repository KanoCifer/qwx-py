"""控制台 API（/finance/v1/summary、/metrics/v1/stats）的结果类型、参数与常量。

控制台 API 查的是帐号自己的财务与请求量，不是天气数据。凭据默认没有权限
访问这两个端点：帐号所有者要在控制台的「项目管理 - 凭据 - 控制台权限」里
单独开通对应的权限，未开通时上游直接拒绝。

上游把这两个端点归在同一页文档下，共享同一套响应骨架（元数据 + asOf），
所以放在一个包里。

两个端点返回的数据都截止至上一个小时或更晚，与控制台网页上显示的可能有
1 小时或更长的延迟，以响应里的 as_of 为准。

模型按依赖顺序排列：被引用的类型先定义。
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from qwx._models import QwxModel
from qwx.refer import MetaData
from qwx.ttl import Endpoint

__all__ = [
    "APICount",
    "AccruedCharges",
    "EndpointFinance",
    "EndpointStats",
    "FinanceResult",
    "PendingBill",
    "ResourcePlan",
    "SavingsPlan",
    "StatsOptions",
    "StatsResult",
]

EndpointFinance = Endpoint("finance/v1/summary")
"""财务汇总端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

取值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置静默
失效。
"""

EndpointStats = Endpoint("metrics/v1/stats")
"""请求量统计端点的标识，用于 TTLPolicy 按端点匹配缓存时长。

取值在已发布版本里定死：TTLPolicy 按值匹配，改值会让用户的 TTL 配置静默
失效。
"""


class AccruedCharges(QwxModel):
    """应计费用。"""

    previous_day: float = 0.0
    """前一天应计费用总额。"""

    this_month: float = 0.0
    """本月应计费用总额。"""

    since_last_bill: float = 0.0
    """从上次出账以来的应计费用总额。"""


class PendingBill(QwxModel):
    """一张待支付的账单。"""

    number: str = ""
    """账单号。"""

    date: str = ""
    """出账日期，如 "2024-04-01T10:00Z"。

    上游给的是 UTC，原样透传。
    """

    type: str = ""
    """账单类型，如 "PayAsYouGo"、"SavingsPlans"。

    官方会新增类型，不要依赖枚举的完备性。
    """

    status: str = ""
    """账单状态，如 "unpaid"、"overdue"。

    官方会新增状态，不要依赖枚举的完备性。
    """

    amount: float = 0.0
    """账单总金额。"""

    amount_due: float = 0.0
    """剩余应付金额。"""

    due_date: str = ""
    """应付日期，如 "2024-04-10T23:59Z"。

    上游给的是 UTC，原样透传。
    """


class SavingsPlan(QwxModel):
    """一个可用的节省计划。"""

    bill_number: str = ""
    """账单号。"""

    status: str = ""
    """计划状态，如 "pending"、"active"。

    官方会新增状态，不要依赖枚举的完备性。
    """

    term: str = ""
    """承诺期限，如 "1"。

    上游给的是字符串，原样透传。
    """

    commitments: float = 0.0
    """承诺金额。"""

    utilized: float = 0.0
    """已用承诺金额。"""

    effective_time: str = ""
    """生效时间，如 "2024-04-30T13:00Z"。

    上游给的是 UTC，原样透传。
    """


class ResourcePlan(QwxModel):
    """一个可用的资源包。"""

    bill_number: str = ""
    """账单号。"""

    status: str = ""
    """资源包状态，如 "pending"、"active"。

    官方会新增状态，不要依赖枚举的完备性。
    """

    requests: int | float | str = ""
    """总请求量。

    上游的返回样例给的是字符串（"1000000"），官方字段表标的是数字 ——
    两种形态都收，调用方按数值用。
    """

    commitments: float = 0.0
    """承诺金额。"""

    utilized: float = 0.0
    """已使用的请求数量。"""

    effective_time: str = ""
    """生效时间，如 "2024-04-03T17:00Z"。

    上游给的是 UTC，原样透传。
    """


class FinanceResult(QwxModel):
    """财务汇总的结果。"""

    metadata: MetaData = Field(default_factory=MetaData)
    """元数据。"""

    as_of: str = ""
    """数据的截止时间，如 "2024-04-03T17:13Z"。

    上游给的是 UTC，原样透传。数据截止至上一个小时或更晚，与控制台网页
    显示的可能有 1 小时以上的延迟，以这里为准。
    """

    currency: str = ""
    """货币代码，如 "CNY"、"USD"。"""

    balance: float = 0.0
    """可用额度。负数表示欠费。"""

    accrued_charges: AccruedCharges = Field(default_factory=AccruedCharges)
    """应计费用。"""

    pending_bills: list[PendingBill] = Field(default_factory=list)
    """待支付的账单列表。

    列表长度不假设 —— 上游可能给得更少，也可能一条都没有。
    """

    available_savings_plans: list[SavingsPlan] = Field(default_factory=list)
    """可用的节省计划列表。

    列表长度不假设 —— 上游可能给得更少。
    """

    available_resource_plans: list[ResourcePlan] = Field(default_factory=list)
    """可用的资源包列表。

    列表长度不假设 —— 上游可能给得更少。
    """


class APICount(QwxModel):
    """一个 API 的逐小时请求量。"""

    api: str = ""
    """API 名称，如 "Weather"、"Geo"、"AirQuality"。

    官方会新增名称，不要依赖枚举的完备性。
    """

    hours: list[int] = Field(default_factory=list)
    """最近 24 小时的逐小时请求量。

    在 `StatsResult.success` 里是成功请求量，在 `StatsResult.errors` 里是
    错误请求量。末位对应 as_of 所在的那一小时：as_of=2025-03-20T09:59Z 时，
    末位是 09:00~09:59（UTC）的请求量。

    上游可能给少于 24 条，不要假设长度。
    """


class StatsResult(QwxModel):
    """请求量统计的结果。"""

    metadata: MetaData = Field(default_factory=MetaData)
    """元数据。"""

    as_of: str = ""
    """数据的截止时间，如 "2025-05-12T02:59Z"。

    上游给的是 UTC，原样透传。数据截止至上一个小时或更晚，以这里为准。
    """

    success: list[APICount] = Field(default_factory=list)
    """各 API 的成功请求量。

    列表长度不假设 —— 上游可能给得更少。
    """

    errors: list[APICount] = Field(default_factory=list)
    """各 API 的错误请求量。

    列表长度不假设 —— 上游可能给得更少。
    """


@dataclass(frozen=True, slots=True)
class StatsOptions:
    """请求量统计的可选参数。

    项目与凭据两个过滤条件互斥，都留空时统计帐号下所有项目与凭据（含已
    删除的 —— 已删除的项目或凭据无法单独查询，但请求量仍计入汇总）。
    """

    project: str = ""
    """项目 ID，只统计这个项目的请求量。

    与 credential 互斥，两个都填在客户端被挡下，不打上游。
    """

    credential: str = ""
    """凭据 ID，只统计这个凭据的请求量。

    与 project 互斥，两个都填在客户端被挡下，不打上游。
    """
