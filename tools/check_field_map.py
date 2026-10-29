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


def field_aliases(stmt: ast.AnnAssign) -> str:
    """取一个字段的别名：写了 alias 用写的，否则按 to_camel 推。"""
    if not isinstance(stmt.target, ast.Name):
        return ""
    alias: str | None = None
    if isinstance(stmt.value, ast.Call):
        func = stmt.value.func
        if isinstance(func, ast.Name) and func.id == "Field":
            for keyword in stmt.value.keywords:
                if keyword.arg == "alias" and isinstance(keyword.value, ast.Constant):
                    alias = keyword.value.value
    return alias if alias else to_camel(stmt.target.id)


def scan_models(src_root: Path) -> dict[str, set[str]]:
    """扫描 Python 模型，取出每个模型的别名集合。

    继承来的字段也要算进去：Go 的内嵌 struct 在 Python 侧常用继承表达
    （字段平铺在 JSON 里），只看类体自己的字段会漏掉一截。
    """
    models: dict[str, set[str]] = {}

    for path in sorted(src_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        package = package_of(path, src_root)

        classes: dict[str, tuple[set[str], set[str]]] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {base.id for base in node.bases if isinstance(base, ast.Name)}
            aliases: set[str] = set()
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign):
                    alias = field_aliases(stmt)
                    if alias:
                        aliases.add(alias)
            classes[node.name] = (bases, aliases)

        def resolve(
            name: str,
            seen: frozenset[str] = frozenset(),
            table: dict[str, tuple[set[str], set[str]]] = classes,
        ) -> set[str]:
            """取一个类的别名集合，含继承来的。"""
            if name in seen or name not in table:
                return set()
            bases, aliases = table[name]
            merged = set(aliases)
            for base in bases:
                merged |= resolve(base, seen | {name}, table)
            return merged

        def is_model(
            name: str,
            seen: frozenset[str] = frozenset(),
            table: dict[str, tuple[set[str], set[str]]] = classes,
        ) -> bool:
            # 这个类是不是响应模型（含间接继承 QwxModel 的）。
            if name in seen or name not in table:
                return False
            bases, _ = table[name]
            if bases & MODEL_BASES:
                return True
            return any(is_model(base, seen | {name}, table) for base in bases)

        for name in classes:
            if not is_model(name):
                continue
            models[f"{package}.{name}"] = resolve(name)

    return models


def _resolve_type(go_type: str, package: str, types: dict[str, Any]) -> str | None:
    """把 Go 类型名解析成契约里的类型键。

    内嵌 struct 在契约里写成简单名（StormState），类型键带包前缀
    （v7/storm.StormState）。
    """
    if go_type in types:
        return go_type
    candidate = f"{package}.{go_type}"
    if candidate in types:
        return candidate
    for key in types:
        if key.rsplit(".", 1)[-1] == go_type:
            return key
    return None


def go_aliases(contract: dict[str, Any]) -> dict[str, set[str]]:
    """从契约里取每个 Go 类型的 json tag 集合。

    Go 的内嵌 struct（没有 json tag 的字段）在 JSON 里是平铺的，
    所以比较时要把内嵌类型的字段并进来 —— Python 侧用继承表达同一件事。
    """
    raw: dict[str, set[str]] = {}
    embeds: dict[str, list[str]] = {}
    for key, info in contract["types"].items():
        raw[key] = {field["json_name"] for field in info["fields"] if field["json_name"]}
        for field in info["fields"]:
            if field["json_name"]:
                continue
            go_type = str(field.get("go_type") or "").strip()
            go_type = go_type.lstrip("*").strip("[]")
            target = _resolve_type(go_type, info.get("package", ""), contract["types"])
            if target is not None:
                embeds.setdefault(key, []).append(target)

    def resolve(key: str, seen: frozenset[str]) -> set[str]:
        if key in seen or key not in raw:
            return set()
        out = set(raw[key])
        for parent in embeds.get(key, []):
            out |= resolve(parent, seen | {key})
        return out

    return {key: resolve(key, frozenset()) for key in raw}


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
