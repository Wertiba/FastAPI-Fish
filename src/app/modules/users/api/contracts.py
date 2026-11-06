"""Public contract of the ``users`` module for other modules' domain and application code.

Everything else in ``app.modules.users`` is private: other modules import only ``users.api``,
and the architecture tests enforce it.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from app.modules.users.domain.enums import UserRole
from app.modules.users.domain.errors import UserAlreadyExistsError
from app.shared.application.events import IntegrationEvent
from app.shared.domain.ids import UserId

__all__ = ["UserAlreadyExistsError", "UserDeactivated", "UserInfo", "UserRole", "UsersFacade"]


@dataclass(kw_only=True)
class UserInfo:
    id: UserId
    email: str
    fullName: str
    role: UserRole
    isActive: bool
    createdAt: datetime
    updatedAt: datetime
    createdBy: UserId


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(IntegrationEvent):
    """Published in the deactivating transaction.

    ``auth`` revokes sessions in that same transaction (``subscriptions``); the event also goes through
    the outbox to the worker and Kafka, for reactions that may happen later (``consumers``).
    """

    topic: ClassVar[str] = "users.user.deactivated"

    user_id: UserId

    def key(self) -> str:
        return str(self.user_id)


class UsersFacade(Protocol):
    async def get(self, user_id: UserId) -> UserInfo | None: ...

    async def check_credentials(self, email: str, password: str) -> UserInfo | None:
        """``None`` for an unknown email or a wrong password; both take as long, so emails do not leak."""
        ...

    async def register(self, *, email: str, password: str, full_name: str) -> UserInfo:
        """Adds a self-registered ``USER`` to the request's unit of work; the caller commits.

        Raises ``UserAlreadyExistsError`` when the email is taken.
        """
        ...

    async def is_admin(self, user_id: UserId) -> bool:
        """The role is read from the database, so revoking it takes effect before the access token expires."""
        ...
