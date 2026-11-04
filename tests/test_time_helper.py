import pytest

from app.core.utils import TimeHelper


def test_parses_minutes():
    assert TimeHelper.parse_duration("15m") == 900


def test_parses_days():
    assert TimeHelper.parse_duration("30d") == 30 * 86400


def test_parses_seconds_and_hours():
    assert TimeHelper.parse_duration("45s") == 45
    assert TimeHelper.parse_duration("2h") == 7200


def test_rejects_bad_format():
    with pytest.raises(ValueError):
        TimeHelper.parse_duration("15")
    with pytest.raises(ValueError):
        TimeHelper.parse_duration("15x")


def test_to_iso_z_keeps_seconds_when_there_are_no_microseconds():
    from datetime import UTC, datetime

    assert TimeHelper.to_iso_z(datetime(2026, 1, 1, 12, 30, 45, tzinfo=UTC)) == "2026-01-01T12:30:45.000Z"


def test_to_iso_z_converts_to_utc_and_treats_naive_as_utc():
    from datetime import datetime, timedelta, timezone

    msk = timezone(timedelta(hours=3))
    assert TimeHelper.to_iso_z(datetime(2026, 1, 1, 15, 0, 0, 123456, tzinfo=msk)) == "2026-01-01T12:00:00.123Z"
    assert TimeHelper.to_iso_z(datetime(2026, 1, 1, 12, 0, 0)) == "2026-01-01T12:00:00.000Z"


def test_now_iso_z_is_second_precision_utc():
    value = TimeHelper.now_iso_z()
    assert value.endswith("Z")
    assert len(value) == len("2026-01-01T12:00:00Z")
