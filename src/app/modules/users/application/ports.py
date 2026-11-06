from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.users.domain.entity import User
from app.modules.users.domain.enums import UserRole
from app.shared.domain.ids import UserId


@dataclass(kw_only=True)
class UserCriteria:
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class UserGateway(Protocol):
    async def get_by_id(self, id_: UserId) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_all(self, offset: int, limit: int, criteria: UserCriteria) -> list[User]:
        """Active users first, newest first."""
        ...

    async def count(self, criteria: UserCriteria) -> int: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, password_hash: str) -> bool: ...
    def verify_dummy(self, password: str) -> None:
        """Spends as long as ``verify`` does, for an email that does not exist."""
        ...
