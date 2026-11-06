from typing import Protocol

from app.domain.base import Base


class UnitOfWork(Protocol):
    async def add(self, entity: Base) -> None: ...
    async def delete(self, entity: Base) -> None: ...
    async def commit(self) -> None:
        """Raises ``DuplicateError`` on a uniqueness violation."""
        ...
