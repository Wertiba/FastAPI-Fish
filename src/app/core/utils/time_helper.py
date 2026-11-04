import re
from datetime import UTC, datetime, timedelta
from typing import Literal

_DURATION_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_DURATION_PATTERN = re.compile(r"^(\d+)([smhd])$")


class TimeHelper:
    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def after(seconds: int) -> datetime:
        """Current UTC time shifted by `seconds` (e.g. a token expiry moment)."""
        return TimeHelper.now_utc() + timedelta(seconds=seconds)

    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """Naive datetimes are treated as UTC; aware ones are converted to UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    @staticmethod
    def to_iso_z(dt: datetime, timespec: Literal["seconds", "milliseconds"] = "milliseconds") -> str:
        """2026-01-01T12:00:00.000Z (or ...12:00:00Z with timespec="seconds")."""
        return TimeHelper.to_utc(dt).isoformat(timespec=timespec).replace("+00:00", "Z")

    @staticmethod
    def now_iso_z() -> str:
        return TimeHelper.to_iso_z(TimeHelper.now_utc(), timespec="seconds")

    @staticmethod
    def parse_duration(value: str) -> int:
        """'15m' -> 900. Units: s, m, h, d."""
        match = _DURATION_PATTERN.match(value.strip())
        if not match:
            raise ValueError(f"Invalid duration format: {value!r} (expected e.g. '15m', '30d')")
        amount, unit = match.groups()
        return int(amount) * _DURATION_UNIT_SECONDS[unit]
