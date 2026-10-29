"""日志文本清洗。"""

from __future__ import annotations

from qwx.logger import Logger, sanitize_error_text


def test_query_string_is_stripped_from_error_text() -> None:
    # GeoAPI 的 location=地名 这类用户输入不该跟着漏进日志。
    text = sanitize_error_text(
        Exception("failed https://host/geo/v2/city/lookup?location=北京&n=5")
    )
    assert "location" not in text
    assert "/geo/v2/city/lookup" in text


def test_plain_error_text_is_untouched() -> None:
    assert sanitize_error_text(Exception("boom")) == "boom"
    assert sanitize_error_text(None) == ""


def test_default_logger_is_silent() -> None:
    logger = Logger()
    assert logger.logger.name == "qwx"
    logger.log(40, "should not appear")
