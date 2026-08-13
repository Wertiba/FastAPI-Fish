from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.db_helper import db_helper
from app.infrastructure.models import Base
from app.main import app


@pytest.fixture
async def db_session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@asynccontextmanager
async def _client_bound_to(session_factory):
    async def override_session_getter():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[db_helper.session_getter] = override_session_getter
    original_session_factory = db_helper.session_factory
    db_helper.session_factory = session_factory

    try:
        # https scheme, not http: with APP_COOKIE_SECURE=true (the .env.example / CI default),
        # Set-Cookie responses carry the Secure attribute, and httpx's cookie jar will only
        # store/resend Secure cookies for an https origin. Over plain http the jar silently
        # drops the refreshToken cookie, breaking every test that relies on the client
        # resending it automatically.
        with TestClient(app, base_url="https://testserver") as test_client:
            yield test_client
    finally:
        db_helper.session_factory = original_session_factory
        app.dependency_overrides.clear()


@pytest.fixture
async def client(db_session_factory):
    async with _client_bound_to(db_session_factory) as test_client:
        yield test_client


@pytest.fixture
async def admin_headers(db_session_factory, client):
    import uuid
    from datetime import UTC, datetime

    from app.core.enums import UserRole
    from app.infrastructure.models import User
    from app.services.jwt_service import JWTService

    admin_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with db_session_factory() as session:
        session.add(
            User(
                id=admin_id,
                email="admin@fish.io",
                password=JWTService().get_password_hash("adminpass1"),
                full_name="Admin Fish",
                role=UserRole.ADMIN,
                is_active=True,
                created_by=admin_id,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    access_token = JWTService().create_access_token(str(admin_id))
    return {"Authorization": f"Bearer {access_token}"}
