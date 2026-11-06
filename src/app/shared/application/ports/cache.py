from contextlib import AbstractAsyncContextManager
from datetime import timedelta
from typing import Protocol


class Cache(Protocol):
    """Key-value cache with expiry (Redis). Values are bytes; serialization is the caller's business."""

    async def get(self, key: str) -> bytes | None: ...

    async def set(self, key: str, value: bytes, ttl: timedelta) -> None: ...

    async def delete(self, key: str) -> None: ...


class DistributedLock(Protocol):
    """A lock shared by every process and replica: one scheduler tick, one payment per order.

    ``async with lock.acquire("job:digest", ttl) as acquired:`` -- ``acquired`` is ``False`` when someone
    else holds it; the lock is released on exit and expires by itself after ``ttl`` if the holder dies.
    """

    def acquire(self, name: str, ttl: timedelta) -> AbstractAsyncContextManager[bool]: ...
