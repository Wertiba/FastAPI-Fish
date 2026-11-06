from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Uuid, true

from app.modules.users.domain.entity import User
from app.modules.users.domain.enums import UserRole
from app.shared.infra.database.registry import map_once, metadata, str_enum
from app.shared.infra.database.types import UtcDateTime

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


def start_mappers() -> None:
    map_once(User, users)


start_mappers()
