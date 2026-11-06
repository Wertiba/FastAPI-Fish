from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.shared.domain.ids import UserId
from app.shared.domain.time import utc_now

type RefreshTokenId = UUID


@dataclass(eq=False, kw_only=True)
class RefreshToken:
    """Only the SHA-256 hash is stored; the token itself lives in the client's HttpOnly cookie."""

    id: RefreshTokenId = field(default_factory=uuid4)
    user_id: UserId
    token_hash: str
    expires_at: datetime
    created_at: datetime = field(default_factory=utc_now)
