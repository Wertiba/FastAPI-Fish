from datetime import datetime
from typing import Any, Protocol

from app.modules.auth.domain.refresh_token import RefreshToken
from app.shared.domain.ids import UserId

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 -- JWT claim discriminator
REFRESH_TOKEN_TYPE = "refresh"  # noqa: S105 -- JWT claim discriminator


class TokenService(Protocol):
    access_expire_seconds: int
    refresh_expire_seconds: int

    def create_access_token(self, subject: str) -> str: ...
    def create_refresh_token(self, subject: str) -> str: ...
    def decode_token(self, token: str, expected_type: str) -> dict[str, Any]:
        """Raises ``InvalidCredentialsError`` for a bad signature, expiry or token type."""
        ...

    def hash_token(self, raw_token: str) -> str: ...


class RefreshTokenGateway(Protocol):
    async def get_by_user_and_hash(self, user_id: UserId, token_hash: str) -> RefreshToken | None: ...

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def delete_by_user(self, user_id: UserId) -> None:
        """Revokes every session of the user, in the current transaction."""
        ...

    async def delete_expired(self, now: datetime) -> int:
        """Removes tokens that expired before ``now``; returns how many."""
        ...
