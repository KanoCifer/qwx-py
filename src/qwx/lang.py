"""语言。

上游用 lang 查询参数切换返回的语言。Lang 给出语言名称与对应的 API 代码，
端点的语言参数用这个类型。

零值（api 为空）表示不指定语言 —— 端点不传 lang 参数，用上游默认
（所在国家或地区的官方语言，没有官方语言时回退到英语）。

官方会新增语言，所以这里不做白名单校验：Validate 只挡笔误，形态不对的
代码上游一律 400。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from qwx.errors import InvalidParameterError

__all__ = ["LANGS", "Lang", "lookup_lang"]

_LANG_CODE_RE = re.compile(r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$")
_MAX_LANG_CODE_LEN = 32


@dataclass(frozen=True, slots=True)
class Lang:
    """一种语言。字段都是字符串，可以直接比较。"""

    name: str
    api: str

    ZH: ClassVar[Lang]
    ZH_HANT: ClassVar[Lang]
    EN: ClassVar[Lang]
    DE: ClassVar[Lang]
    ES: ClassVar[Lang]
    FR: ClassVar[Lang]
    IT: ClassVar[Lang]
    JA: ClassVar[Lang]
    KO: ClassVar[Lang]
    RU: ClassVar[Lang]
    HI: ClassVar[Lang]
    TH: ClassVar[Lang]
    AR: ClassVar[Lang]
    PT: ClassVar[Lang]
    BN: ClassVar[Lang]
    MS: ClassVar[Lang]
    NL: ClassVar[Lang]
    EL: ClassVar[Lang]
    LA: ClassVar[Lang]
    SV: ClassVar[Lang]
    ID: ClassVar[Lang]
    PL: ClassVar[Lang]
    TR: ClassVar[Lang]
    CS: ClassVar[Lang]
    ET: ClassVar[Lang]
    VI: ClassVar[Lang]
    FIL: ClassVar[Lang]
    FI: ClassVar[Lang]
    HE: ClassVar[Lang]
    IS: ClassVar[Lang]
    NB: ClassVar[Lang]
    UNSPECIFIED: ClassVar[Lang]

    def __str__(self) -> str:
        """返回 API 语言代码。"""
        return self.api

    def is_zero(self) -> bool:
        """该语言是否未指定。"""
        return self.api == ""

    def validate(self) -> None:
        """校验语言代码的形态。

        不按官方列表做白名单：官方会新增语言，白名单会把新代码挡在门外。
        这里只挡笔误 —— 形态不对的代码上游一律 400。未指定语言是合法的。
        """
        if self.api == "":
            return
        if len(self.api) > _MAX_LANG_CODE_LEN or not _LANG_CODE_RE.match(self.api):
            raise InvalidParameterError(f"qwx: lang {self.api!r} is not a valid language code")


Lang.ZH = Lang("简体中文", "zh")
Lang.ZH_HANT = Lang("繁体中文", "zh-hant")
Lang.EN = Lang("英文", "en")
Lang.DE = Lang("德语", "de")
Lang.ES = Lang("西班牙语", "es")
Lang.FR = Lang("法语", "fr")
Lang.IT = Lang("意大利语", "it")
Lang.JA = Lang("日语", "ja")
Lang.KO = Lang("韩语", "ko")
Lang.RU = Lang("俄语", "ru")
Lang.HI = Lang("印地语", "hi")
Lang.TH = Lang("泰语", "th")
Lang.AR = Lang("阿拉伯语", "ar")
Lang.PT = Lang("葡萄牙语", "pt")
Lang.BN = Lang("孟加拉语", "bn")
Lang.MS = Lang("马来语", "ms")
Lang.NL = Lang("荷兰语", "nl")
Lang.EL = Lang("希腊语", "el")
Lang.LA = Lang("拉丁语", "la")
Lang.SV = Lang("瑞典语", "sv")
Lang.ID = Lang("印尼语", "id")
Lang.PL = Lang("波兰语", "pl")
Lang.TR = Lang("土耳其语", "tr")
Lang.CS = Lang("捷克语", "cs")
Lang.ET = Lang("爱沙尼亚语", "et")
Lang.VI = Lang("越南语", "vi")
Lang.FIL = Lang("菲律宾语", "fil")
Lang.FI = Lang("芬兰语", "fi")
Lang.HE = Lang("希伯来语", "he")
Lang.IS = Lang("冰岛语", "is")
Lang.NB = Lang("挪威语", "nb")

Lang.UNSPECIFIED = Lang("", "")

LANGS: tuple[Lang, ...] = (
    Lang.ZH,
    Lang.ZH_HANT,
    Lang.EN,
    Lang.DE,
    Lang.ES,
    Lang.FR,
    Lang.IT,
    Lang.JA,
    Lang.KO,
    Lang.RU,
    Lang.HI,
    Lang.TH,
    Lang.AR,
    Lang.PT,
    Lang.BN,
    Lang.MS,
    Lang.NL,
    Lang.EL,
    Lang.LA,
    Lang.SV,
    Lang.ID,
    Lang.PL,
    Lang.TR,
    Lang.CS,
    Lang.ET,
    Lang.VI,
    Lang.FIL,
    Lang.FI,
    Lang.HE,
    Lang.IS,
    Lang.NB,
)

_ALIASES: dict[str, Lang] = {
    "zh-hans": Lang.ZH,
}


def lookup_lang(code: str) -> Lang | None:
    """按代码查找语言。

    先按 API 代码匹配，再按等价别名匹配，都不区分大小写。找不到返回 None。
    """
    key = code.strip().lower()
    if not key:
        return None
    for lang in LANGS:
        if lang.api.lower() == key:
            return lang
    return _ALIASES.get(key)
