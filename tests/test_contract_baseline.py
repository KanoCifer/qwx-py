"""契约基线的自检。

基线由 tools/extract_go_contract.py 从 Go 源码抽取，与 Go 仓库的
docs/endpoints.md 逐项对账通过。这里校验基线自身的一致性，以及它与
Python 侧缓存键实现的对应关系。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from qwx._cachekey import Family, Params

ROOT = Path(__file__).resolve().parents[1]
GO_ROOT = ROOT.parent / "qwx"
CONTRACT = ROOT / "contract" / "endpoints.json"
TYPES = ROOT / "contract" / "types.json"

EXPECTED_ENDPOINTS = 26


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    return load(CONTRACT)


@pytest.fixture(scope="module")
def types_contract() -> dict[str, Any]:
    return load(TYPES)


def test_endpoint_count(contract: dict[str, Any]) -> None:
    """端点数量与 Go 版一致。"""
    assert len(contract["endpoints"]) == EXPECTED_ENDPOINTS


def test_every_endpoint_is_complete(contract: dict[str, Any]) -> None:
    """每个端点的契约要素齐全。"""
    for endpoint in contract["endpoints"]:
        key = f"{endpoint['package']}.{endpoint['method']}"
        assert endpoint["upstream_path"].startswith("/"), key
        assert endpoint["endpoint"], key
        assert endpoint["endpoint_constant"], key
        assert endpoint["location_shape"], key
        assert endpoint["default_ttl"], key
        assert endpoint["default_ttl_seconds"], key
        assert endpoint["cache_key_template"], key
        assert endpoint["response_type"], key


def test_cache_key_template_starts_with_family(contract: dict[str, Any]) -> None:
    """缓存键模板以族前缀开头。"""
    for endpoint in contract["endpoints"]:
        assert endpoint["cache_key_template"].startswith(endpoint["cache_prefix"]), (
            endpoint["package"],
            endpoint["method"],
        )


def test_cache_prefix_exists_in_python_implementation(
    contract: dict[str, Any],
) -> None:
    """契约里的族前缀在 Python 的 Family 里有对应项。

    少一个就意味着 Python 侧拼不出与 Go 版一致的键。
    """
    known = {family.value for family in Family}
    for endpoint in contract["endpoints"]:
        assert endpoint["cache_prefix"] in known, endpoint["cache_prefix"]


def test_params_suffix_placeholders_match_python_params(
    contract: dict[str, Any],
) -> None:
    """契约里的参数后缀占位符与 Python 的 Params 字段一一对应。"""
    placeholders = set(re.findall(r"\{(\w+)\}", contract["params_suffix"]))
    mapping = contract["params_placeholders"]
    assert placeholders <= set(mapping)
    assert set(mapping.values()) == set(Params.__dataclass_fields__)


def render_suffix_template(template: str, params: Params) -> str:
    """按契约里的参数后缀模板渲染出实际的键后缀。

    模板是已发布的键字面量，固定段（如 localTime=1）也有条件。
    """
    fixed_conditions = {"localTime": "local_time"}
    out: list[str] = []
    for segment in template.split(":")[1:]:
        key, _, value = segment.partition("=")
        match = re.fullmatch(r"\{(\w+)\}", value)
        if match:
            field = contract_placeholder_to_field(match.group(1))
            raw = getattr(params, field)
            if not should_emit(field, raw):
                continue
            out.append(f":{key}={raw}")
            continue
        if fixed_conditions.get(key) and not getattr(params, fixed_conditions[key]):
            continue
        out.append(f":{key}={value}")
    return "".join(out)


# 必须为正才进键的参数：0 表示「用上游默认」。
POSITIVE_ONLY = {"number", "interval"}

# 0 是合法取值、给值就进键的参数。
ZERO_IS_VALID = {"radius", "tilt", "azimuth"}


def should_emit(field: str, raw: Any) -> bool:
    """判断一个参数该不该进键后缀。"""
    if field in ZERO_IS_VALID:
        return raw is not None
    if field in POSITIVE_ONLY:
        return isinstance(raw, int) and raw > 0
    return bool(raw)


def contract_placeholder_to_field(placeholder: str) -> str:
    """缓存键占位符 → Python 的 Params 字段名。"""
    return PLACEHOLDER_TO_FIELD[placeholder]


PLACEHOLDER_TO_FIELD = {
    "lang": "lang",
    "localTime": "local_time",
    "n": "number",
    "r": "radius",
    "adm": "adm",
    "range": "range",
    "city": "city",
    "interval": "interval",
    "tilt": "tilt",
    "azimuth": "azimuth",
    "extra": "extra",
    "project": "project",
    "credential": "credential",
}


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (Params(), ""),
        (Params(number=0), ""),
        (Params(lang="zh"), ":lang=zh"),
        (
            Params(lang="zh", local_time=True, number=5, radius=0),
            ":lang=zh:localTime=1:n=5:r=0",
        ),
        (Params(tilt=0, azimuth=0), ":tilt=0:azimuth=0"),
        (
            Params(
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
            ),
            ":lang=zh:localTime=1:n=5:adm=101010100:range=cn:city=101010100"
            ":interval=15:tilt=0:azimuth=180:extra=poa:project=proj-1:credential=cred-1",
        ),
    ],
)
def test_contract_template_matches_implementation(
    contract: dict[str, Any],
    params: Params,
    expected: str,
) -> None:
    """契约模板渲染出的后缀与 Python 实现逐字相同。

    两边不同步，就是缓存键开始漂移的信号。
    """
    template = contract["params_suffix"]
    assert render_suffix_template(template, params) == expected
    assert params.suffix() == expected


def test_no_endpoint_uses_unknown_query_param(contract: dict[str, Any]) -> None:
    """查询参数都在 Params 的字段范围内。"""
    fields = set(Params.__dataclass_fields__)
    for endpoint in contract["endpoints"]:
        for param in endpoint["query_params"]:
            assert param["name"] in fields, (
                endpoint["package"],
                endpoint["method"],
                param["name"],
            )


def test_field_map_has_python_name(types_contract: dict[str, Any]) -> None:
    """每个 Go 字段都给出了 Python 字段名。"""
    for key, info in types_contract["types"].items():
        for field in info["fields"]:
            if field["alias_mode"] == "未解析":
                continue
            assert field["py_name"], f"{key}.{field['go_name']}"
            assert field["py_type"], f"{key}.{field['go_name']}"


def test_explicit_alias_list_is_consistent(types_contract: dict[str, Any]) -> None:
    """显式 alias 清单与类型清单对得上。"""
    explicit = {
        (item["package"], item["type"], item["go_field"])
        for item in types_contract["explicit_aliases"]
    }
    from_fields = {
        (info["package"], info["name"], field["go_name"])
        for info in types_contract["types"].values()
        for field in info["fields"]
        if field["alias_mode"] == "显式"
    }
    assert explicit == from_fields


def test_explicit_alias_really_needs_explicit(
    types_contract: dict[str, Any],
) -> None:
    """显式 alias 的字段确实不能靠 to_camel 自动生成。

    这一条防的是清单本身写错：标成「显式」却其实能自动生成。
    """
    for item in types_contract["explicit_aliases"]:
        parts = item["py_name"].split("_")
        auto = parts[0] + "".join(part.capitalize() for part in parts[1:])
        assert auto != item["json_name"], item


@pytest.mark.skipif(
    not (GO_ROOT / "internal" / "cachekey" / "cachekey.go").exists(),
    reason="Go 仓库不在旁边，跳过漂移检查",
)
def test_contract_has_no_drift() -> None:
    """重跑抽取器，基线必须一字不差。"""
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "extract_go_contract.py"),
            "--go-root",
            str(GO_ROOT),
            "--out",
            str(ROOT / "contract"),
            "--docs",
            str(ROOT / "docs"),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
