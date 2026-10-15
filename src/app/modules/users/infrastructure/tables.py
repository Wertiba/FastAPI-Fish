import sqlalchemy as sa

from app.modules.users.domain.entities import User
from app.shared.domain.identity import UserRole
from app.shared.infrastructure.database import UtcDateTime, map_entity, metadata

users_table = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("email", sa.String(254), nullable=False, unique=True),
    sa.Column("password_hash", sa.String(255), nullable=False),
    sa.Column("full_name", sa.String(200), nullable=False),
    sa.Column(
        "role",
        sa.Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    ),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.Column("created_by", sa.Uuid, sa.ForeignKey("users.id"), nullable=False),
    sa.Column("created_at", UtcDateTime, nullable=False),
    sa.Column("updated_at", UtcDateTime, nullable=False),
)


def map_tables() -> None:
    map_entity(User, users_table)
