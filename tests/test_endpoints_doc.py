"""端点索引文档与契约基线的漂移检查。

三件事：

1. `docs/endpoints.md` 是生成物，重新生成后必须与入库文件逐字相同。
2. 扫描 Python 源码里的端点常量（`EndpointCurrent = Endpoint("weather/v1/current")`），
   与契约基线的常量名与常量值逐项比对。
3. 扫描 Python 源码里的默认 TTL（`CURRENT_CACHE_TTL = timedelta(seconds=600)`），
   与契约基线里该端点族的 TTL 集合逐项比对。

Python 侧改了端点常量值或默认 TTL 而没同步契约，本文件必须红。
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
CONTRACT_PATH = ROOT / "contract" / "endpoints.json"
DOC_PATH = ROOT / "docs" / "endpoints.md"

sys.path.insert(0, str(TOOLS))

import gen_endpoints  # noqa: E402

# 契约里有、源码里还没有的端点族。空的：26 个端点都已落地。
# 契约里新增端点族而源码还没跟上时，把模块名加进来 —— 落地后自动进入严格比对。
PENDING_PACKAGES: frozenset[str] = frozenset()

SOURCE_MODULES = ("types.py", "client.py")

TIMEDELTA_UNITS = {
    "days": 86400,
    "hours": 3600,
    "minutes": 60,
    "seconds": 1,
    "milliseconds": 0.001,
}


def _load_contract() -> dict[str, Any]:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


CONTRACT = _load_contract()
ENDPOINTS: list[dict[str, Any]] = CONTRACT["endpoints"]


def packages() -> list[str]:
    """契约里出现过的端点族模块名，保持契约顺序。"""
    seen: list[str] = []
    for endpoint in ENDPOINTS:
        if endpoint["py_package"] not in seen:
            seen.append(endpoint["py_package"])
    return seen


def package_dir(py_package: str) -> Path:
    """`qwx.v1.weather` 对应的源码目录。"""
    return SRC / Path(*py_package.split("."))


def contract_constants(py_package: str) -> dict[str, str]:
    """契约里某个端点族的端点常量：短名 -> 常量值。"""
    out: dict[str, str] = {}
    for endpoint in ENDPOINTS:
        if endpoint["py_package"] != py_package:
            continue
        name = endpoint["endpoint_constant"].rsplit(".", 1)[-1]
        out[name] = endpoint["endpoint"]
    return out


def contract_ttls(py_package: str) -> set[float]:
    """契约里某个端点族的默认 TTL 集合（秒）。"""
    return {
        float(endpoint["default_ttl_seconds"])
        for endpoint in ENDPOINTS
        if endpoint["py_package"] == py_package
    }


def _call_name(node: ast.Call) -> str:
    """取出被调用者的名字：`Endpoint`、`_Endpoint`、`timedelta` 等。"""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _assignments(path: Path) -> list[tuple[str, ast.Call]]:
    """取文件里所有「单目标赋值且右值是调用」的项。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[tuple[str, ast.Call]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Call):
            continue
        out.append((target.id, node.value))
    return out


def source_constants(py_package: str) -> dict[str, str]:
    """扫源码，取出端点常量的名字与值。"""
    out: dict[str, str] = {}
    directory = package_dir(py_package)
    if not directory.is_dir():
        return out
    for module in SOURCE_MODULES:
        path = directory / module
        if not path.is_file():
            continue
        for name, call in _assignments(path):
            if "endpoint" not in _call_name(call).lower():
                continue
            if not call.args or not isinstance(call.args[0], ast.Constant):
                continue
            literal = call.args[0]
            if not isinstance(literal.value, str):
                continue
            out[name] = literal.value
    return out


def source_ttls(py_package: str) -> set[float]:
    """扫源码，取出该端点族里所有默认 TTL 常量的时长（秒）。"""
    out: set[float] = set()
    directory = package_dir(py_package)
    if not directory.is_dir():
        return out
    for module in SOURCE_MODULES:
        path = directory / module
        if not path.is_file():
            continue
        for name, call in _assignments(path):
            if not name.endswith("_TTL") or _call_name(call) != "timedelta":
                continue
            seconds = _timedelta_seconds(call)
            if seconds is not None:
                out.add(seconds)
    return out


def _timedelta_seconds(node: ast.Call) -> float | None:
    """把 `timedelta(...)` 换算成秒。认不出的写法返回 None。"""
    total = 0.0
    if node.args:
        first = node.args[0]
        if not isinstance(first, ast.Constant) or not isinstance(first.value, int):
            return None
        total += first.value * TIMEDELTA_UNITS["days"]
    for keyword in node.keywords:
        if keyword.arg not in TIMEDELTA_UNITS:
            return None
        literal = keyword.value
        if not isinstance(literal, ast.Constant) or not isinstance(literal.value, int):
            return None
        total += literal.value * TIMEDELTA_UNITS[keyword.arg]
    return total


def test_doc_matches_generated() -> None:
    """入库的 docs/endpoints.md 必须与重新生成的内容逐字相同。"""
    expected = gen_endpoints.render(CONTRACT)
    assert DOC_PATH.exists(), "docs/endpoints.md 不存在，跑 python tools/gen_endpoints.py 生成"
    assert DOC_PATH.read_text(encoding="utf-8") == expected, (
        "docs/endpoints.md 与契约基线漂移，跑 python tools/gen_endpoints.py 更新"
    )


def test_doc_has_26_endpoints() -> None:
    """端点条数必须是 26。"""
    assert len(ENDPOINTS) == 26
    text = DOC_PATH.read_text(encoding="utf-8")
    section = text.split("## 端点方法总表", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("| `qwx.")]
    assert len(rows) == 26


def test_doc_lists_every_endpoint() -> None:
    """每个端点的方法名与上游路径都要出现在文档里。"""
    text = DOC_PATH.read_text(encoding="utf-8")
    for endpoint in ENDPOINTS:
        assert f"`{endpoint['py_method']}`" in text, endpoint["py_method"]
        assert f"`{endpoint['upstream_path']}`" in text, endpoint["upstream_path"]
        const = f"`{endpoint['py_package']}.{endpoint['endpoint_constant'].rsplit('.', 1)[-1]}`"
        assert const in text, const


@pytest.mark.parametrize("py_package", packages())
def test_endpoint_constants_match_contract(py_package: str) -> None:
    """Python 源码里的端点常量名与常量值必须与契约一致。"""
    directory = package_dir(py_package)
    if not directory.is_dir():
        assert py_package in PENDING_PACKAGES, f"{py_package} 的源码目录不存在"
        pytest.skip(f"{py_package} 尚未实现")
    assert source_constants(py_package) == contract_constants(py_package)


@pytest.mark.parametrize("py_package", packages())
def test_default_ttls_match_contract(py_package: str) -> None:
    """Python 源码里的默认 TTL 集合必须与契约里该族的 TTL 集合一致。"""
    directory = package_dir(py_package)
    if not directory.is_dir():
        assert py_package in PENDING_PACKAGES, f"{py_package} 的源码目录不存在"
        pytest.skip(f"{py_package} 尚未实现")
    assert source_ttls(py_package) == contract_ttls(py_package)
