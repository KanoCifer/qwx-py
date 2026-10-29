"""语言表与语言校验。"""

from __future__ import annotations

import pytest

from qwx.errors import InvalidParameterError
from qwx.lang import LANGS, Lang, lookup_lang


def test_official_language_list_is_complete() -> None:
    assert len(LANGS) == 31
    assert LANGS[0] is Lang.ZH
    assert Lang.ZH.api == "zh"
    assert Lang.ZH.name == "简体中文"


def test_language_codes_are_unique() -> None:
    codes = [lang.api for lang in LANGS]
    assert len(set(codes)) == len(codes)


def test_lookup_by_api_code() -> None:
    assert lookup_lang("zh-hant") is Lang.ZH_HANT
    assert lookup_lang("EN") is Lang.EN
    assert lookup_lang("  fr  ") is Lang.FR


def test_lookup_uses_alias_for_equivalent_code() -> None:
    # 官方给简体中文列了两个等价代码，zh-hans 查得到但不发出去。
    assert lookup_lang("zh-hans") is Lang.ZH
    assert Lang.ZH.api == "zh"


def test_lookup_unknown_code_returns_none() -> None:
    assert lookup_lang("klingon") is None
    assert lookup_lang("") is None


def test_validate_accepts_known_code() -> None:
    Lang.ZH.validate()
    Lang.EN.validate()


def test_validate_rejects_malformed_code() -> None:
    with pytest.raises(InvalidParameterError):
        Lang("x", "zh_hant").validate()
    with pytest.raises(InvalidParameterError):
        Lang("x", "a" * 33).validate()


def test_unspecified_language_is_valid() -> None:
    Lang("", "").validate()
    assert Lang("", "").is_zero()


def test_str_is_the_api_code() -> None:
    assert str(Lang.ZH) == "zh"
