from datetime import UTC, datetime

from app.integrations.gitlab_client import _parse_dt


def test_parse_dt_iso_with_offset():
    parsed = _parse_dt("2026-01-15T10:00:00.000+00:00")
    assert parsed == datetime(2026, 1, 15, 10, 0, tzinfo=UTC)


def test_parse_dt_z_suffix():
    parsed = _parse_dt("2026-01-15T10:00:00Z")
    assert parsed is not None
    assert parsed.tzinfo is not None


def test_parse_dt_invalid_or_empty():
    assert _parse_dt(None) is None
    assert _parse_dt("") is None
    assert _parse_dt("not-a-date") is None
