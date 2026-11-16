"""请求结构：HTTP 方法的约定只有一处。"""

from __future__ import annotations

from qwx.request import METHOD_GET, Request


def test_default_method_is_get() -> None:
    """留空的方法按 GET 处理。"""
    assert Request().method == METHOD_GET
    assert Request().http_method() == "GET"


def test_http_method_falls_back_to_get() -> None:
    """空串也按 GET 处理 —— 约定不在调用方重复。"""
    assert Request(method="").http_method() == "GET"


def test_http_method_keeps_explicit_method() -> None:
    """显式给的方法原样保留。"""
    assert Request(method="POST").http_method() == "POST"
