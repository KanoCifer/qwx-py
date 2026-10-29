"""端点族服务客户端的公共骨架。

同步与异步共用同一套端点方法体：方法只负责算出请求参数，发送交给
Client.do 或 AsyncClient.do。同步客户端拿到的是模型，异步客户端拿到的是
协程，调用方 await 即可。
"""

from __future__ import annotations

from typing import Any

from qwx.request import Request

__all__ = ["Service"]


class Service:
    """端点族服务客户端的骨架。

    base 是 Client 或 AsyncClient。类型标成 Any 是有意的：同步实现返回
    模型，异步实现返回协程，两者的返回类型不同，静态检查无法统一。
    """

    def __init__(self, base: Any) -> None:
        self._base = base

    def _call(self, request: Request) -> Any:
        """发一次请求。

        同步客户端返回解析好的模型，异步客户端返回协程。
        """
        return self._base.do(request)
