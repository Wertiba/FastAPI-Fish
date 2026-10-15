from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.users.domain.entities import User
from app.shared.application.pagination import Pagination
from app.shared.domain.identity import UserRole


@dataclass(frozen=True, slots=True, kw_only=True)
class UserFilter:
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class UserRepository(Protocol):
    async def add(self, user: User) -> None:
        """Бросает ``EmailAlreadyExistsError`` при нарушении уникальности."""
        ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def find(self, filters: UserFilter, pagination: Pagination) -> list[User]: ...

    async def count(self, filters: UserFilter) -> int: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...
