#!/usr/bin/env python3
"""从契约基线生成 docs/endpoints.md。

输入 `contract/endpoints.json`：由 `tools/extract_go_contract.py` 从 Go 源码
抽取，已与 Go 仓库的 `docs/endpoints.md` 逐项对账。

输出 `docs/endpoints.md`：Python 侧的端点索引，是生成物，不要手改。

用法：
    python tools/gen_endpoints.py         # 写文件
    python tools/gen_endpoints.py --check # 只校验漂移，有漂移退出码非零
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "contract" / "endpoints.json"
DOC_PATH = ROOT / "docs" / "endpoints.md"


def load_contract(path: Path) -> dict[str, Any]:
    """读契约基线。"""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def code(text: str) -> str:
    """把文本包成行内代码。"""
    return f"`{text}`"


def const_name(endpoint: dict[str, Any]) -> str:
    """端点常量的短名，如 `EndpointCurrent`。"""
    return endpoint["endpoint_constant"].rsplit(".", 1)[-1]


def const_path(endpoint: dict[str, Any]) -> str:
    """端点常量的 Python 全路径，如 `qwx.v1.weather.EndpointCurrent`。"""
    return f"{endpoint['py_package']}.{const_name(endpoint)}"


def render(contract: dict[str, Any]) -> str:
    """渲染 docs/endpoints.md。"""
    endpoints = contract["endpoints"]
    lines: list[str] = []

    lines.append("# 端点索引")
    lines.append("")
    lines.append(
        "一处看全所有端点：Python 模块、方法名、端点常量、上游路径、位置形态、"
        "默认 TTL、缓存键前缀与缓存键模板。"
    )
    lines.append("")
    lines.append("表体是生成物，不要手改：")
    lines.append("")
    lines.append("```bash")
    lines.append("python tools/gen_endpoints.py         # 写文件")
    lines.append("python tools/gen_endpoints.py --check # 只校验漂移")
    lines.append("```")
    lines.append("")
    lines.append(
        "数据源是 `contract/endpoints.json` —— 由 `tools/extract_go_contract.py` "
        "从 Go 源码抽取的契约基线，已与 Go 仓库的 `docs/endpoints.md` 逐项对账。"
        "Python 侧的端点常量值与默认 TTL 由 `tests/test_endpoints_doc.py` "
        "反向核对这份基线。"
    )
    lines.append("")
    lines.append(
        "端点常量的真源在各端点族的 `types.py`（`qwx.v1.weather.EndpointCurrent`、"
        "`qwx.geo.EndpointCity`……）。一个包只导出一个端点时，常量名就是 "
        "`Endpoint`（`qwx.v1.alert.Endpoint`、`qwx.v7.ocean.Endpoint`）。"
        "常量的**值**发布后不再变更：`qwx.TTLPolicy` 按值匹配，改值会让用户的 "
        "TTL 配置静默失效。"
    )
    lines.append("")
    lines.append(f"端点总数：**{len(endpoints)}**。")
    lines.append("")

    lines.append("## 端点常量总览")
    lines.append("")
    lines.append("| 端点常量 | 值 | 模块 | 方法 |")
    lines.append("| --- | --- | --- | --- |")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for endpoint in endpoints:
        grouped.setdefault(const_path(endpoint), []).append(endpoint)
    for const, group in grouped.items():
        lines.append(
            "| {const} | {value} | {module} | {methods} |".format(
                const=code(const),
                value=code(group[0]["endpoint"]),
                module=code(group[0]["py_package"]),
                methods="、".join(code(e["py_method"]) for e in group),
            )
        )
    lines.append("")

    lines.append("## 端点方法总表")
    lines.append("")
    header = "| 包 | 方法 | 端点常量 | 上游路径 | 位置形态 | 默认 TTL | 缓存键前缀 | 缓存键模板 |"
    lines.append(header)
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    row = "| {pkg} | {method} | {const} | {path} | {shape} | {ttl} | {prefix} | {template} |"
    for endpoint in endpoints:
        lines.append(
            row.format(
                pkg=code(endpoint["py_package"]),
                method=code(endpoint["py_method"]),
                const=code(const_path(endpoint)),
                path=code(endpoint["upstream_path"]),
                shape=endpoint["location_shape"],
                ttl=endpoint["default_ttl"],
                prefix=code(endpoint["cache_prefix"]),
                template=code(endpoint["cache_key_template"]),
            )
        )
    lines.append("")

    lines.append("## 位置形态")
    lines.append("")
    lines.append("位置形态决定调用方怎么传位置。形态互不等价，传错的上游直接拒绝：")
    lines.append("")
    lines.append("| 形态 | 怎么构造 | 谁认 |")
    lines.append("| --- | --- | --- |")
    lines.append(
        "| 坐标对 | `qwx.Location(lat=39.92, lon=116.41)` 或 "
        '`qwx.parse_location("116.41,39.92")` | 新一代全部端点；'
        "v7 的生活指数、分钟级降水、太阳高度角 |"
    )
    lines.append('| 坐标对 / LocationID | `qwx.Location(id="101010100")` | 天文的日出日落与月相 |')
    lines.append(
        '| 坐标对 / LocationID / 地名 | `qwx.Location(name="杭州")` | '
        "GeoAPI 的城市检索与 POI 检索 |"
    )
    lines.append('| 站点 ID | `qwx.Location(id="P2352")` | 潮汐、空气质量监测站 |')
    lines.append("")
    lines.append("新一代的路径参数是**纬度在前**，v7 与 GeoAPI 的查询参数是**经度在前**。")
    lines.append("")
    lines.append(
        "每个端点认哪种形态见上面的方法总表。参数上限、返回类型、字段单位见 "
        "[contract.md](contract.md)；上游的怪癖见 [gotchas.md](gotchas.md)。"
    )
    lines.append("")

    lines.append("## 缓存时长")
    lines.append("")
    lines.append("默认时长由端点包内置，用户用 `qwx.TTLPolicy` 按端点覆盖：")
    lines.append("")
    lines.append("```python")
    lines.append("from datetime import timedelta")
    lines.append("")
    lines.append("import qwx")
    lines.append("from qwx.v1.airquality import EndpointCurrent as AQCurrent")
    lines.append("from qwx.v1.weather import EndpointCurrent")
    lines.append("")
    lines.append("policy = qwx.TTLMap({")
    lines.append("    EndpointCurrent: timedelta(seconds=30),")
    lines.append("    AQCurrent: timedelta(0),  # 该端点不缓存")
    lines.append("})")
    lines.append('client = qwx.Client(auth, "abcxyz.qweatherapi.com", ttl_policy=policy)')
    lines.append("```")
    lines.append("")
    lines.append(
        "优先级：单次上下文覆盖（`qwx.override_ttl`） > `TTLPolicy` > 端点默认时长。"
        "TTL 与缓存键是两回事：改 TTL 不会让已写入的旧条目提前失效。"
    )
    lines.append("")

    lines.append("## 加新端点时")
    lines.append("")
    lines.append(
        "- 端点常量放进所属资源族的 `types.py`：包里有多个端点时命名 "
        "`EndpointFoo`，只有一个时命名 `Endpoint`。"
    )
    lines.append(
        "- 在 `client.py` 构造的 `qwx.Request` 里填上 `endpoint` 与 `ttl`，用户才能按端点调 TTL。"
    )
    lines.append(
        "- 缓存键在 `qwx/_cachekey.py` 里拼：选一个 `Family`，用 `Params` 声明"
        "影响结果的参数，不要自己拼 `:lang=` 这类字符串。"
    )
    lines.append("- 跑 `python tools/gen_endpoints.py` 更新本文件的表体。")
    lines.append(
        "- 同步 [contract.md](contract.md) 的端点表、[caching.md](caching.md) 的"
        "键表与 TTL 表、README 的「支持的接口」表。"
    )
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 docs/endpoints.md")
    parser.add_argument("--check", action="store_true", help="只校验漂移，不写文件")
    args = parser.parse_args(argv)

    contract = load_contract(CONTRACT_PATH)
    content = render(contract)

    if args.check:
        if not DOC_PATH.exists():
            print(f"gen: {DOC_PATH} 不存在", file=sys.stderr)
            return 1
        current = DOC_PATH.read_text(encoding="utf-8")
        if current == content:
            print(f"gen: 校验通过 端点 {len(contract['endpoints'])} 个")
            return 0
        diff = list(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=str(DOC_PATH),
                tofile="重新生成的内容",
            )
        )
        print("gen: docs/endpoints.md 与契约基线漂移", file=sys.stderr)
        sys.stderr.writelines(diff)
        return 1

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(content, encoding="utf-8")
    print(f"gen: 已写入 {DOC_PATH} 端点 {len(contract['endpoints'])} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
