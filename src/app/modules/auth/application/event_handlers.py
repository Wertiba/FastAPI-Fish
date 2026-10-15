from app.modules.auth.application.ports import RefreshTokenRepository
from app.modules.users.public import UserDeactivated
from app.shared.application.events import EventHandler


class RevokeSessionsOnUserDeactivated(EventHandler[UserDeactivated]):
    """Деактивированный пользователь теряет все refresh-токены (в той же транзакции)."""

    def __init__(self, refresh_tokens: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_tokens

    async def handle(self, event: UserDeactivated) -> None:
        await self._refresh_tokens.delete_all_for_user(event.user_id)
