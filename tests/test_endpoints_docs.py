"""文档漂移校验：文档里的表要与源码一致。

端点常量与缓存键族各有一个真源：源码里的常量声明。文档里的表是从源码扫
出来生成的，改了源码忘了改文档，这些测试会失败。

刷新命令：`python tools/endpoints.py --write`。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from tools.endpoints import (
    Index,
    constants_table,
    extract_block,
    families_table,
    scan,
)

ROOT = Path(__file__).resolve().parent.parent

CONSTANT_HEADERS_ZH = ("端点常量", "值", "模块", "方法")
CONSTANT_HEADERS_EN = ("Endpoint constant", "Value", "Module", "Method")
FAMILY_HEADERS_ZH = ("族常量", "前缀根", "模块")
FAMILY_HEADERS_EN = ("Family constant", "Prefix root", "Module")

CELL = chr(96)
"""Markdown 里的反引号。"""


@pytest.fixture(scope="module")
def index() -> Index:
    """扫一次源码，供多个测试复用。"""
    return scan(ROOT)


def _rows(path: Path) -> list[list[str]]:
    """取出 Markdown 表格里每一行的单元格。"""
    out: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("|"):
            continue
        out.append([cell.strip() for cell in text.strip("|").split("|")])
    return out


def _cell(cells: list[str], pattern: str) -> str | None:
    """取第一个匹配正则的单元格内容（去掉反引号）。"""
    for cell in cells:
        match = re.fullmatch(pattern, cell.strip(CELL))
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return None


@pytest.mark.parametrize(
    ("path", "kind", "headers", "separator"),
    [
        ("docs/zh/endpoints.md", "constants", CONSTANT_HEADERS_ZH, "、"),
        ("docs/en/endpoints.md", "constants", CONSTANT_HEADERS_EN, ", "),
        ("docs/zh/cache.md", "families", FAMILY_HEADERS_ZH, "、"),
        ("docs/en/cache.md", "families", FAMILY_HEADERS_EN, ", "),
    ],
)
def test_generated_tables_are_in_sync(
    index: Index,
    path: str,
    kind: str,
    headers: tuple[str, ...],
    separator: str,
) -> None:
    """生成块里的表体要与源码扫出的一致。"""
    body = (ROOT / path).read_text(encoding="utf-8")
    begin = f"<!-- BEGIN GENERATED: {kind} -->"
    end = f"<!-- END GENERATED: {kind} -->"
    got = extract_block(body, begin, end)
    assert got is not None, f"{path} 缺少生成标记"

    if kind == "constants":
        want = constants_table(index, headers, separator)
    else:
        want = families_table(index, headers, separator)
    assert got == want, f"{path} 的表与源码不一致，用 python tools/endpoints.py --write 刷新"


@pytest.mark.parametrize("path", ["docs/zh/endpoints.md", "docs/en/endpoints.md"])
def test_endpoint_table_covers_every_constant(index: Index, path: str) -> None:
    """方法总表要覆盖全部端点常量。

    源码里有、文档里没有的端点，读者就查不到。
    """
    rows = _rows(ROOT / path)
    documented = {
        name
        for cells in rows
        if (name := _cell(cells, r"qwx(?:\.[A-Za-z0-9_]+)*\.Endpoint[A-Za-z0-9_]*"))
    }
    scanned = {f"{item.module}.{item.name}" for item in index.constants}
    assert scanned <= documented, f"{path} 漏掉了端点常量：{sorted(scanned - documented)}"


@pytest.mark.parametrize("path", ["README.md", "README_EN.md"])
def test_readme_table_covers_every_endpoint(index: Index, path: str) -> None:
    """README 的接口表要覆盖全部端点方法。"""
    rows = _rows(ROOT / path)
    pairs = set()
    for cells in rows:
        package = _cell(cells, r"qwx(?:\.[A-Za-z0-9_]+)*")
        method = _cell(cells, r"[a-z][a-z0-9_]*")
        if package is not None and method is not None:
            pairs.add((package, method))
    missing = [
        f"{item.module}.{method}"
        for item in index.constants
        for method in item.methods
        if (item.module, method) not in pairs
    ]
    assert not missing, f"{path} 漏掉了端点方法：{missing}"


def test_every_constant_is_used_by_some_method(index: Index) -> None:
    """端点常量要挂在端点方法上。

    挂不上说明扫描器跟丢了调用链，文档表会少一列信息。
    """
    unused = [f"{item.module}.{item.name}" for item in index.constants if not item.methods]
    assert not unused, f"这些端点常量没找到使用方：{unused}"


def test_every_family_is_used_by_some_module(index: Index) -> None:
    """键族要挂在模块上。"""
    unused = [f"Family.{item.name}" for item in index.families if not item.modules]
    assert not unused, f"这些键族没有模块引用：{unused}"
