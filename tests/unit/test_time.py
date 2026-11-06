from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.shared.domain.time import FrozenTime, TimeService


def test_utc_normalisation_and_format() -> None:
    moscow = timezone(timedelta(hours=3))
    assert TimeService.as_utc(datetime(2026, 1, 2, 6, 0, tzinfo=moscow)) == datetime(2026, 1, 2, 3, 0, tzinfo=UTC)
    assert TimeService.as_utc(datetime(2026, 1, 2, 3, 0)).tzinfo is UTC  # naive is taken as UTC
    moment = datetime(2026, 1, 2, 3, 4, 5, 678_900, tzinfo=UTC)
    assert TimeService.to_iso(moment) == "2026-01-02T03:04:05.678Z"
    assert TimeService.to_iso(moment, timespec="seconds") == "2026-01-02T03:04:05Z"
    assert TimeService.from_timestamp(0) == datetime(1970, 1, 1, tzinfo=UTC)


def test_durations() -> None:
    assert TimeService.parse_duration("15m") == timedelta(minutes=15)
    assert TimeService.parse_duration(" 30d ") == timedelta(days=30)
    with pytest.raises(ValueError, match="duration"):
        TimeService.parse_duration("15 minutes")


def test_frozen_time() -> None:
    time = FrozenTime(datetime(2026, 11, 7, 12, 0, tzinfo=UTC))
    deadline = time.after(timedelta(hours=1))
    assert not time.is_past(deadline)
    time.advance(timedelta(hours=1))
    assert time.is_past(deadline)  # expires exactly at the deadline
    assert time.now() == deadline
