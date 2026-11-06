from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.users.entity import User
from app.domain.users.enums import UserRole


@dataclass(kw_only=True)
class UserCriteria:
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class UserGateway(Protocol):
    async def get_by_id(self, id_: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_all(self, offset: int, limit: int, criteria: UserCriteria) -> list[User]:
        """Active users first, newest first."""
        ...

    async def count(self, criteria: UserCriteria) -> int: ...
