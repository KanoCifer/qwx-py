#!/usr/bin/env python3
"""对照 Go 字段契约与 Python 模型的别名集合。

Go 侧的真源是 contract/types.json（由 extract_go_contract.py 抽取）。
Python 侧扫描 src/qwx 下的 pydantic 模型，取每个字段的别名：

- 写了 Field(alias=...) 就用写的；
- 没写就按 to_camel(字段名) 推。

两边的别名集合必须完全相等。少一个就是漏映射，多一个就是凭空多出的字段。
P2 之后每落一个模型都该跑一次。

用法：
    python tools/check_field_map.py
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

MODEL_BASES = {"QwxModel", "BaseModel"}


def to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def package_of(path: Path, src_root: Path) -> str:
    """从模型文件路径推出包名，与契约里的包名对齐。"""
    rel = path.relative_to(src_root).parent.as_posix()
    if rel in {"", "."}:
        return "core"
    return rel


def scan_models(src_root: Path) -> dict[str, set[str]]:
    """扫描 Python 模型，取出每个模型的别名集合。"""
    models: dict[str, set[str]] = {}

    for path in sorted(src_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        package = package_of(path, src_root)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {base.id for base in node.bases if isinstance(base, ast.Name)}
            if not bases & MODEL_BASES:
                continue
            aliases: set[str] = set()
            for stmt in node.body:
                if not isinstance(stmt, ast.AnnAssign):
                    continue
                if not isinstance(stmt.target, ast.Name):
                    continue
                alias: str | None = None
                if isinstance(stmt.value, ast.Call):
                    func = stmt.value.func
                    if isinstance(func, ast.Name) and func.id == "Field":
                        for keyword in stmt.value.keywords:
                            if keyword.arg == "alias" and isinstance(keyword.value, ast.Constant):
                                alias = keyword.value.value
                aliases.add(alias if alias else to_camel(stmt.target.id))
            models[f"{package}.{node.name}"] = aliases

    return models


def go_aliases(contract: dict[str, Any]) -> dict[str, set[str]]:
    """从契约里取每个 Go 类型的 json tag 集合。"""
    out: dict[str, set[str]] = {}
    for key, info in contract["types"].items():
        aliases = {field["json_name"] for field in info["fields"] if field["json_name"]}
        out[key] = aliases
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="对照 Go 字段契约与 Python 模型")
    parser.add_argument("--contract", default="contract/types.json")
    parser.add_argument("--src", default="src/qwx")
    args = parser.parse_args(argv)

    contract_path = Path(args.contract)
    if not contract_path.exists():
        print(f"check: {contract_path} 不存在，先跑抽取器", file=sys.stderr)
        return 2

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    go_map = go_aliases(contract)
    py_map = scan_models(Path(args.src))

    if not py_map:
        print("check: Python 侧还没有模型，P2 落模型后再跑")
        return 0

    problems: list[str] = []
    for key, go_aliases_set in sorted(go_map.items()):
        if key not in py_map:
            continue
        py_aliases_set = py_map[key]
        missing = sorted(go_aliases_set - py_aliases_set)
        extra = sorted(py_aliases_set - go_aliases_set)
        if missing:
            problems.append(f"{key}: 少了 {len(missing)} 个别名 {missing}")
        if extra:
            problems.append(f"{key}: 多了 {len(extra)} 个别名 {extra}")

    if problems:
        print("check: 字段映射与 Go 契约不一致", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    checked = sum(1 for key in go_map if key in py_map)
    print(f"check: {checked} 个模型与 Go 契约一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
