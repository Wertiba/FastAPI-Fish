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


@pytest.fixture
async def client(db_session_factory):
    async def override_session_getter():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[db_helper.session_getter] = override_session_getter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
