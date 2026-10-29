#!/usr/bin/env python3
"""从 Go 源码抽取 qwx 契约基线。

契约基线包含两部分：

1. 端点契约：上游路径、位置形态、默认 TTL、缓存键模板、查询参数、端点常量。
2. 类型契约：每个响应类型的字段，含 Go 字段名、json tag、Go 类型、可选性与注释。

位置形态以 Go 仓库的 docs/endpoints.md 为准 —— 那张表由 internal/endpoints
从源码生成。其余取值全部由源码抽取，并与那张表逐项对账；对不上就报错退出。

用法：
    python tools/extract_go_contract.py --go-root ../qwx
    python tools/extract_go_contract.py --go-root ../qwx --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

GO_SKIP_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".venv",
    "__pycache__",
    "internal",
    "rediscache",
    "examples",
    "live",
    "docs",
    "assets",
}

FIELD_RE = re.compile(r"^(?P<name>[A-Za-z_]\w*)\s+(?P<type>[^\s\`]+)(?:\s+\`(?P<tag>[^\`]*)\`)?$")
JSON_TAG_RE = re.compile(r'json:"(?P<name>[^",]*)(?P<opts>[^"]*)"')
TYPE_DECL_RE = re.compile(r"^type\s+(?P<name>\w+)\s+(?P<kind>struct\s*\{|\S.*)$")
CONST_BLOCK_RE = re.compile(r"^(?:const|var)\s*\($")
CONST_SINGLE_RE = re.compile(r"^(?:const|var)\s+(\w+)(?:\s+\w+)?\s*=\s*(.+)$")
CONST_ENTRY_RE = re.compile(r"^(\w+)(?:\s+\w+)?\s*=\s*(.+)$")
ENDPOINT_CONST_RE = re.compile(r'^qwx\.Endpoint\("([^"]+)"\)$')
DURATION_RE = re.compile(r"(\d+)\s*\*\s*time\.(Second|Minute|Hour)")
DURATION_UNIT_RE = re.compile(r"time\.(Second|Minute|Hour)\b")
FAMILY_RE = re.compile(r"^\s*(Family\w+)\s+Family\s*=\s*\"([^\"]*)\"$", re.M)
WRITE_STRING_RE = re.compile(r'WriteString\("(?P<prefix>[^"]*)"(?:\s*\+\s*(?P<val>[^)]*))?\)')
METHOD_RE = re.compile(r"^func \(c \*Client\) (\w+)\(", re.M)
REQUEST_FIELD_RE = {
    "path": re.compile(r"Path:\s*(?P<expr>.+?),\s*$", re.M),
    "endpoint": re.compile(r"Endpoint:\s*(?P<expr>\w+),\s*$", re.M),
    "ttl": re.compile(r"TTL:\s*(?P<expr>\w+),\s*$", re.M),
    "cache_key": re.compile(r"CacheKey:\s*(?P<expr>.+?),\s*$", re.M),
}
QSET_RE = re.compile(r'q\.Set\("(?P<name>[^"]+)",\s*(?P<expr>.+?)\),\s*$', re.M)
CACHE_CALL_RE = re.compile(r"\.(Path|PathCoord|Count|Params)\((?P<args>(?:[^()]|\([^()]*\))*)\)")

DURATION_UNITS = {"Second": 1, "Minute": 60, "Hour": 3600}

PARAM_PLACEHOLDERS = {
    "Lang": "lang",
    "LocalTime": "localTime",
    "Number": "n",
    "Radius": "r",
    "Adm": "adm",
    "Range": "range",
    "City": "city",
    "Interval": "interval",
    "Tilt": "tilt",
    "Azimuth": "azimuth",
    "Extra": "extra",
    "Project": "project",
    "Credential": "credential",
}

# 缓存键占位符 → Python 的 Params 字段名。
#
# 占位符是已发布的键字面量，不能改；Python 侧的字段名走 PEP 8。
PY_PARAM_NAMES = {
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

PLACEHOLDER_ALIASES = {
    "loc": "location",
    "stationID": "station_id",
    "stormID": "storm_id",
    "typeSeg": "type",
    "timeStr": "time",
}


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------


def snake_case(name: str) -> str:
    """CamelCase 转 snake_case，缩略串按一个词处理。

    FXTime -> fx_time，AQIDisplay -> aqi_display，ID -> id，POIs -> pois。
    """
    if re.fullmatch(r"[A-Z]+s", name):
        return name.lower()
    step = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    step = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step)
    return step.lower()


def to_camel(name: str) -> str:
    """snake_case 转 camelCase，与 pydantic.alias_generators.to_camel 一致。"""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def placeholder(ident: str) -> str:
    """把 Go 标识符转成缓存键模板里的占位符。"""
    return PLACEHOLDER_ALIASES.get(ident, snake_case(ident))


ARG_PLACEHOLDERS = {
    "Query": "location",
    "ID": "id",
    "Lat": "lat",
    "Lon": "lon",
}


def arg_placeholder(arg: str) -> str:
    """把缓存键链式调用里的实参转成占位符。

    loc.Query() 是位置参数，loc.ID 是 LocationID，string(typ) 是类型段。
    """
    text = arg.strip()
    inner = re.search(r"\(([^()]*)\)", text)
    if inner and inner.group(1).strip():
        text = inner.group(1).strip()
    name = text.rstrip("()").split(".")[-1].strip()
    if name in ARG_PLACEHOLDERS:
        return ARG_PLACEHOLDERS[name]
    return placeholder(name)


def split_top_level(text: str, sep: str = ",") -> list[str]:
    """按分隔符切分，忽略括号与字符串里的分隔符。"""
    out: list[str] = []
    depth = 0
    buf: list[str] = []
    in_str = False
    for ch in text:
        if in_str:
            buf.append(ch)
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            buf.append(ch)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def parse_duration_seconds(expr: str) -> int | None:
    """把 Go 的 duration 字面量解析成秒。"""
    match = DURATION_RE.search(expr)
    if match:
        return int(match.group(1)) * DURATION_UNITS[match.group(2)]
    match = DURATION_UNIT_RE.search(expr)
    if match:
        return DURATION_UNITS[match.group(1)]
    return None


def format_ttl(seconds: int) -> str:
    """把秒数格式化成人类可读的 TTL。"""
    if seconds % 3600 == 0:
        return f"{seconds // 3600} 小时"
    if seconds % 60 == 0:
        return f"{seconds // 60} 分钟"
    return f"{seconds} 秒"


# --------------------------------------------------------------------------
# Go 源码扫描
# --------------------------------------------------------------------------


def scan_go(text: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """扫一个 Go 文件，取出类型定义与常量。"""
    lines = text.splitlines()
    types: dict[str, dict[str, Any]] = {}
    consts: dict[str, dict[str, Any]] = {}
    pending: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("//"):
            pending.append(stripped[2:].strip())
            i += 1
            continue

        type_match = TYPE_DECL_RE.match(stripped)
        if type_match and type_match.group("kind").startswith("struct"):
            name = type_match.group("name")
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != "}":
                body.append(lines[i])
                i += 1
            types[name] = {
                "kind": "struct",
                "doc": " ".join(p for p in pending if p),
                "fields": parse_struct_body(body),
            }
            pending = []
            continue

        if type_match and stripped.startswith("type "):
            name = type_match.group("name")
            types[name] = {
                "kind": type_match.group("kind").strip(),
                "doc": " ".join(p for p in pending if p),
                "fields": [],
            }
            pending = []
            i += 1
            continue

        single = CONST_SINGLE_RE.match(stripped)
        if single:
            consts[single.group(1)] = {
                "expr": single.group(2).strip(),
                "doc": " ".join(p for p in pending if p),
            }
            pending = []
            i += 1
            continue

        if CONST_BLOCK_RE.match(stripped):
            i += 1
            while i < len(lines) and lines[i].strip() != ")":
                entry = lines[i].strip()
                if entry.startswith("//"):
                    pending.append(entry[2:].strip())
                elif entry:
                    item = CONST_ENTRY_RE.match(entry)
                    if item:
                        consts[item.group(1)] = {
                            "expr": item.group(2).strip(),
                            "doc": " ".join(p for p in pending if p),
                        }
                    pending = []
                i += 1
            i += 1
            pending = []
            continue

        pending = []
        i += 1

    return types, consts


def parse_struct_body(body: list[str]) -> list[dict[str, Any]]:
    """解析 struct 体里的字段。"""
    fields: list[dict[str, Any]] = []
    pending: list[str] = []
    for raw in body:
        stripped = raw.strip()
        if not stripped:
            pending = []
            continue
        if stripped.startswith("//"):
            pending.append(stripped[2:].strip())
            continue
        match = FIELD_RE.match(stripped)
        if not match:
            fields.append(
                {
                    "go_name": "",
                    "go_type": stripped,
                    "json_name": None,
                    "doc": " ".join(p for p in pending if p),
                    "unparsed": True,
                }
            )
            pending = []
            continue
        tag = match.group("tag")
        json_name = None
        if tag:
            tag_match = JSON_TAG_RE.search(tag)
            if tag_match:
                json_name = tag_match.group("name")
        fields.append(
            {
                "go_name": match.group("name"),
                "go_type": match.group("type"),
                "json_name": json_name,
                "doc": " ".join(p for p in pending if p),
                "unparsed": False,
            }
        )
        pending = []
    return fields


def parse_params(text: str) -> list[dict[str, str]]:
    """解析方法参数列表。"""
    names: list[str] = []
    typ = ""
    for part in split_top_level(text):
        tokens = part.split()
        if not tokens:
            continue
        if len(tokens) == 1:
            names.append(tokens[0])
        else:
            names.extend(tokens[:-1])
            typ = tokens[-1]
    return [{"name": n, "type": typ} for n in names]


def parse_methods(text: str, functions: dict[str, str]) -> list[dict[str, Any]]:
    """解析 client.go 里的端点方法。"""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if METHOD_RE.match(line)]
    methods: list[dict[str, Any]] = []

    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        region = lines[start:end]
        signature = region[0].strip()

        doc_lines: list[str] = []
        for raw in reversed(lines[:start]):
            stripped = raw.strip()
            if stripped.startswith("//"):
                doc_lines.insert(0, stripped[2:].strip())
                continue
            break

        name_match = METHOD_RE.match(signature)
        name = name_match.group(1) if name_match else ""

        params_text = ""
        ret_text = ""
        # 方法签名里的左括号在方法名之后，receiver 的括号不算。
        open_paren = (name_match.end() - 1) if name_match else -1
        if open_paren >= 0:
            depth = 0
            close = -1
            for idx in range(open_paren, len(signature)):
                if signature[idx] == "(":
                    depth += 1
                elif signature[idx] == ")":
                    depth -= 1
                    if depth == 0:
                        close = idx
                        break
            if close > 0:
                params_text = signature[open_paren + 1 : close]
                ret_text = signature[close + 1 :].strip().rstrip("{").strip()

        body = "\n".join(region)
        request: dict[str, str] = {}
        for key, pattern in REQUEST_FIELD_RE.items():
            found = pattern.search(body)
            if found:
                request[key] = found.group("expr").strip()

        delegate = re.search(r"return c\.(\w+)\(", body)

        # 校验逻辑多在独立的 validate/require 辅助函数里，一并纳入。
        guards = [
            line.strip()
            for line in region
            if re.match(r"^\s*if\b", line) and re.search(r"[<>!=]", line)
        ]
        for candidate in re.findall(r"\b(\w+)\(", body):
            if candidate in SKIP_CALLS:
                continue
            helper = functions.get(candidate)
            if helper and ("ErrInvalidParameter" in helper or "ErrInvalidLocation" in helper):
                guards.extend(guard_lines(helper))

        methods.append(
            {
                "name": name,
                "params": parse_params(params_text),
                "returns": ret_text,
                "doc": " ".join(d for d in doc_lines if d),
                "request": request,
                "query": [
                    {"name": q.group("name"), "expr": q.group("expr").strip()}
                    for q in QSET_RE.finditer(body)
                ],
                "guards": guards,
                "validations": [
                    line.strip()
                    for line in region
                    if "ErrInvalidParameter" in line or "ErrInvalidLocation" in line
                ],
                "delegates_to": delegate.group(1) if delegate else "",
            }
        )

    return methods


FUNC_RE = re.compile(r"^func (\w+)\(", re.M)

SKIP_CALLS = {
    "if",
    "for",
    "return",
    "fmt",
    "qwx",
    "cachekey",
    "strconv",
    "strings",
    "make",
    "append",
    "len",
    "cap",
    "panic",
    "time",
    "errors",
    "json",
    "context",
    "int",
    "float64",
    "string",
    "bool",
}


def extract_functions(text: str) -> dict[str, str]:
    """取出文件里所有函数的体。"""
    out: dict[str, str] = {}
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        match = FUNC_RE.match(line)
        if not match or not line.rstrip().endswith("{"):
            continue
        body: list[str] = []
        for raw in lines[idx + 1 :]:
            if raw.strip() == "}":
                break
            body.append(raw)
        out[match.group(1)] = "\n".join(body)
    return out


def guard_lines(body: str) -> list[str]:
    """挑出函数体里的比较判断行。"""
    out: list[str] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if re.match(r"^if\b", stripped) and re.search(r"[<>!=]", stripped):
            out.append(stripped)
    return out


# --------------------------------------------------------------------------
# 缓存键模板
# --------------------------------------------------------------------------


def parse_families(go_root: Path) -> dict[str, str]:
    """取 internal/cachekey 里的族前缀。"""
    text = (go_root / "internal" / "cachekey" / "cachekey.go").read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in FAMILY_RE.finditer(text)}


def parse_params_suffix(go_root: Path) -> str:
    """从 internal/cachekey/params.go 还原参数后缀模板。"""
    text = (go_root / "internal" / "cachekey" / "params.go").read_text(encoding="utf-8")
    parts = text.split("func (p Params) suffix() string {", 1)
    if len(parts) < 2:
        raise SystemExit("extract: 未找到 Params.suffix")
    body = parts[1].split("\n}", 1)[0]

    chunks: list[str] = []
    for match in WRITE_STRING_RE.finditer(body):
        prefix = match.group("prefix")
        value = match.group("val")
        if not value:
            chunks.append(prefix)
            continue
        field = re.search(r"p\.(\w+)", value)
        key = PARAM_PLACEHOLDERS.get(field.group(1)) if field else None
        if key is None:
            chunks.append(prefix)
            continue
        chunks.append(f"{prefix}{{{key}}}")
    return "".join(chunks)


def extract_cache_helpers(text: str) -> dict[str, str]:
    """取出 client.go 里的缓存键辅助函数体。"""
    helpers: dict[str, str] = {}
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        match = re.match(r"^func (\w*[cC]acheKey)\(.*\) string \{", line)
        if not match:
            continue
        body: list[str] = []
        for raw in lines[idx + 1 :]:
            if raw.strip() == "}":
                break
            body.append(raw)
        helpers[match.group(1)] = "\n".join(body)
    return helpers


def render_cache_key(
    expr: str,
    helpers: dict[str, str],
    families: dict[str, str],
    suffix: str,
) -> tuple[str, str] | None:
    """把缓存键表达式渲染成模板。

    返回 (完整键模板, 族前缀)。支持三种写法：字面量拼接、cachekey 链式
    构造、调用本文件里的辅助函数。
    """
    expr = " ".join(expr.split())
    if not expr:
        return None

    if expr.startswith('"'):
        out: list[str] = []
        prefix_parts: list[str] = []
        seen_ident = False
        for literal_part, ident in re.findall(r'"([^"]*)"|(\w+)', expr):
            if ident:
                seen_ident = True
                out.append("{" + placeholder(ident) + "}")
                continue
            out.append(literal_part)
            if not seen_ident:
                prefix_parts.append(literal_part)
        family = "".join(prefix_parts)
        if not family.endswith(":"):
            family = ""
        return "".join(out), family

    chain_source = expr
    helper_match = re.fullmatch(r"(\w+)\(.*\)", expr)
    if helper_match and helper_match.group(1) in helpers:
        chain_source = helpers[helper_match.group(1)]

    family_match = re.search(r"cachekey\.New\(cachekey\.(Family\w+)\)", chain_source)
    if not family_match:
        return None
    family = families.get(family_match.group(1))
    if family is None:
        return None

    tail = chain_source[family_match.end() :]
    # Go 的链式调用常把点号留在行尾，匹配前先把 ".\s+" 归一。
    tail = re.sub(r"\.\s+", ".", tail)

    segments: list[str] = []
    suffix_part = ""
    for match in CACHE_CALL_RE.finditer(tail):
        kind = match.group(1)
        args = match.group("args")
        if kind == "Path":
            for arg in split_top_level(args):
                arg = arg.strip()
                if not arg:
                    continue
                pieces: list[str] = []
                for piece in arg.split("+"):
                    piece = piece.strip()
                    if not piece:
                        continue
                    if piece.startswith('"'):
                        pieces.append(piece.strip('"'))
                    else:
                        pieces.append("{" + arg_placeholder(piece) + "}")
                if pieces:
                    segments.append("".join(pieces))
        elif kind == "PathCoord":
            segments.append("{lat},{lon}")
        elif kind == "Count":
            arg_list = split_top_level(args)
            name = arg_list[0].strip().strip('"') if arg_list else ""
            var = arg_list[1].strip() if len(arg_list) > 1 else "n"
            segments.append(f"{name}{{{arg_placeholder(var)}}}")
        elif kind == "Params":
            suffix_part = suffix

    return family + ":".join(segments) + suffix_part, family


def render_path(expr: str) -> str:
    """把上游路径表达式渲染成模板。

    占位符沿用 Go 的标识符写法，与 Go 仓库的端点表逐字一致。
    """
    expr = " ".join(expr.split())
    out: list[str] = []
    for part in expr.split("+"):
        part = part.strip()
        if not part:
            continue
        if part.startswith('"'):
            out.append(part.strip('"'))
            continue
        itoa = re.search(r"Itoa\((\w+)\)", part)
        if itoa:
            out.append("{" + itoa.group(1) + "}")
            continue
        out.append("{" + part.split(".")[-1] + "}")
    return "".join(out)


# --------------------------------------------------------------------------
# Go 的 docs/endpoints.md 对账
# --------------------------------------------------------------------------


def parse_go_endpoints_doc(go_root: Path) -> dict[str, dict[str, str]]:
    """读 Go 仓库生成的端点表，作为位置形态的权威来源。"""
    text = (go_root / "docs" / "endpoints.md").read_text(encoding="utf-8")
    table: dict[str, dict[str, str]] = {}

    in_methods = False
    for line in text.splitlines():
        if line.startswith("## 端点方法总表"):
            in_methods = True
            continue
        if in_methods and line.startswith("## "):
            break
        if not in_methods or not line.startswith("|"):
            continue
        cells = [c.strip().strip(chr(96)) for c in line.strip().strip("|").split("|")]
        if len(cells) != 7 or cells[0] in {"包", "---"}:
            continue
        pkg, method, path, shape, ttl, prefix, constant = cells
        table[f"{pkg}.{method}"] = {
            "package": pkg,
            "method": method,
            "upstream_path": path,
            "location_shape": shape,
            "default_ttl": ttl,
            "cache_prefix": prefix,
            "endpoint_constant": constant,
        }
    return table


def response_type(returns: str) -> str:
    """从 Go 的返回签名里取结果类型名。"""
    text = returns.strip()
    if text.startswith("("):
        text = text[1:]
    text = text.split(",")[0]
    return text.strip().lstrip("*").strip()


def parse_limits(
    validations: list[str], consts: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """从校验表达式里还原参数约束。

    形如 hours > MaxForecastHours 的比较取常量的值，形如 days != 1 && days != 3
    的比较取允许值集合，形如 len(date) != 8 的比较取长度。
    """
    limits: dict[str, dict[str, Any]] = {}

    for line in validations:
        for var, op, const in re.findall(r"(\w+)\s*([<>]=?)\s*(\w+)", line):
            if var in {"if", "for", "return", "len"}:
                continue
            raw = const.strip()
            if raw.isdigit():
                value = int(raw)
            else:
                expr = consts.get(raw, {}).get("expr", "").strip()
                if not re.fullmatch(r"\d+", expr):
                    continue
                value = int(expr)
            entry = limits.setdefault(snake_case(var), {})
            if op.startswith("<"):
                entry["min"] = value
            else:
                entry["max"] = value

        length = re.search(r"len\((\w+)\)\s*!=\s*(\d+)", line)
        if length:
            limits.setdefault(snake_case(length.group(1)), {})["length"] = int(length.group(2))

        allowed = re.search(r"(\w+)\s*!=\s*(\d+)\s*&&\s*\1\s*!=\s*(\d+)", line)
        if allowed:
            limits[snake_case(allowed.group(1))] = {
                "allowed": [int(allowed.group(2)), int(allowed.group(3))]
            }
            continue

        one = re.search(r"(\w+)\s*!=\s*(\w+)", line)
        if one:
            expr = consts.get(one.group(2), {}).get("expr", "").strip()
            if expr.startswith('"'):
                limits.setdefault(snake_case(one.group(1)), {})["one_of"] = [expr.strip('"')]

    return limits


def describe_limit(bound: dict[str, Any]) -> str:
    """把参数约束写成人读的一行。"""
    if "allowed" in bound:
        return "只取 " + " 或 ".join(str(v) for v in bound["allowed"])
    if "one_of" in bound:
        return "只取 " + " 或 ".join(bound["one_of"])
    if "length" in bound:
        return f"长度 = {bound['length']}"
    low = bound.get("min")
    high = bound.get("max")
    if low is not None and high is not None:
        return f"{low} ≤ 值 ≤ {high}"
    if high is not None:
        return f"值 ≤ {high}"
    if low is not None:
        return f"值 ≥ {low}"
    return ""


# --------------------------------------------------------------------------
# 契约组装
# --------------------------------------------------------------------------

GO_SKIP_DIRS = GO_SKIP_DIRS


def discover_packages(go_root: Path) -> list[Path]:
    """找出所有含 client.go 的资源族目录。"""
    found: list[Path] = []
    for path in go_root.rglob("client.go"):
        if any(part in GO_SKIP_DIRS for part in path.parts):
            continue
        found.append(path.parent)
    return sorted(found)


SHARED_TYPE_FILES = {
    "v1": "v1/types.go",
    "core": "refer.go",
}


def scan_shared_types(go_root: Path) -> dict[str, dict[str, Any]]:
    """扫描两代共享与根包的类型。

    v1 包承载新一代跨族共用的类型，根包承载两代共用的 Refer 与 MetaData。
    """
    result: dict[str, dict[str, Any]] = {}
    for pkg, relative in SHARED_TYPE_FILES.items():
        path = go_root / relative
        if not path.exists():
            continue
        types, _ = scan_go(path.read_text(encoding="utf-8"))
        result[pkg] = types
    return result


def relative_package(go_root: Path, package: Path) -> str:
    rel = package.relative_to(go_root).as_posix()
    return "." if rel == "." else rel


def build_contract(go_root: Path) -> dict[str, Any]:
    """抽取完整契约。"""
    families = parse_families(go_root)
    suffix = parse_params_suffix(go_root)

    endpoints: list[dict[str, Any]] = []
    types_by_package: dict[str, dict[str, Any]] = scan_shared_types(go_root)

    for package in discover_packages(go_root):
        pkg_name = relative_package(go_root, package)
        types_file = package / "types.go"
        client_file = package / "client.go"

        types: dict[str, dict[str, Any]] = {}
        consts: dict[str, dict[str, Any]] = {}
        if types_file.exists():
            types, consts = scan_go(types_file.read_text(encoding="utf-8"))
        types_by_package[pkg_name] = types

        endpoint_consts = {
            name: info for name, info in consts.items() if ENDPOINT_CONST_RE.match(info["expr"])
        }
        ttl_consts = {
            name: info for name, info in consts.items() if "TTL" in name and "time." in info["expr"]
        }

        client_text = client_file.read_text(encoding="utf-8")
        helpers = extract_cache_helpers(client_text)
        functions = extract_functions(client_text)
        methods = parse_methods(client_text, functions)

        records: dict[str, dict[str, Any]] = {}

        for method in methods:
            request = method["request"]
            endpoint_const = request.get("endpoint", "")
            endpoint_info = endpoint_consts.get(endpoint_const)
            if endpoint_info is None:
                continue

            endpoint_value = ENDPOINT_CONST_RE.match(endpoint_info["expr"]).group(1)
            ttl_expr = ttl_consts.get(request.get("ttl", ""), {}).get("expr", "")
            ttl_seconds = parse_duration_seconds(ttl_expr)
            rendered = render_cache_key(request.get("cache_key", ""), helpers, families, suffix)
            cache_key = rendered[0] if rendered else ""
            cache_prefix = rendered[1] if rendered else ""

            records[method["name"]] = {
                "package": pkg_name,
                "method": method["name"],
                "py_method": snake_case(method["name"]),
                "endpoint": endpoint_value,
                "endpoint_constant": f"{pkg_name}.{endpoint_const}",
                "upstream_path": render_path(request.get("path", "")),
                "default_ttl": format_ttl(ttl_seconds) if ttl_seconds else "",
                "default_ttl_seconds": ttl_seconds,
                "cache_key_template": cache_key,
                "cache_prefix": cache_prefix,
                "query_params": method["query"],
                "params": method["params"],
                "returns": method["returns"],
                "response_type": response_type(method["returns"]),
                "limits": parse_limits(method["guards"], consts),
                "validations": method["validations"],
                "delegates_to": "",
                "doc": method["doc"],
            }

        for method in methods:
            if method["name"] in records:
                continue
            target = records.get(method.get("delegates_to", ""))
            if target is None:
                continue
            record = dict(target)
            record.update(
                {
                    "method": method["name"],
                    "py_method": snake_case(method["name"]),
                    "params": method["params"],
                    "returns": method["returns"],
                    "response_type": response_type(method["returns"]),
                    "delegates_to": method["delegates_to"],
                    "doc": method["doc"],
                }
            )
            records[method["name"]] = record

        endpoints.extend(records[m["name"]] for m in methods if m["name"] in records)

    return {
        "families": families,
        "params_suffix": suffix,
        "endpoints": endpoints,
        "types": types_by_package,
    }


def cross_check(go_root: Path, endpoints: list[dict[str, Any]]) -> list[str]:
    """与 Go 仓库的端点表对账。"""
    table = parse_go_endpoints_doc(go_root)
    problems: list[str] = []
    seen = set()

    for endpoint in endpoints:
        key = f"{endpoint['package']}.{endpoint['method']}"
        seen.add(key)
        expected = table.get(key)
        if expected is None:
            problems.append(f"{key}: Go 端点表里没有这个方法")
            continue
        if expected["upstream_path"] != endpoint["upstream_path"]:
            problems.append(
                f"{key}: 上游路径不一致 表={expected['upstream_path']} "
                f"源码={endpoint['upstream_path']}"
            )
        if expected["default_ttl"] != endpoint["default_ttl"]:
            problems.append(
                f"{key}: 默认 TTL 不一致 表={expected['default_ttl']} "
                f"源码={endpoint['default_ttl']}"
            )
        if expected["cache_prefix"] != endpoint["cache_prefix"]:
            problems.append(
                f"{key}: 缓存键前缀不一致 表={expected['cache_prefix']} "
                f"源码={endpoint['cache_prefix']}"
            )

    for key in table:
        if key not in seen:
            problems.append(f"{key}: 端点表里有、源码里没抽到")

    return problems


# --------------------------------------------------------------------------
# 字段映射
# --------------------------------------------------------------------------

SIMPLE_PY_TYPES = {
    "string": "str",
    "float64": "float",
    "float32": "float",
    "int": "int",
    "int64": "int",
    "bool": "bool",
    "any": "Any",
    "interface{}": "Any",
    "json.Number": "int | float | str",
}


def map_py_type(go_type: str) -> tuple[str, bool]:
    """Go 类型映射成 Python 类型注解，并返回是否可选。"""
    text = go_type.strip()
    optional = False
    if text.startswith("*"):
        optional = True
        text = text[1:]
    if text.startswith("[]"):
        inner, _ = map_py_type(text[2:])
        return f"list[{inner}]", optional
    if text.startswith("map["):
        return "dict[str, Any]", optional
    if text in SIMPLE_PY_TYPES:
        return SIMPLE_PY_TYPES[text], optional
    return text.split(".")[-1], optional


def build_field_map(contract: dict[str, Any]) -> dict[str, Any]:
    """生成 Go↔Python 字段映射清单。"""
    result: dict[str, Any] = {}
    explicit_aliases: list[dict[str, str]] = []

    for pkg, types in contract["types"].items():
        for type_name, info in types.items():
            if info["kind"] != "struct" or not info["fields"]:
                continue
            rows = []
            for field in info["fields"]:
                if field.get("unparsed"):
                    rows.append(
                        {
                            "go_name": "",
                            "json_name": None,
                            "go_type": field["go_type"],
                            "optional": False,
                            "py_name": "",
                            "py_type": "需人工确认",
                            "alias": "",
                            "alias_mode": "未解析",
                            "doc": field["doc"],
                        }
                    )
                    continue

                py_name = snake_case(field["go_name"])
                py_type, optional = map_py_type(field["go_type"])
                json_name = field["json_name"]
                auto = to_camel(py_name)
                if json_name is None:
                    alias_mode = "无 tag"
                    alias = ""
                elif auto == json_name:
                    alias_mode = "自动"
                    alias = json_name
                else:
                    alias_mode = "显式"
                    alias = json_name
                    explicit_aliases.append(
                        {
                            "package": pkg,
                            "type": type_name,
                            "go_field": field["go_name"],
                            "json_name": json_name,
                            "py_name": py_name,
                            "reason": f"to_camel({py_name}) = {auto}",
                        }
                    )

                rows.append(
                    {
                        "go_name": field["go_name"],
                        "json_name": json_name,
                        "go_type": field["go_type"],
                        "optional": optional,
                        "py_name": py_name,
                        "py_type": py_type,
                        "alias": alias,
                        "alias_mode": alias_mode,
                        "doc": field["doc"],
                    }
                )
            result[f"{pkg}.{type_name}"] = {
                "package": pkg,
                "name": type_name,
                "doc": info["doc"],
                "fields": rows,
            }

    return {"types": result, "explicit_aliases": explicit_aliases}


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------

BACKTICK = chr(96)


def code(text: str) -> str:
    """给文本裹上反引号。"""
    return BACKTICK + text + BACKTICK


def render_endpoints_markdown(contract: dict[str, Any]) -> str:
    """生成 docs/contract_baseline.md。"""
    endpoints = contract["endpoints"]
    lines: list[str] = []
    lines.append("# 端点契约基线")
    lines.append("")
    lines.append(
        "由 `tools/extract_go_contract.py` 从 Go 源码抽取，"
        "与 Go 仓库的 `docs/endpoints.md` 逐项对账通过。"
        "改 Go 源码后重跑抽取器更新本文。"
    )
    lines.append("")
    lines.append(f"端点总数：**{len(endpoints)}**。")
    lines.append("")

    lines.append("## 端点表")
    lines.append("")
    lines.append("| 包 | 方法 | 端点常量 | 端点值 | 上游路径 | 位置形态 | 默认 TTL | 缓存键前缀 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for endpoint in endpoints:
        lines.append(
            "| {pkg} | {method} | {const} | {value} | {path} | {shape} | {ttl} | {prefix} |".format(
                pkg=code(endpoint["package"]),
                method=code(endpoint["method"]),
                const=code(endpoint["endpoint_constant"]),
                value=code(endpoint["endpoint"]),
                path=code(endpoint["upstream_path"]),
                shape=endpoint["location_shape"],
                ttl=endpoint["default_ttl"],
                prefix=code(endpoint["cache_prefix"]),
            )
        )
    lines.append("")

    lines.append("## 缓存键模板")
    lines.append("")
    lines.append("模板里的花括号是占位符。参数后缀只在该参数有值时出现。")
    lines.append("")
    lines.append("| 包.方法 | 模板 |")
    lines.append("| --- | --- |")
    for endpoint in endpoints:
        lines.append(
            f"| {endpoint['package']}.{endpoint['method']} | "
            f"{code(endpoint['cache_key_template'])} |"
        )
    lines.append("")

    lines.append("## 查询参数")
    lines.append("")
    lines.append("| 包.方法 | 参数 | 取值来源 |")
    lines.append("| --- | --- | --- |")
    for endpoint in endpoints:
        if not endpoint["query_params"]:
            lines.append(f"| {endpoint['package']}.{endpoint['method']} | 无 | 无 |")
            continue
        for param in endpoint["query_params"]:
            lines.append(
                f"| {endpoint['package']}.{endpoint['method']} | "
                f"{code(param['name'])} | {code(param['expr'])} |"
            )
    lines.append("")

    lines.append("## 参数约束")
    lines.append("")
    lines.append("客户端先校验，越界返回 `InvalidParameterError`，不打上游。")
    lines.append("")
    lines.append("| 包.方法 | 参数 | 约束 |")
    lines.append("| --- | --- | --- |")
    has_limits = False
    for endpoint in endpoints:
        for name, bound in endpoint["limits"].items():
            has_limits = True
            lines.append(
                f"| {endpoint['package']}.{endpoint['method']} | {code(name)} | "
                f"{describe_limit(bound)} |"
            )
    if not has_limits:
        lines.append("| 无 | 无 | 无 |")
    lines.append("")

    lines.append("## 客户端校验点")
    lines.append("")
    lines.append("| 包.方法 | 校验 |")
    lines.append("| --- | --- |")
    has_validation = False
    for endpoint in endpoints:
        for validation in endpoint["validations"]:
            has_validation = True
            lines.append(f"| {endpoint['package']}.{endpoint['method']} | {code(validation)} |")
    if not has_validation:
        lines.append("| 无 | 无 |")
    lines.append("")

    lines.append("## 参数后缀模板")
    lines.append("")
    lines.append("由 `internal/cachekey/params.go` 的 `Params.suffix()` 还原，顺序即字节顺序。")
    lines.append("")
    lines.append(code(contract["params_suffix"]))
    lines.append("")

    lines.append("## 缓存键族前缀")
    lines.append("")
    lines.append("前缀与包名不必对齐。`qwx:tide:` 不是 `qwx:ocean:`，这是已发布键字面量的约定。")
    lines.append("")
    lines.append("| 族 | 前缀 |")
    lines.append("| --- | --- |")
    for family, prefix in contract["families"].items():
        lines.append(f"| {code(family)} | {code(prefix)} |")
    lines.append("")

    return "\n".join(lines)


def render_field_map_markdown(field_map: dict[str, Any]) -> str:
    """生成 docs/field_map.md。"""
    lines: list[str] = []
    lines.append("# Go↔Python 字段映射清单")
    lines.append("")
    lines.append(
        "由 `tools/extract_go_contract.py` 从 Go 的 struct 定义抽取。"
        "Python 侧按本清单落模型：Go 字段名决定 Python 字段名，json tag 决定别名。"
    )
    lines.append("")
    lines.append(
        "别名策略分三档：**自动** 由 `to_camel(Python 字段名)` 得到；"
        "**显式** 需要写 `Field(alias=...)`；**无 tag** 表示上游没有这个键。"
    )
    lines.append("")

    explicit = field_map["explicit_aliases"]
    lines.append("## 需要显式 alias 的字段")
    lines.append("")
    lines.append(f"共 {len(explicit)} 个。Python 侧漏写 alias 就会解析不到值。")
    lines.append("")
    lines.append("| 包 | 类型 | Go 字段 | json tag | Python 字段 | 原因 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for item in explicit:
        lines.append(
            "| {pkg} | {typ} | {go} | {json} | {py} | {reason} |".format(
                pkg=item["package"],
                typ=item["type"],
                go=code(item["go_field"]),
                json=code(item["json_name"]),
                py=code(item["py_name"]),
                reason=item["reason"],
            )
        )
    lines.append("")

    by_package: dict[str, list[dict[str, Any]]] = {}
    for info in field_map["types"].values():
        by_package.setdefault(info["package"], []).append(info)

    lines.append("## 类型清单")
    lines.append("")
    for pkg in sorted(by_package):
        lines.append(f"### {code(pkg)}")
        lines.append("")
        for info in sorted(by_package[pkg], key=lambda x: x["name"]):
            lines.append(f"#### {info['name']}")
            lines.append("")
            if info["doc"]:
                lines.append(f"> {info['doc']}")
                lines.append("")
            lines.append(
                "| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |"
            )
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for field in info["fields"]:
                alias = field["alias"]
                mode = field["alias_mode"]
                if mode == "自动":
                    alias_cell = "自动"
                elif mode == "显式":
                    alias_cell = f"显式 {code(alias)}"
                else:
                    alias_cell = mode
                lines.append(
                    "| {go} | {json} | {gotype} | {opt} | {py} | {pytype} | {mode} "
                    "| {doc} |".format(
                        go=code(field["go_name"]),
                        json=code(field["json_name"] or ""),
                        gotype=code(field["go_type"]),
                        opt="是" if field["optional"] else "",
                        py=code(field["py_name"]),
                        pytype=code(field["py_type"]),
                        mode=alias_cell,
                        doc=field["doc"].replace("|", "\\|"),
                    )
                )
            lines.append("")

    return "\n".join(lines)


def write_or_check(path: Path, content: str, check: bool) -> list[str]:
    """写入文件；check 模式下只比对。"""
    if check:
        if not path.exists():
            return [f"{path}: 文件不存在"]
        current = path.read_text(encoding="utf-8")
        if current != content:
            return [f"{path}: 与抽取结果不一致，重新生成"]
        return []

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="抽取 qwx 契约基线")
    parser.add_argument("--go-root", default="../qwx", help="Go 仓库路径")
    parser.add_argument("--out", default="contract", help="JSON 输出目录")
    parser.add_argument("--docs", default="docs", help="Markdown 输出目录")
    parser.add_argument("--check", action="store_true", help="只校验漂移，不写文件")
    args = parser.parse_args(argv)

    go_root = Path(args.go_root).resolve()
    if not (go_root / "internal" / "cachekey" / "cachekey.go").exists():
        print(f"extract: {go_root} 不是 qwx 的 Go 仓库", file=sys.stderr)
        return 2

    contract = build_contract(go_root)

    problems = cross_check(go_root, contract["endpoints"])
    if problems:
        print("extract: 与 Go 端点表对账失败", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2

    go_table = parse_go_endpoints_doc(go_root)
    for endpoint in contract["endpoints"]:
        key = f"{endpoint['package']}.{endpoint['method']}"
        endpoint["location_shape"] = go_table[key]["location_shape"]
        endpoint["py_package"] = "qwx." + endpoint["package"].replace("/", ".")

    field_map = build_field_map(contract)

    out_dir = Path(args.out)
    docs_dir = Path(args.docs)

    endpoints_json = (
        json.dumps(
            {
                "source": "https://github.com/KanoCifer/qwx",
                "families": contract["families"],
                "params_suffix": contract["params_suffix"],
                "params_placeholders": PY_PARAM_NAMES,
                "endpoints": contract["endpoints"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    types_json = (
        json.dumps(
            {
                "source": "https://github.com/KanoCifer/qwx",
                "explicit_aliases": field_map["explicit_aliases"],
                "types": field_map["types"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    drift: list[str] = []
    drift += write_or_check(out_dir / "endpoints.json", endpoints_json, args.check)
    drift += write_or_check(out_dir / "types.json", types_json, args.check)
    drift += write_or_check(
        docs_dir / "contract_baseline.md",
        render_endpoints_markdown(contract),
        args.check,
    )
    drift += write_or_check(
        docs_dir / "field_map.md",
        render_field_map_markdown(field_map),
        args.check,
    )

    if drift:
        print("extract: 契约基线漂移", file=sys.stderr)
        for item in drift:
            print(f"  - {item}", file=sys.stderr)
        return 1

    action = "校验" if args.check else "生成"
    print(
        f"extract: {action}完成 端点 {len(contract['endpoints'])} 个 "
        f"类型 {len(field_map['types'])} 个 "
        f"显式 alias {len(field_map['explicit_aliases'])} 处"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
