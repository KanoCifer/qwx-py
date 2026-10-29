"""两种认证方式。"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

from qwx.auth import APIKeyAuth, JWTAuth
from qwx.errors import InvalidConfigError


def make_pem() -> tuple[str, Ed25519PrivateKey]:
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return pem, key


def decode_segment(segment: str) -> dict[str, object]:
    padding = "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(segment + padding))


def test_api_key_auth_sets_header() -> None:
    headers: dict[str, str] = {}
    APIKeyAuth("secret").apply(headers)
    assert headers == {"X-QW-Api-Key": "secret"}


def test_api_key_auth_rejects_empty_key() -> None:
    with pytest.raises(InvalidConfigError):
        APIKeyAuth("")


def test_jwt_auth_sets_bearer_header() -> None:
    pem, _ = make_pem()
    headers: dict[str, str] = {}
    JWTAuth(
        private_key_pem=pem,
        key_id="kid",
        project_id="proj",
        developer_id="devid",
    ).apply(headers)
    assert headers["Authorization"].startswith("Bearer ")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"private_key_pem": "", "key_id": "kid", "project_id": "proj", "developer_id": "dev"},
        {"private_key_pem": "x", "key_id": "", "project_id": "proj", "developer_id": "dev"},
        {"private_key_pem": "x", "key_id": "kid", "project_id": "", "developer_id": "dev"},
        {"private_key_pem": "x", "key_id": "kid", "project_id": "proj", "developer_id": ""},
    ],
)
def test_jwt_auth_requires_every_credential(kwargs: dict[str, str]) -> None:
    with pytest.raises(InvalidConfigError):
        JWTAuth(**kwargs)


def test_jwt_auth_rejects_broken_pem() -> None:
    with pytest.raises(InvalidConfigError):
        JWTAuth(
            private_key_pem="not a pem",
            key_id="kid",
            project_id="proj",
            developer_id="dev",
        )


def test_jwt_auth_rejects_non_ed25519_key() -> None:
    rsa = generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    with pytest.raises(InvalidConfigError):
        JWTAuth(
            private_key_pem=pem,
            key_id="kid",
            project_id="proj",
            developer_id="dev",
        )


def test_jwt_signature_verifies_against_the_public_key() -> None:
    pem, key = make_pem()
    auth = JWTAuth(
        private_key_pem=pem,
        key_id="kid",
        project_id="proj",
        developer_id="dev",
        clock=lambda: datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )
    token = auth.token()
    header_b64, payload_b64, signature_b64 = token.split(".")

    header = decode_segment(header_b64)
    assert header == {"alg": "EdDSA", "kid": "kid"}

    payload = decode_segment(payload_b64)
    assert payload["iss"] == "dev"
    assert payload["sub"] == "proj"
    # iat 回退 30 秒容忍时钟偏差，exp = iat + 15 分钟。
    assert payload["iat"] == 1767323045 - 30
    assert payload["exp"] == 1767323045 - 30 + 15 * 60

    signature = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
    public = key.public_key()
    public.verify(signature, f"{header_b64}.{payload_b64}".encode())


def test_jwt_token_is_reused_until_it_is_close_to_expiry() -> None:
    pem, _ = make_pem()
    now = [datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)]
    auth = JWTAuth(
        private_key_pem=pem,
        key_id="kid",
        project_id="proj",
        developer_id="dev",
        clock=lambda: now[0],
    )
    first = auth.token()
    assert auth.token() == first

    # 过期前 1 分钟换新，留出请求在途的余量。
    now[0] = now[0] + timedelta(minutes=14, seconds=30)
    assert auth.token() != first


def test_jwt_auth_accepts_escaped_newlines() -> None:
    pem, _ = make_pem()
    escaped = pem.replace(chr(10), chr(92) + "n")
    auth = JWTAuth(
        private_key_pem=escaped,
        key_id="kid",
        project_id="proj",
        developer_id="dev",
    )
    assert auth.token().count(".") == 2
