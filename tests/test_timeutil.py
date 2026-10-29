"""上游时间字符串解析。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qwx.timeutil import parse_qtime


def test_parse_utc_with_z() -> None:
    assert parse_qtime("2026-10-21T05:00Z") == datetime(2026, 10, 21, 5, 0, tzinfo=timezone.utc)


def test_parse_offset_time() -> None:
    parsed = parse_qtime("2026-10-21T13:00+08:00")
    assert parsed is not None
    assert parsed.utcoffset() == timedelta(hours=8)


def test_parse_compact_offset() -> None:
    parsed = parse_qtime("2026-10-21T13:00+0800")
    assert parsed is not None
    assert parsed.utcoffset() == timedelta(hours=8)


def test_parse_minutes_and_seconds() -> None:
    assert parse_qtime("2026-10-21T05:00") == datetime(2026, 10, 21, 5, 0)
    assert parse_qtime("2026-10-21T05:00:30") == datetime(2026, 10, 21, 5, 0, 30)


def test_parse_date_only() -> None:
    assert parse_qtime("2026-10-21") == datetime(2026, 10, 21)


def test_parse_failure_returns_none() -> None:
    assert parse_qtime("") is None
    assert parse_qtime(None) is None
    assert parse_qtime("not a time") is None
