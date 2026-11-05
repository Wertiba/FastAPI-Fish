from typing import Protocol

from app.domain.refresh_tokens.entity import RefreshToken
from app.domain.users.entity import User

type Entity = User | RefreshToken


class UnitOfWork(Protocol):
    async def add(self, entity: Entity) -> None: ...
    async def delete(self, entity: Entity) -> None: ...
    async def commit(self) -> None:
        """Raises ``DuplicateError`` on a uniqueness violation."""
        ...
