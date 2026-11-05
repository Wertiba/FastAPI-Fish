from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.engine import Dialect


def _as_aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class UtcDateTime(sa.TypeDecorator[datetime]):
    """``timestamptz`` that always returns an aware UTC datetime, also on SQLite (which drops tzinfo)."""

    impl = sa.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else _as_aware_utc(value)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else _as_aware_utc(value)
