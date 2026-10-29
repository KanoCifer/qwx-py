"""新一代接口跨端点族共用的基础类型。

这一代的字段形态与旧一代不同：数值与单位分离，湿度、云量、降水概率是
0~1 的比例而不是百分数。只有两个以上端点族都用到的类型才放在这里 ——
只服务单一端点族的类型留在该端点族自己的包里。

官方文档强调「不要假设」：字段可能缺失，枚举值可能新增，所以可选字段
一律用 None 表达，缺失与零值可区分。
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from qwx._models import QwxModel
from qwx.lang import Lang

__all__ = ["Metadata", "Options", "Value"]


class Metadata(QwxModel):
    """新一代接口统一的元数据块。"""

    tag: str = ""
    attributions: list[str] = Field(default_factory=list)
    zero_result: bool | None = None
    """上游确实查了但结果为空。

    老于该字段的接口版本没有它，此时为 None —— 无法区分「没查」与
    「查了是空」，调用方需要自己结合业务判断。
    """


class Value(QwxModel):
    """带单位的数值。

    新一代接口把数值与单位拆开，不再像 v7 那样把单位拼进字符串。
    """

    value: float = 0.0
    unit: str = ""


@dataclass(frozen=True, slots=True)
class Options:
    """新一代端点共用的可选参数。

    天气与预警两个端点族接受同一组参数，所以类型放在这里 —— 只服务单一
    端点族的参数留在该端点族自己的包里。
    """

    lang: Lang = Lang.UNSPECIFIED
    """语言，如 [qwx.Lang.ZH]。留空用上游默认。

    上游默认是所在国家或地区的官方语言，没有官方语言时回退到英语。
    """

    local_time: bool = False
    """是否返回查询地点的当地时间。

    新一代接口默认给 UTC（"2026-10-21T05:00Z"），不传 localTime
    时间会整整差 8 小时。除非明确要 UTC，否则应设为 true。
    """
