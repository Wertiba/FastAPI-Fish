from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer

from app.application.schema import PyModel

__all__ = ["PyModel", "UtcDatetime", "format_utc", "timestamp_now"]


def format_utc(value: datetime) -> str:
    """``2026-01-02T03:04:05.678Z``"""
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timestamp_now() -> str:
    """``2026-01-02T03:04:05Z``: timestamp of an error body."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(format_utc, return_type=str, when_used="json")]
