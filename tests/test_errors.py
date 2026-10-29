"""错误解析与归类。"""

from __future__ import annotations

import pytest

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
    upstream_error,
)


def test_all_errors_share_a_base() -> None:
    for cls in (
        InvalidConfigError,
        InvalidLocationError,
        InvalidParameterError,
        InvalidResponseError,
        UpstreamError,
        UpstreamRejectedError,
        QuotaExceededError,
        UnauthorizedError,
        UpstreamUnavailableError,
    ):
        assert issubclass(cls, QwxError)


@pytest.mark.parametrize(
    ("status", "want"),
    [
        (400, UpstreamRejectedError),
        (404, UpstreamRejectedError),
        (401, UnauthorizedError),
        (403, UnauthorizedError),
        (429, QuotaExceededError),
        (500, UpstreamUnavailableError),
        (503, UpstreamUnavailableError),
    ],
)
def test_upstream_error_is_classified_by_status(status: int, want: type[UpstreamError]) -> None:
    error = upstream_error(status, b"{}")
    assert isinstance(error, want)
    assert error.status_code == status


def test_new_generation_error_body_is_parsed() -> None:
    body = b'{"error":{"status":400,"title":"Invalid Parameters","invalidParams":["location"]}}'
    error = upstream_error(400, body)
    assert error.title == "Invalid Parameters"
    assert error.invalid_params == ["location"]
    assert error.body == body.decode()


def test_legacy_error_body_is_parsed() -> None:
    body = b'{"code":"400","error":"Invalid Parameters"}'
    error = upstream_error(400, body)
    assert error.code == "400"
    assert error.title == "Invalid Parameters"


def test_error_body_is_truncated_to_two_kilobytes() -> None:
    body = b"x" * 4096
    error = upstream_error(500, body)
    assert error.body.endswith("...(truncated)")
    assert len(error.body) == 2048 + len("...(truncated)")


def test_non_json_body_keeps_status_only() -> None:
    error = upstream_error(502, b"not json")
    assert error.status_code == 502
    assert error.title == ""
    assert error.body == "not json"


def test_error_message_contains_status_and_invalid_params() -> None:
    body = (
        b'{"error":{"status":400,"title":"Invalid Parameters",'
        b'"invalidParams":["longitude","latitude"]}}'
    )
    error = upstream_error(400, body)
    text = str(error)
    assert "status 400" in text
    assert "Invalid Parameters" in text
    assert "longitude, latitude" in text
