"""qwx —— 和风天气（QWeather）开发服务的 Python 客户端。

Python 版与 Go 版（https://github.com/KanoCifer/qwx）语义对等：端点集合、
缓存键字节、端点常量值、错误分类与 TTL 优先级完全一致。

最小用法：

    import qwx
    from qwx.v1.weather import WeatherService

    auth = qwx.APIKeyAuth("你的 API KEY")
    with qwx.Client(auth, "abcxyz.qweatherapi.com") as client:
        weather = WeatherService(client)
        print(weather.current(qwx.Location(lat=39.92, lon=116.41)))
"""

from __future__ import annotations

from qwx._models import QwxModel
from qwx.auth import APIKeyAuth, Auth, JWTAuth
from qwx.cache import Cache, MemoryCache
from qwx.client import AsyncClient, Client
from qwx.errors import (
    InvalidConfigError,
    InvalidLocationError,
    InvalidParameterError,
    InvalidResponseError,
    QuotaExceededError,
    QwxError,
    UnauthorizedError,
    UpstreamError,
    UpstreamRejectedError,
    UpstreamUnavailableError,
)
from qwx.lang import LANGS, Lang, lookup_lang
from qwx.location import Location, parse_location
from qwx.logger import Logger
from qwx.refer import MetaData, Refer
from qwx.request import AsyncDoer, Doer, Request
from qwx.timeutil import parse_qtime
from qwx.ttl import Endpoint, TTLMap, TTLPolicy, TTLPolicyFunc, current_ttl_override, override_ttl

__version__ = "0.1.0.dev0"

__all__ = [
    "LANGS",
    "APIKeyAuth",
    "AsyncClient",
    "AsyncDoer",
    "Auth",
    "Cache",
    "Client",
    "Doer",
    "Endpoint",
    "InvalidConfigError",
    "InvalidLocationError",
    "InvalidParameterError",
    "InvalidResponseError",
    "JWTAuth",
    "Lang",
    "Location",
    "Logger",
    "MemoryCache",
    "MetaData",
    "QuotaExceededError",
    "QwxError",
    "QwxModel",
    "Refer",
    "Request",
    "TTLMap",
    "TTLPolicy",
    "TTLPolicyFunc",
    "UnauthorizedError",
    "UpstreamError",
    "UpstreamRejectedError",
    "UpstreamUnavailableError",
    "__version__",
    "current_ttl_override",
    "lookup_lang",
    "override_ttl",
    "parse_location",
    "parse_qtime",
]
