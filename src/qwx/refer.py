"""数据来源与许可信息。

旧一代接口（/v7/*）与 GeoAPI 在响应里带 refer 对象，说明数据来源与
授权方式。新一代接口没有 refer —— 同样的意思由 metadata.attributions
表达。展示上游数据时需要一并展示来源与许可声明。
"""

from __future__ import annotations

from pydantic import Field

from qwx._models import QwxModel

__all__ = ["MetaData", "Refer"]


class Refer(QwxModel):
    """数据来源与许可信息。上游可能给空列表。"""

    sources: list[str] = Field(default_factory=list)
    license: list[str] = Field(default_factory=list)


class MetaData(QwxModel):
    """控制台 API 返回的元数据块。

    响应里的 metadata 对象说明本次响应的数据标签与来源署名。展示上游
    数据时需要保留 attributions。
    """

    tag: str = ""
    attributions: list[str] = Field(default_factory=list)
