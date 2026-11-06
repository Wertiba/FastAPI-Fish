"""Everything about time in one place: the current moment, UTC normalisation, formatting, durations.

The app keeps every datetime aware and in UTC. ``TimeService`` is a DI dependency (``Scope.APP``), so
a test of "in a month" provides ``FrozenTime`` and moves it with ``advance`` instead of waiting.
Code that decides something by time (expiry, schedules, tokens) takes ``TimeService``; dataclass
defaults (``created_at``) use ``utc_now``, which has no instance to receive.
"""

import re
from datetime import UTC, datetime, timedelta

_DURATION = re.compile(r"^(\d+)([smhd])$")
_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


def utc_now() -> datetime:
    """The system clock; prefer ``TimeService.now`` wherever an instance can be injected."""
    return datetime.now(UTC)


class TimeService:
    def now(self) -> datetime:
        """Aware UTC datetime."""
        return utc_now()

    def after(self, delta: timedelta) -> datetime:
        return self.now() + delta

    def is_past(self, moment: datetime) -> bool:
        """``True`` once ``moment`` has come: an ``expires_at`` equal to now is already expired."""
        return self.as_utc(moment) <= self.now()

    @staticmethod
    def as_utc(value: datetime) -> datetime:
        """A naive value is taken as UTC (SQLite drops tzinfo); an aware one is converted."""
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def to_iso(value: datetime, timespec: str = "milliseconds") -> str:
        """``2026-01-02T03:04:05.678Z``: the API's format."""
        return TimeService.as_utc(value).isoformat(timespec=timespec).replace("+00:00", "Z")

    @staticmethod
    def from_timestamp(seconds: float) -> datetime:
        return datetime.fromtimestamp(seconds, UTC)

    @staticmethod
    def parse_duration(value: str) -> timedelta:
        """``"15m"``, ``"12h"``, ``"30d"``: the format of durations in the environment."""
        match = _DURATION.match(value.strip())
        if not match:
            raise ValueError(f"Invalid duration format: {value!r} (expected e.g. '15m', '30d')")
        amount, unit = match.groups()
        return timedelta(**{_UNITS[unit]: int(amount)})


class FrozenTime(TimeService):
    """Time that stands still until ``advance``; for tests and replays."""

    def __init__(self, at: datetime | None = None) -> None:
        self._now = self.as_utc(at) if at is not None else utc_now()

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta
