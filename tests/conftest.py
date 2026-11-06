"""Shared fixtures.

Tests run on in-memory SQLite by default: no Docker and no ``.env`` needed.
``TEST_DB_URL=postgresql+asyncpg://...`` runs the same suite on PostgreSQL (every test gets clean tables).
"""

import os

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password-1"
USER_PASSWORD = "user-password-1"

for _key, _value in {
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "app_test",
    "DB_USER": "postgres",
    "DB_PASSWORD": "postgres",
    "APP_SECURITY_JWT_SECRET": "test-secret-not-for-production-0123456789",
    "APP_SECURITY_ACCESS_TOKEN_EXPIRATION": "15m",
    "APP_SECURITY_REFRESH_TOKEN_EXPIRATION": "30d",
    "APP_COOKIE_SECURE": "true",
    "LOG_CONSOLE_LEVEL": "WARNING",
}.items():
    os.environ.setdefault(_key, _value)
# The admin is part of the fixtures, so values from the developer's shell must not leak in.
os.environ["ADMIN_EMAIL"] = ADMIN_EMAIL
os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD

from collections.abc import AsyncIterator, Callable, Iterator  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from typing import Any  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
from dishka import Provider, Scope, provide  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.bootstrap import build_container  # noqa: E402
from app.infra.database.db_helper import DatabaseHelper  # noqa: E402
from app.infra.database import metadata  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_DB_URL = os.getenv("TEST_DB_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture
async def db_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    if TEST_DB_URL.startswith("sqlite"):
        engine = create_async_engine(TEST_DB_URL, poolclass=StaticPool, connect_args={"check_same_thread": False})
    else:
        engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def make_app(db_session_factory: async_sessionmaker[AsyncSession]) -> Callable[[], FastAPI]:
    class TestDatabaseProvider(Provider):
        @provide(scope=Scope.APP, override=True)
        def database(self) -> DatabaseHelper:
            return SimpleNamespace(session_factory=db_session_factory)  # type: ignore[return-value]

    return lambda: create_app(build_container(TestDatabaseProvider()))


@pytest.fixture
def client(make_app: Callable[[], FastAPI]) -> Iterator[TestClient]:
    # https: with APP_COOKIE_SECURE=true httpx drops the Secure refresh cookie on plain http.
    with TestClient(make_app(), base_url="https://testserver") as test_client:
        yield test_client


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert response.status_code == 200, response.text
    return bearer(response.json()["accessToken"])


RegisterUser = Callable[..., dict[str, Any]]


@pytest.fixture
def register_user(client: TestClient) -> RegisterUser:
    """Registers a user; returns the response body plus ready ``headers`` and the ``refreshToken``."""

    def _register(email: str | None = None, full_name: str = "Test User") -> dict[str, Any]:
        body = {
            "email": email or f"user-{uuid4().hex[:8]}@example.com",
            "password": USER_PASSWORD,
            "fullName": full_name,
        }
        response = client.post("/api/v1/auth/register", json=body)
        assert response.status_code == 201, response.text
        data: dict[str, Any] = response.json()
        data["headers"] = bearer(data["accessToken"])
        data["refreshToken"] = response.cookies["refreshToken"]
        return data

    return _register
