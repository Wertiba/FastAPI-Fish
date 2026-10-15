from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.shared.domain.time import utc_now


@dataclass(kw_only=True, eq=False)
class RefreshToken:
    """Хранится только SHA-256 хеш токена; сам токен живёт в HttpOnly-куке клиента."""

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime

    @classmethod
    def issue(cls, *, user_id: UUID, token_hash: str, ttl_seconds: int) -> "RefreshToken":
        now = utc_now()
        return cls(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=now + timedelta(seconds=ttl_seconds),
            created_at=now,
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        return self.expires_at <= (now or utc_now())
