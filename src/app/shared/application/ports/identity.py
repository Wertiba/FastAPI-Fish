from dataclasses import dataclass
from typing import Protocol

from app.shared.domain.ids import UserId


@dataclass(frozen=True, kw_only=True)
class CurrentUser:
    """The authenticated caller. Modules read the rest (role, profile) through the module that owns it."""

    id: UserId


class IdentityProvider(Protocol):
    """Implemented by the ``auth`` module; the rest of the app depends on this port, not on ``auth``."""

    async def authenticate(self, access_token: str) -> CurrentUser:
        """Raises ``InvalidCredentialsError`` for a bad token or an inactive user."""
        ...
