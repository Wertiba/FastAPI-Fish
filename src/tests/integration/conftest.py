import shutil
import subprocess
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.core.enums import UserRole
from app.infrastructure.database.db_helper import db_helper
from app.infrastructure.models import Base, User
from app.main import app
from app.services.jwt_service import JWTService


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@pytest.fixture(scope="session")
def postgres_container():
    if not _docker_available():
        pytest.skip("Docker is not available - skipping Postgres integration tests")

    with PostgresContainer("postgres:15-alpine") as container:
        yield container


@pytest.fixture
async def pg_session_factory(postgres_container):
    url = (
        f"postgresql+asyncpg://{postgres_container.username}:{postgres_container.password}"
        f"@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(5432)}"
        f"/{postgres_container.dbname}"
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(pg_session_factory):
    # Starlette's sync TestClient runs the app on its own portal thread/event loop, which
    # asyncpg's loop-bound connections reject when called from the pytest-asyncio loop that
    # created them (aiosqlite tolerates this cross-loop use; asyncpg does not). An ASGI-transport
    # AsyncClient runs the app on the same event loop as this fixture, avoiding that entirely.
    async def override_session_getter():
        async with pg_session_factory() as session:
            yield session

    app.dependency_overrides[db_helper.session_getter] = override_session_getter
    original_session_factory = db_helper.session_factory
    db_helper.session_factory = pg_session_factory

    try:
        # https scheme, not http: with APP_COOKIE_SECURE=true (the .env.example / CI default),
        # Set-Cookie responses carry the Secure attribute, and httpx's cookie jar will only
        # store/resend Secure cookies for an https origin.
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://testserver") as test_client:
            yield test_client
    finally:
        db_helper.session_factory = original_session_factory
        app.dependency_overrides.clear()


@pytest.fixture
async def admin_headers(pg_session_factory, client):
    admin_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with pg_session_factory() as session:
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
