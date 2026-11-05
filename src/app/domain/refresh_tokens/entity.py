from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.refresh_tokens.ids import RefreshTokenId
from app.domain.users.ids import UserId


@dataclass(eq=False, kw_only=True)
class RefreshToken:
    """Only the SHA-256 hash is stored; the token itself lives in the client's HttpOnly cookie."""

    id: RefreshTokenId = field(default_factory=uuid4)
    user_id: UserId
    token_hash: str
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
