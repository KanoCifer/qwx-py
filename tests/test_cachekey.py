"""缓存键的 golden 测试。

期望值抄自 Go 版 `internal/cachekey` 的测试。两边必须逐字相同：
键不一样，Go 与 Python 共享同一个 Redis 时会互相覆盖。
"""

from __future__ import annotations

import pytest

from qwx._cachekey import Family, Key, Params


def test_family_prefixes_are_frozen() -> None:
    """族前缀在已发布版本里定死。

    改了前缀，命中不到旧缓存条目，还要让新旧两代共键。
    """
    want = {
        Family.WEATHER: "qwx:v1:",
        Family.AIR_QUALITY: "qwx:aq:v1:",
        Family.ALERT: "qwx:alert:v1:",
        Family.GEO: "qwx:geo:",
        Family.TIDE: "qwx:tide:",
        Family.INDICES: "qwx:indices:",
        Family.MINUTELY: "qwx:minutely:",
        Family.CONSOLE: "qwx:console:",
    }
    for family, expected in want.items():
        assert family.value == expected


def test_families_are_distinct() -> None:
    """两代与 GeoAPI 的前缀不能互相嵌套。

    前缀嵌套会让一个族的键落进另一个族的前缀空间。
    """
    all_families = [
        Family.WEATHER,
        Family.AIR_QUALITY,
        Family.ALERT,
        Family.GEO,
        Family.TIDE,
        Family.INDICES,
        Family.MINUTELY,
        Family.CONSOLE,
    ]
    for i, first in enumerate(all_families):
        for j, second in enumerate(all_families):
            if i == j:
                continue
            assert first != second
            assert not second.value.startswith(first.value)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (
            str(
                Key(Family.WEATHER)
                .path("current")
                .path_coord(39.92, 116.41)
                .params(Params(lang="zh"))
            ),
            "qwx:v1:current:39.92,116.41:lang=zh",
        ),
        (
            str(
                Key(Family.WEATHER)
                .path("hourly")
                .path_coord(39.92, 116.41)
                .count("h", 24)
                .params(Params(lang="zh", local_time=True))
            ),
            "qwx:v1:hourly:39.92,116.41:h24:lang=zh:localTime=1",
        ),
        (
            str(Key(Family.GEO).path("city", "101011600").params(Params(lang="zh", number=5))),
            "qwx:geo:city:101011600:lang=zh:n=5",
        ),
        (
            str(
                Key(Family.GEO)
                .path("poirange", "scenic", "116.41,39.92")
                .params(Params(lang="zh", number=5, radius=5))
            ),
            "qwx:geo:poirange:scenic:116.41,39.92:lang=zh:n=5:r=5",
        ),
        (
            str(Key(Family.TIDE).path("P2352", "20260101")),
            "qwx:tide:P2352:20260101",
        ),
        (
            str(Key(Family.GEO).path("city", "")),
            "qwx:geo:city:",
        ),
    ],
)
def test_key_shape(key: str, expected: str) -> None:
    """键的形状与 Go 版逐字相同。"""
    assert key == expected


def test_path_coord_normalizes_negative_zero() -> None:
    """负零不进键。"""
    got = str(Key(Family.WEATHER).path("current").path_coord(-0.0001, 0))
    assert got == "qwx:v1:current:0.00,0.00"


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (Params(lang="zh"), Params(lang="en")),
        (Params(local_time=True), Params()),
        (Params(number=5), Params(number=10)),
        (Params(radius=5), Params(radius=10)),
    ],
)
def test_params_change_key(first: Params, second: Params) -> None:
    """每个影响结果的参数都必须改变键。"""
    base = str(Key(Family.GEO).path("city", "101011600"))
    a = str(Key(Family.GEO).path("city", "101011600").params(first))
    b = str(Key(Family.GEO).path("city", "101011600").params(second))
    assert a != b
    assert a != base


def test_params_query_reports_set_params() -> None:
    """设了的参数上报上游。"""
    query = Params(lang="zh", local_time=True, number=3, radius=5).query()
    assert query == {
        "lang": "zh",
        "localTime": "true",
        "number": "3",
        "radius": "5",
    }


def test_params_query_omits_unset() -> None:
    """没设的参数不上报上游。"""
    assert Params(number=0, radius=0).query() == {}


def test_params_query_includes_family_params() -> None:
    """新加的参数也要上报上游。"""
    query = Params(
        adm="101010100",
        range="cn",
        city="101010100",
        interval=15,
        tilt=0,
        azimuth=180,
        extra="weather,poa",
        project="proj-1",
        credential="cred-1",
    ).query()
    assert query == {
        "adm": "101010100",
        "range": "cn",
        "city": "101010100",
        "interval": "15",
        "tilt": "0",
        "azimuth": "180",
        "extra": "weather,poa",
        "project": "proj-1",
        "credential": "cred-1",
    }


def test_params_suffix_order() -> None:
    """后缀顺序固定：语言 → 本地时间 → 条数 → 半径。"""
    got = Params(lang="zh", local_time=True, number=5, radius=0).suffix()
    assert got == ":lang=zh:localTime=1:n=5:r=0"


def test_params_suffix_skips_unset() -> None:
    """空参数不进键，也不留分隔符。"""
    assert Params().suffix() == ""
    assert Params(number=0).suffix() == ""


def test_params_suffix_includes_family_params() -> None:
    """新加的参数进键，顺序接在已有参数之后。"""
    got = Params(
        lang="zh",
        local_time=True,
        number=5,
        adm="101010100",
        range="cn",
        city="101010100",
        interval=15,
        tilt=0,
        azimuth=180,
        extra="poa",
        project="proj-1",
        credential="cred-1",
    ).suffix()
    assert got == (
        ":lang=zh:localTime=1:n=5:adm=101010100:range=cn:city=101010100"
        ":interval=15:tilt=0:azimuth=180:extra=poa:project=proj-1:credential=cred-1"
    )


def test_params_tilt_and_azimuth_zero_is_reported() -> None:
    """倾斜角与方位角的 0 是合法取值。

    与半径的语义相反：非 None 时就要上报，不能当「没传」。
    """
    query = Params(tilt=0, azimuth=0).query()
    assert query["tilt"] == "0"
    assert query["azimuth"] == "0"
    assert Params(tilt=0, azimuth=0).suffix() == ":tilt=0:azimuth=0"
