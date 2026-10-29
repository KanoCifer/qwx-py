"""和风天气的两种认证方式。

官方支持 JWT 与 API KEY 两种，但不能同时使用（同时使用会导致认证失败）。
"""

from __future__ import annotations

import base64
import json
import threading
from collections.abc import Callable, Mapping, MutableMapping
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from qwx.errors import InvalidConfigError

__all__ = ["DEFAULT_TOKEN_TTL", "APIKeyAuth", "Auth", "JWTAuth"]

DEFAULT_TOKEN_TTL = timedelta(minutes=15)
"""token 的默认有效期（官方口径 15 分钟）。"""

_CLOCK_SKEW = timedelta(seconds=30)
"""iat 回退的秒数，容忍时钟偏差（官方口径 30 秒）。"""


@runtime_checkable
class Auth(Protocol):
    """认证方式。"""

    def apply(self, headers: MutableMapping[str, str]) -> None:
        """把认证信息写入请求头。"""
        ...


def _b64url(data: bytes) -> str:
    """JWT 用的 base64url 编码（无 padding）。"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _compact_json(payload: Mapping[str, object]) -> bytes:
    """紧凑 JSON：键排序、无空白，与 Go 版 json.Marshal 的输出一致。"""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_private_key(pem_text: str) -> Ed25519PrivateKey:
    """解析 PKCS#8 编码的 Ed25519 私钥。"""
    # 环境变量里的私钥常写成一行，用字面量的反斜杠加 n 表示换行。
    text = pem_text.replace(chr(92) + "n", chr(10))
    try:
        key = serialization.load_pem_private_key(text.encode("utf-8"), password=None)
    except Exception as exc:
        raise InvalidConfigError(f"qwx: parse PKCS#8 private key: {exc}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise InvalidConfigError("qwx: private key is not Ed25519")
    return key


class JWTAuth:
    """用 Ed25519 私钥签发和风天气要求的 EdDSA JWT。

    官方推荐 JWT 作为首选认证方式。token 有效期 15 分钟，本实现在过期前
    自动重新签发，调用方无需关心。
    """

    def __init__(
        self,
        *,
        private_key_pem: str,
        key_id: str,
        project_id: str,
        developer_id: str,
        token_ttl: timedelta = DEFAULT_TOKEN_TTL,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """构造 JWTAuth。

        私钥、Key ID、Project ID、Developer ID 四项都必填，缺任一项抛
        InvalidConfigError。Developer ID 对应 payload 的 iss，官方口径下
        上游按它校验凭据归属，缺失会导致 401。

        private_key_pem 接受 PKCS#8 格式的 PEM，也接受含字面量换行转义的
        字符串（环境变量常见写法）。生成方式：

            openssl genpkey -algorithm ED25519 -out ed25519-private.pem
        """
        if not private_key_pem:
            raise InvalidConfigError("qwx: empty private key")
        if not key_id:
            raise InvalidConfigError("qwx: empty key ID")
        if not project_id:
            raise InvalidConfigError("qwx: empty project ID")
        if not developer_id:
            raise InvalidConfigError("qwx: empty developer ID")

        self._key = _load_private_key(private_key_pem)
        self._key_id = key_id
        self._project_id = project_id
        self._developer_id = developer_id
        self._token_ttl = token_ttl if token_ttl > timedelta(0) else DEFAULT_TOKEN_TTL
        self._clock = clock if clock is not None else (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._token = ""
        self._token_till = datetime.min.replace(tzinfo=timezone.utc)

    def token(self) -> str:
        """返回当前的 JWT，必要时重新签发。

        token 在过期前 1 分钟失效并重新签发，避免请求发出时刚好过期。
        """
        with self._lock:
            now = self._clock()
            if self._token and now < self._token_till:
                return self._token
            token = self._sign(now)
            self._token = token
            # 提前 1 分钟换新，留出请求在途的余量。
            self._token_till = now + (self._token_ttl - timedelta(minutes=1))
            return token

    def apply(self, headers: MutableMapping[str, str]) -> None:
        """把 Bearer token 写入请求头。"""
        headers["Authorization"] = "Bearer " + self.token()

    def _sign(self, now: datetime) -> str:
        """生成一个 EdDSA JWT。

        payload 字段与官方口径一致：iss 是签发者（Developer ID），sub 是
        凭据的项目 ID，iat 回退 30 秒容忍时钟偏差，exp = iat + tokenTTL。
        """
        issued = now - _CLOCK_SKEW
        expires = issued + self._token_ttl
        header = {"alg": "EdDSA", "kid": self._key_id}
        payload: dict[str, object] = {
            "iat": int(issued.timestamp()),
            "exp": int(expires.timestamp()),
            "sub": self._project_id,
            "iss": self._developer_id,
        }
        signing_input = _b64url(_compact_json(header)) + "." + _b64url(_compact_json(payload))
        signature = self._key.sign(signing_input.encode("ascii"))
        return signing_input + "." + _b64url(signature)


class APIKeyAuth:
    """用 API KEY 认证。

    官方已公告：从 2027 年 1 月 1 日起限制用 API KEY 认证的每日请求量，
    且 SDK 5+ 不再支持 API KEY。新项目建议改用 JWTAuth。
    """

    def __init__(self, key: str) -> None:
        """构造 APIKeyAuth。key 为空时抛 InvalidConfigError。"""
        if not key:
            raise InvalidConfigError("qwx: empty API key")
        self._key = key

    def apply(self, headers: MutableMapping[str, str]) -> None:
        """把 API KEY 写入请求头。"""
        headers["X-QW-Api-Key"] = self._key
