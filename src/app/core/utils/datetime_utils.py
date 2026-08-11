from datetime import datetime, timezone


def as_aware_utc(dt: datetime) -> datetime:
    """Normalize a possibly-naive datetime to timezone-aware UTC.

    SQLite (aiosqlite) round-trips TIMESTAMP(timezone=True) columns as naive
    datetimes even though the value was written as UTC-aware; Postgres preserves
    tzinfo. Normalize so comparisons/serialization against aware UTC datetimes
    work consistently on both backends.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
