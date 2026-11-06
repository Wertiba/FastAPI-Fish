from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base, utc_now


class RefreshToken(Base, kw_only=True):
    """Only the SHA-256 hash is stored; the token itself lives in the client's HttpOnly cookie."""

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default_factory=utc_now)
