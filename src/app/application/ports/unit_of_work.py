from typing import Protocol

from app.domain.base import Base


class UnitOfWork(Protocol):
    async def add(self, entity: Base) -> None: ...
    async def delete(self, entity: Base) -> None: ...

    async def flush(self) -> None:
        """Sends pending changes without committing, e.g. so a new row can be referenced by FK.

        Raises ``DuplicateError`` on a uniqueness violation.
        """
        ...

    async def commit(self) -> None:
        """Raises ``DuplicateError`` on a uniqueness violation."""
        ...
