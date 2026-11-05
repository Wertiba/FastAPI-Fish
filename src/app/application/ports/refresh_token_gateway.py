from typing import Protocol

from app.domain.refresh_tokens.entity import RefreshToken
from app.domain.users.ids import UserId


class RefreshTokenGateway(Protocol):
    async def get_by_user_and_hash(self, user_id: UserId, token_hash: str) -> RefreshToken | None: ...

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def delete_by_user(self, user_id: UserId) -> None:
        """Revokes every session of the user, in the current transaction."""
        ...
