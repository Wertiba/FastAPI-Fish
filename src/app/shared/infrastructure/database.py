"""Общая инфраструктура БД: metadata, imperative mapping, engine.

Доменные сущности — обычные dataclass'ы без зависимости от SQLAlchemy.
Каждый модуль описывает свои таблицы через ``Table(..., metadata)`` и
привязывает к ним сущности функцией ``map_entity`` (imperative mapping).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import registry
from sqlalchemy.pool import StaticPool

from app.shared.domain.time import as_aware_utc

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)
mapper_registry = registry(metadata=metadata)


def map_entity(entity: type[Any], table: sa.Table, **kwargs: Any) -> None:
    """Идемпотентный ``map_imperatively``: безопасно вызывать повторно (тесты, reload)."""
    if any(mapper.class_ is entity for mapper in mapper_registry.mappers):
        return
    mapper_registry.map_imperatively(entity, table, **kwargs)


class UtcDateTime(sa.TypeDecorator[datetime]):
    """``timestamptz``, который всегда возвращает aware-UTC datetime (в т.ч. на SQLite)."""

    impl = sa.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else as_aware_utc(value)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else as_aware_utc(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class DatabaseConfig:
    url: str
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 10


def create_engine(config: DatabaseConfig) -> AsyncEngine:
    if config.url.startswith("sqlite"):
        # Для тестов и прототипов: одна общая in-memory БД на процесс.
        return create_async_engine(
            config.url,
            echo=config.echo,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(
        config.url,
        echo=config.echo,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_pre_ping=True,
    )


def create_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, autoflush=False, expire_on_commit=False)
