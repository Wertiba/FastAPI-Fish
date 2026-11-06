from sqlalchemy import Column, ForeignKey, String, Table, Uuid

from app.modules.auth.domain.refresh_token import RefreshToken
from app.shared.infra.database.registry import map_once, metadata
from app.shared.infra.database.types import UtcDateTime

# The foreign key names the ``users`` table, not the ``users`` module: the database keeps
# integrity, and no Python import crosses the module boundary.
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
    map_once(RefreshToken, refresh_tokens)


start_mappers()
