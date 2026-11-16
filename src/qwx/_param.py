"""跨端点族共用的参数格式校验。

参数名在 [qwx._upstream]，键在 [qwx._cachekey]，这里只管"这个值的形态对不对"。

旧一代三个端点族（天文、历史天气、潮汐）的日期参数是同一个约定，各自写
一份校验，改一处就会漏掉另外两处。
"""

from __future__ import annotations

from datetime import datetime

from qwx.errors import InvalidParameterError

__all__ = ["DATE_FORMAT", "is_digits", "validate_date"]

DATE_FORMAT = "%Y%m%d"
"""日期参数的格式。"""


def is_digits(value: str) -> bool:
    """报告 value 是否全是 ASCII 数字。

    str.isdigit() 对全角数字与上标数字也为真，这里只认 ASCII 的 0~9。
    """
    return all("0" <= ch <= "9" for ch in value)


def validate_date(date: str) -> None:
    """校验日期参数：8 位数字且是真实日历日期。

    只校验格式与日历合法性，不校验范围 —— 上游对日期范围各有规定（天文
    最多未来 60 天、历史天气只给最近 10 天），拿"今天"比要引入时钟依赖，
    超范围的请求交给上游拒绝。
    """
    if len(date) != 8 or not is_digits(date):
        raise InvalidParameterError(f"qwx: date {date!r} must be in yyyyMMdd format")
    try:
        datetime.strptime(date, DATE_FORMAT)
    except ValueError:
        raise InvalidParameterError(f"qwx: date {date!r} is not a valid calendar date") from None
