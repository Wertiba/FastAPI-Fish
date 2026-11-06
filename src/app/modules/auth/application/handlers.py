"""Reactions of ``auth`` to other modules' events; subscribed in ``auth/module.py``."""

from dataclasses import dataclass

from app.modules.auth.application.ports import RefreshTokenGateway
from app.modules.users.api.contracts import UserDeactivated


@dataclass
class RevokeSessionsOnUserDeactivated:
    refresh_token_gateway: RefreshTokenGateway

    async def __call__(self, event: UserDeactivated) -> None:
        await self.refresh_token_gateway.delete_by_user(event.user_id)
