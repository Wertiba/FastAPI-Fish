from typing import Protocol


class UnitOfWork(Protocol):
    """One per request, shared by every module: a use case that touches several modules commits once."""

    async def add(self, entity: object) -> None: ...
    async def delete(self, entity: object) -> None: ...
    async def flush(self) -> None:
        """Sends pending changes without committing, e.g. so other modules can reference a new row by FK.

        Raises ``DuplicateError`` on a uniqueness violation.
        """
        ...

    async def commit(self) -> None:
        """Raises ``DuplicateError`` on a uniqueness violation."""
        ...
