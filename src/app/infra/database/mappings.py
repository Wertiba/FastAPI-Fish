"""All tables and their imperative mapping onto plain domain dataclasses.

Domain entities know nothing about SQLAlchemy; this module binds them to tables.
Alembic autogenerate reads ``metadata`` from here.
"""

from enum import Enum

from sqlalchemy import Boolean, Column, ForeignKey, MetaData, String, Table, Uuid, true
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import registry

from app.domain.refresh_tokens.entity import RefreshToken
from app.domain.users.entity import User
from app.domain.users.enums import UserRole
from app.infra.database.types import UtcDateTime

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

mapper_registry = registry(metadata=MetaData(naming_convention=NAMING_CONVENTION))
metadata = mapper_registry.metadata


def str_enum(enum_cls: type[Enum], name: str, length: int = 20) -> SAEnum:
    """Enum stored as plain VARCHAR with the member values."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
    )


users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("full_name", String(200), nullable=False),
    Column("role", str_enum(UserRole, "user_role"), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=true()),
    Column("created_by", Uuid, ForeignKey("users.id"), nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("updated_at", UtcDateTime, nullable=False),
)
refresh_tokens = Table(
    "refresh_tokens",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("token_hash", String(64), nullable=False, index=True),
    Column("expires_at", UtcDateTime, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
)


def start_mappers() -> None:
    """Configure once; both ASGI startup and Alembic use this metadata."""
    if list(mapper_registry.mappers):
        return
    mapper_registry.map_imperatively(User, users)
    mapper_registry.map_imperatively(RefreshToken, refresh_tokens)


start_mappers()
