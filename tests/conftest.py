"""Общие фикстуры.

По умолчанию тесты идут на in-memory SQLite — без Docker и без .env.
``TEST_DB_URL=postgresql+asyncpg://...`` прогоняет тот же набор на PostgreSQL
(каждый тест получает чистые таблицы).
"""

import os
from collections.abc import Callable, Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bootstrap.config import Settings
from app.main import create_app
from app.shared.infrastructure.database import metadata

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password-1"
USER_PASSWORD = "user-password-1"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_SECURITY_JWT_SECRET="test-secret-test-secret-test-secret",
        DB_URL=os.getenv("TEST_DB_URL", "sqlite+aiosqlite:///:memory:"),
        DB_CREATE_TABLES=True,
        APP_ADMIN_EMAIL=ADMIN_EMAIL,
        APP_ADMIN_PASSWORD=ADMIN_PASSWORD,
        APP_COOKIE_SECURE=False,
        LOG_FILE="",
        LOG_LEVEL="WARNING",
    )


async def _drop_all(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
        if not settings.database_url.startswith("sqlite"):
            engine = test_client.portal.call(app.state.dishka_container.get, AsyncEngine)
            test_client.portal.call(_drop_all, engine)


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
    """Регистрирует пользователя; возвращает тело ответа + готовые заголовки ``headers``."""

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
