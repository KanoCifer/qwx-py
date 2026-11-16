"""从源码扫出端点常量与缓存键族，供文档生成与漂移校验使用。

端点常量与缓存键族各有一个真源：源码里的常量声明。文档里的表是从源码
扫出来生成的，改了源码忘了改文档，漂移测试会失败。

用法：

    python tools/endpoints.py          # 只报差异
    python tools/endpoints.py --write  # 把扫出的表体写回文档
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Constant",
    "Family",
    "Index",
    "constants_table",
    "extract_block",
    "families_table",
    "replace_block",
    "scan",
]

SRC_DIR = "src"
"""包源码根（相对仓库根）。"""


@dataclass(frozen=True)
class Constant:
    """一个端点常量。"""

    name: str
    """模块内的名字，如 "EndpointCurrent"。"""

    value: str
    """常量的值，如 "weather/v1/current"。

    值发布后不再变更：qwx.TTLPolicy 按值匹配。
    """

    module: str
    """所属模块，如 "qwx.v1.weather"。"""

    methods: tuple[str, ...]
    """使用该常量的端点方法名，按字典序。"""


@dataclass(frozen=True)
class Family:
    """一个缓存键族常量。"""

    name: str
    """枚举成员名，如 "WEATHER"。"""

    prefix: str
    """前缀根，如 "qwx:v1:"。

    前缀与模块名不必对齐（潮汐族是 "qwx:tide:" 而不是 "qwx:ocean:"），
    这是已发布键字面量的约定。
    """

    modules: tuple[str, ...]
    """使用该族的模块，按字典序。"""


@dataclass(frozen=True)
class Index:
    """一次扫描的结果。"""

    constants: tuple[Constant, ...]
    families: tuple[Family, ...]


def scan(root: Path) -> Index:
    """扫描源码目录下的端点常量与缓存键族。"""
    src = root / SRC_DIR
    modules = _module_files(src)
    constants = _scan_constants(modules)
    families = _scan_families(src, modules)
    return Index(constants=constants, families=families)


def constants_table(index: Index, headers: tuple[str, str, str, str], sep: str = "、") -> str:
    """渲染端点常量表。"""
    lines = [
        f"| {headers[0]} | {headers[1]} | {headers[2]} | {headers[3]} |",
        "| --- | --- | --- | --- |",
    ]
    for item in index.constants:
        methods = sep.join(item.methods) if item.methods else "—"
        lines.append(
            f"| `{item.module}.{item.name}` | `{item.value}` | `{item.module}` | {methods} |"
        )
    return "\n".join(lines)


def families_table(index: Index, headers: tuple[str, str, str], sep: str = "、") -> str:
    """渲染缓存键族表。"""
    lines = [
        f"| {headers[0]} | {headers[1]} | {headers[2]} |",
        "| --- | --- | --- |",
    ]
    for item in index.families:
        modules = sep.join(item.modules) if item.modules else "—"
        lines.append(f"| `Family.{item.name}` | `{item.prefix}` | {modules} |")
    return "\n".join(lines)


def extract_block(body: str, begin: str, end: str) -> str | None:
    """取两个标记之间的内容。"""
    start = body.find(begin)
    if start < 0:
        return None
    start += len(begin)
    stop = body.find(end, start)
    if stop < 0:
        return None
    return body[start:stop].strip()


def replace_block(body: str, begin: str, end: str, table: str) -> str:
    """替换两个标记之间的内容。"""
    start = body.find(begin)
    if start < 0:
        return body
    start += len(begin)
    stop = body.find(end, start)
    if stop < 0:
        return body
    return body[:start] + "\n" + table + "\n" + body[stop:]


def _module_files(src: Path) -> list[tuple[str, Path]]:
    """列出全部模块文件与它们所属的包。

    包名取文件所在目录：端点常量在 `<包>/types.py`，请求构造在
    `<包>/client.py`，同一个包里才对得上。
    """
    out: list[tuple[str, Path]] = []
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(src)
        parts = list(rel.parts[:-1])
        if not parts:
            continue
        out.append((".".join(parts), path))
    return out


def _scan_constants(modules: list[tuple[str, Path]]) -> tuple[Constant, ...]:
    """扫出全部端点常量，并找出每个常量被哪些方法用到。"""
    constants: dict[tuple[str, str], str] = {}
    usage: dict[tuple[str, str], set[str]] = {}

    for package, path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        public = _public_methods(tree)
        aliases = _endpoint_aliases(tree)
        helper_endpoints: dict[str, set[str]] = {}
        helper_calls: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            endpoints = _request_endpoints(node)
            if endpoints:
                helper_endpoints[node.name] = endpoints
            helper_calls[node.name] = _called_helpers(node)
        for helper, endpoints in helper_endpoints.items():
            for name in _public_callers(helper, helper_calls, public):
                for endpoint in endpoints:
                    usage.setdefault((package, endpoint), set()).add(name)
        for node in ast.walk(tree):
            target, value = _endpoint_value(node, aliases)
            if target is not None and value is not None:
                constants[(package, target)] = value

    items = [
        Constant(
            name=name,
            value=value,
            module=package,
            methods=tuple(sorted(usage.get((package, name), set()))),
        )
        for (package, name), value in constants.items()
    ]
    return tuple(sorted(items, key=lambda item: (item.module, item.name)))


def _scan_families(src: Path, modules: list[tuple[str, Path]]) -> tuple[Family, ...]:
    """扫出缓存键族常量，以及用到它们的模块。"""
    cachekey = src / "qwx" / "_cachekey.py"
    prefixes: dict[str, str] = {}
    tree = ast.parse(cachekey.read_text(encoding="utf-8"), filename=str(cachekey))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Family":
            for item in node.body:
                if not isinstance(item, ast.Assign) or not isinstance(item.value, ast.Constant):
                    continue
                target = item.targets[0]
                if isinstance(target, ast.Name) and isinstance(item.value.value, str):
                    prefixes[target.id] = item.value.value

    used: dict[str, set[str]] = {name: set() for name in prefixes}
    for module, path in modules:
        if module == "qwx._cachekey":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "Family"
                and node.attr in used
            ):
                used[node.attr].add(module)

    return tuple(
        Family(name=name, prefix=prefix, modules=tuple(sorted(used[name])))
        for name, prefix in sorted(prefixes.items())
    )


def _endpoint_aliases(tree: ast.Module) -> set[str]:
    """找出本模块里指向 Endpoint 类型的名字。

    端点常量有的直接 `from qwx.ttl import Endpoint`，有的改过名
    （`EndpointType`、`_Endpoint`）。只认构造调用，不认名字本身。
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module != "qwx.ttl":
            continue
        for alias in node.names:
            if alias.name == "Endpoint":
                names.add(alias.asname or alias.name)
    return names


def _endpoint_value(node: ast.AST, aliases: set[str]) -> tuple[str | None, str | None]:
    """判断一个赋值是不是端点常量，是则取出名字与值。"""
    if isinstance(node, ast.AnnAssign):
        targets = [node.target]
        value = node.value
    elif isinstance(node, ast.Assign):
        targets = list(node.targets)
        value = node.value
    else:
        return None, None
    if len(targets) != 1 or not isinstance(targets[0], ast.Name):
        return None, None
    if not isinstance(value, ast.Call):
        return None, None
    if not isinstance(value.func, ast.Name) or value.func.id not in aliases:
        return None, None
    if len(value.args) != 1:
        return None, None
    arg = value.args[0]
    if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
        return None, None
    return targets[0].id, arg.value


def _request_endpoints(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """找出函数体里 Request(...) 用到的端点常量名。"""
    found: set[str] = set()
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        if not isinstance(inner.func, ast.Name) or inner.func.id != "Request":
            continue
        for keyword in inner.keywords:
            if keyword.arg == "endpoint" and isinstance(keyword.value, ast.Name):
                found.add(keyword.value.id)
    return found


def _called_helpers(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """函数体里调用到的内部方法名。

    端点族把请求构造放在 `_xxx_call` 里，对外的方法转调它 —— 顺着这条
    链才能知道某个端点常量服务于哪些对外方法。
    """
    found: set[str] = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
            found.add(inner.func.attr)
    return found


def _public_callers(
    helper: str,
    helper_calls: dict[str, set[str]],
    public: set[str],
) -> set[str]:
    """找出转调了某个内部方法的对外方法名。"""
    return {name for name, called in helper_calls.items() if name in public and helper in called}


def _public_methods(tree: ast.Module) -> set[str]:
    """模块里对外暴露的方法名。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(
                item, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and not item.name.startswith("_"):
                names.add(item.name)
    return names


_SECTIONS = (
    ("docs/endpoints.md", "constants", ("端点常量", "值", "模块", "方法"), "、"),
    ("docs/zh/endpoints.md", "constants", ("端点常量", "值", "模块", "方法"), "、"),
    ("docs/en/endpoints.md", "constants", ("Endpoint constant", "Value", "Module", "Method"), ", "),
    ("docs/caching.md", "families", ("族常量", "前缀根", "模块"), "、"),
    ("docs/zh/cache.md", "families", ("族常量", "前缀根", "模块"), "、"),
    ("docs/en/cache.md", "families", ("Family constant", "Prefix root", "Module"), ", "),
)


def main() -> int:
    """刷新文档里的生成表，或只报差异。"""
    parser = argparse.ArgumentParser(description="扫描端点常量并刷新文档里的表")
    parser.add_argument("--write", action="store_true", help="把扫出的表体写回文档")
    parser.add_argument("--check", action="store_true", help="只校验漂移（默认行为）")
    parser.add_argument("--root", default=".", help="仓库根目录")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index = scan(root)
    drift = False

    for path, kind, headers, sep in _SECTIONS:
        begin = f"<!-- BEGIN GENERATED: {kind} -->"
        end = f"<!-- END GENERATED: {kind} -->"
        target = root / path
        if not target.exists():
            # 内部文档不在版本控制里（.gitignore 忽略 docs/*），新克隆的仓库里没有。
            continue
        body = target.read_text(encoding="utf-8")
        want = (
            constants_table(index, headers, sep)
            if kind == "constants"
            else families_table(index, headers, sep)
        )
        got = extract_block(body, begin, end)
        if got is None:
            print(f"{path} 缺少标记 {begin}", file=sys.stderr)
            return 1
        if got == want:
            continue
        drift = True
        if not args.write:
            print(f"{path} 与源码不一致，用 --write 刷新", file=sys.stderr)
            continue
        target.write_text(replace_block(body, begin, end, want), encoding="utf-8")
        print(f"已刷新 {path}")

    return 1 if drift and not args.write else 0


if __name__ == "__main__":
    raise SystemExit(main())
