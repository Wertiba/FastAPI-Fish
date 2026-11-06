"""Redis cache and distributed lock, with in-process fallbacks when ``REDIS_URL`` is empty."""

import time
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from app.shared.application.ports.cache import Cache, DistributedLock
from app.shared.infra.config import RedisConfig

# Deletes the lock only if it still holds our token: an expired lock re-taken by someone else survives.
_RELEASE = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end return 0"


class RedisCache(Cache):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, key: str) -> bytes | None:
        value: bytes | str | None = await self._redis.get(key)
        return value.encode() if isinstance(value, str) else value

    async def set(self, key: str, value: bytes, ttl: timedelta) -> None:
        await self._redis.set(key, value, px=int(ttl.total_seconds() * 1000))

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)


class RedisLock(DistributedLock):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def acquire(self, name: str, ttl: timedelta) -> AbstractAsyncContextManager[bool]:
        return self._acquire(f"lock:{name}", ttl)

    @asynccontextmanager
    async def _acquire(self, key: str, ttl: timedelta) -> AsyncIterator[bool]:
        token = uuid4().hex
        acquired = bool(await self._redis.set(key, token, nx=True, px=int(ttl.total_seconds() * 1000)))
        try:
            yield acquired
        finally:
            if acquired:
                await self._redis.eval(_RELEASE, 1, key, token)  # type: ignore[misc]


class InMemoryCache(Cache):
    """One process only: each replica has its own copy."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[bytes, float]] = {}

    async def get(self, key: str) -> bytes | None:
        item = self._items.get(key)
        if item is None or item[1] <= time.monotonic():
            self._items.pop(key, None)
            return None
        return item[0]

    async def set(self, key: str, value: bytes, ttl: timedelta) -> None:
        self._items[key] = (value, time.monotonic() + ttl.total_seconds())

    async def delete(self, key: str) -> None:
        self._items.pop(key, None)


class InMemoryLock(DistributedLock):
    """Excludes only within one process; run one replica of a process that relies on it."""

    def __init__(self) -> None:
        self._held: dict[str, float] = {}

    def acquire(self, name: str, ttl: timedelta) -> AbstractAsyncContextManager[bool]:
        return self._acquire(name, ttl)

    @asynccontextmanager
    async def _acquire(self, name: str, ttl: timedelta) -> AsyncIterator[bool]:
        now = time.monotonic()
        if self._held.get(name, 0.0) > now:
            yield False
            return
        self._held[name] = now + ttl.total_seconds()
        try:
            yield True
        finally:
            self._held.pop(name, None)


@dataclass(frozen=True)
class _CacheBackend:
    cache: Cache
    lock: DistributedLock


class CacheProvider(Provider):
    scope = Scope.APP

    @provide
    async def backend(self, config: RedisConfig) -> AsyncIterator[_CacheBackend]:
        if not config.url:
            yield _CacheBackend(InMemoryCache(), InMemoryLock())
            return
        redis = Redis.from_url(config.url)
        try:
            yield _CacheBackend(RedisCache(redis), RedisLock(redis))
        finally:
            await redis.aclose()

    @provide
    def cache(self, backend: _CacheBackend) -> Cache:
        return backend.cache

    @provide
    def lock(self, backend: _CacheBackend) -> DistributedLock:
        return backend.lock
