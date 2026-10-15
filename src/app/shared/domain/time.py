from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_aware_utc(value: datetime) -> datetime:
    """Наивные datetime считаются UTC (SQLite теряет tzinfo при чтении)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
