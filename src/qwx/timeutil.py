"""上游时间字符串的解析辅助。

响应模型里的时间字段保持 str：上游时间格式偶有变体，解析失败不该让整份
响应变成校验错误。需要结构化时间时用 parse_qtime，解析不出来返回 None。
"""

from __future__ import annotations

import re
from datetime import datetime

__all__ = ["parse_qtime"]

_OFFSET_RE = re.compile(r"([+-][0-9]{2})([0-9]{2})$")

_FALLBACK_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def parse_qtime(value: str | None) -> datetime | None:
    """解析上游的时间字符串。

    支持 ISO 8601 的常见形态：带 Z 的 UTC、带偏移量的本地时间、只有
    分钟或秒的写法，以及纯日期。解析不出来返回 None，不抛异常。
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None

    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"

    offset = _OFFSET_RE.search(text)
    if offset is not None:
        text = text[: offset.start()] + offset.group(1) + ":" + offset.group(2)

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    for fmt in _FALLBACK_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
