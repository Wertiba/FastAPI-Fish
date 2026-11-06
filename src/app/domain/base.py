"""Base of every entity: a declarative SQLAlchemy model that is also a dataclass.

An entity is the business object and its table at once, so a field is declared in one place.
``eq=False`` compares entities by identity, as the ORM does. Subclasses repeat ``kw_only=True``: the base
sets it at runtime, but type checkers read it only from the class itself; it keeps the field order free.
"""

from datetime import UTC, datetime
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


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


def str_enum(enum_cls: type[Enum], name: str, length: int = 20) -> sa.Enum:
    """Enum stored as plain VARCHAR with the member values."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
    )


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True, eq=False):
    metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: UtcDateTime()}
