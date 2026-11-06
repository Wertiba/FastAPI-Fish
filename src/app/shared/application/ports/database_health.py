from typing import Protocol


class DatabaseHealth(Protocol):
    async def check(self) -> None: ...
