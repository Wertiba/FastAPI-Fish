import sqlalchemy as sa

from app.modules.auth.domain.entities import RefreshToken
from app.shared.infrastructure.database import UtcDateTime, map_entity, metadata

# FK на users.id — допустимая связь на уровне схемы БД: модули делят одну базу,
# но в коде auth ничего не импортирует из users, кроме ``users.public``.
refresh_tokens_table = sa.Table(
    "refresh_tokens",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    sa.Column("token_hash", sa.String(64), nullable=False, index=True),
    sa.Column("expires_at", UtcDateTime, nullable=False),
    sa.Column("created_at", UtcDateTime, nullable=False),
)


def map_tables() -> None:
    map_entity(RefreshToken, refresh_tokens_table)
