import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.enums import UserRole
from app.infrastructure.models import Base, User
from app.infrastructure.unit_of_work import UnitOfWork


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def test_user_repo_add_and_get_by_email(session_factory):
    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            user = User(
                id=uuid.uuid4(),
                email="fish@example.com",
                password="hashed",
                full_name="Fish Admin",
                role=UserRole.ADMIN,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_repo.add(user)

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            found = await uow.user_repo.get_by_email("fish@example.com")
            assert found is not None
            assert found.role == UserRole.ADMIN
            assert found.full_name == "Fish Admin"


async def test_refresh_token_repo_roundtrip(session_factory):
    from app.infrastructure.models import RefreshToken
    from datetime import timedelta

    user_id = uuid.uuid4()
    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            user = User(
                id=user_id,
                email="rt@example.com",
                password="hashed",
                full_name="RT User",
                role=UserRole.USER,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_repo.add(user)
            token = RefreshToken(
                id=uuid.uuid4(),
                user_id=user_id,
                hashed_token="abc123",
                expires_at=datetime.now(UTC) + timedelta(days=30),
                created_at=datetime.now(UTC),
            )
            await uow.refresh_token_repo.add(token)

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            found = await uow.refresh_token_repo.get_by_user_and_hash(user_id, "abc123")
            assert found is not None
            await uow.refresh_token_repo.delete_by_hash("abc123")

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            gone = await uow.refresh_token_repo.get_by_user_and_hash(user_id, "abc123")
            assert gone is None
