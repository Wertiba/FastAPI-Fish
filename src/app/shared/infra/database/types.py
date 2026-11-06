from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.engine import Dialect

from app.shared.domain.time import TimeService


class UtcDateTime(sa.TypeDecorator[datetime]):
    """``timestamptz`` that always returns an aware UTC datetime, also on SQLite (which drops tzinfo)."""

    impl = sa.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else TimeService.as_utc(value)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else TimeService.as_utc(value)
