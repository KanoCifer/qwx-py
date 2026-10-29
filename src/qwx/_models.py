"""pydantic 模型的公共基类。

所有响应模型都从这里派生，保证同一套约定：

- 字段名用 snake_case，上游的 camelCase 键由别名生成器补齐；
- 允许额外字段（上游会新增，保留进 model_extra 比丢弃更可用）；
- 模型冻结，避免调用方误改解析结果。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["QwxModel", "to_camel"]


def to_camel(name: str) -> str:
    """snake_case 转 camelCase。

    只做大写首字母，不做其他变换：字段名到上游键的映射要 predictable，
    不规则键用 Field(alias=...) 显式覆盖。
    """
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


class QwxModel(BaseModel):
    """响应模型的基类。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
        frozen=True,
    )
