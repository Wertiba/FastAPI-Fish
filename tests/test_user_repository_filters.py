import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.enums import UserRole
from app.core.schemas.user import UserFilterQuery
from app.infrastructure.models import Base, User
from app.infrastructure.repositories import UserRepository


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _make_user(repo, **overrides):
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        email="user@example.com",
        password="hashed",
        full_name="Some User",
        role=UserRole.USER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return await repo.add(User(**defaults))


async def test_email_and_full_name_filters_are_case_insensitive_contains(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        await _make_user(repo, email="alice@fish.io", full_name="Alice Fisher")
        await _make_user(repo, email="bob@fish.io", full_name="Bob Carp")
        await session.commit()

        results = await repo.get_filtered(UserFilterQuery(email="ALICE"), offset=0, limit=10)
        assert [u.email for u in results] == ["alice@fish.io"]

        results = await repo.get_filtered(UserFilterQuery(fullName="carp"), offset=0, limit=10)
        assert [u.email for u in results] == ["bob@fish.io"]


async def test_role_and_is_active_filters_are_exact_match(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        await _make_user(repo, email="admin@fish.io", role=UserRole.ADMIN)
        await _make_user(repo, email="inactive@fish.io", is_active=False)
        await session.commit()

        results = await repo.get_filtered(UserFilterQuery(role=UserRole.ADMIN), offset=0, limit=10)
        assert [u.email for u in results] == ["admin@fish.io"]

        results = await repo.get_filtered(UserFilterQuery(isActive=False), offset=0, limit=10)
        assert [u.email for u in results] == ["inactive@fish.io"]


async def test_created_at_range_filter_is_inclusive(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        base = datetime(2026, 1, 1, tzinfo=UTC)
        await _make_user(repo, email="early@fish.io", created_at=base - timedelta(days=10))
        await _make_user(repo, email="mid@fish.io", created_at=base)
        await _make_user(repo, email="late@fish.io", created_at=base + timedelta(days=10))
        await session.commit()

        results = await repo.get_filtered(
            UserFilterQuery(createdFrom=base, createdTo=base + timedelta(days=10)), offset=0, limit=10
        )
        assert {u.email for u in results} == {"mid@fish.io", "late@fish.io"}


async def test_results_sorted_active_desc_then_created_at_desc(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        base = datetime(2026, 1, 1, tzinfo=UTC)
        await _make_user(repo, email="old_active@fish.io", is_active=True, created_at=base)
        await _make_user(repo, email="new_active@fish.io", is_active=True, created_at=base + timedelta(days=1))
        await _make_user(repo, email="new_inactive@fish.io", is_active=False, created_at=base + timedelta(days=2))
        await session.commit()

        results = await repo.get_filtered(UserFilterQuery(), offset=0, limit=10)
        assert [u.email for u in results] == [
            "new_active@fish.io",
            "old_active@fish.io",
            "new_inactive@fish.io",
        ]


async def test_count_filtered_matches_filtered_results(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        await _make_user(repo, email="a@fish.io", role=UserRole.ADMIN)
        await _make_user(repo, email="b@fish.io", role=UserRole.USER)
        await session.commit()

        assert await repo.count_filtered(UserFilterQuery(role=UserRole.ADMIN)) == 1
        assert await repo.count_filtered(UserFilterQuery()) == 2
