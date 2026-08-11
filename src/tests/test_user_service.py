import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.enums import UserRole
from app.core.exceptions.user_exs import ForbiddenError, UserAlreadyExistsError, UserNotFoundError
from app.core.schemas.user import AdminRegisterUserBody, UserData, UserFilterQuery, UserUpdateBody
from app.core.utils.paginated import PaginationParams
from app.infrastructure.models import Base, RefreshToken
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.jwt_service import JWTService
from app.services.user_service import UserService


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _service(session):
    return UserService(UnitOfWork(session), JWTService())


def _admin_principal(user_id: uuid.UUID) -> UserData:
    return UserData(
        id=user_id, email="admin@fish.io", fullName="Admin", role=UserRole.ADMIN, isActive=True,
        createdAt="2026-01-01T00:00:00Z", updatedAt="2026-01-01T00:00:00Z", createdBy=user_id,
    )


async def test_create_user_allows_arbitrary_role(session_factory):
    async with session_factory() as session:
        service = _service(session)
        body = AdminRegisterUserBody(email="admin2@fish.io", password="password1", fullName="Fish", role=UserRole.ADMIN)
        created = await service.create_user(body)
        assert created.role == UserRole.ADMIN
        assert created.createdBy == created.id


async def test_create_user_rejects_duplicate_email(session_factory):
    async with session_factory() as session:
        service = _service(session)
        body = AdminRegisterUserBody(email="dup2@fish.io", password="password1", fullName="Fish")
        await service.create_user(body)

    async with session_factory() as session:
        service = _service(session)
        with pytest.raises(UserAlreadyExistsError):
            await service.create_user(AdminRegisterUserBody(email="dup2@fish.io", password="password1", fullName="Fish"))


async def test_get_by_id_raises_when_missing(session_factory):
    async with session_factory() as session:
        service = _service(session)
        with pytest.raises(UserNotFoundError):
            await service.get_by_id(uuid.uuid4())


async def test_self_update_of_full_name_is_allowed(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="self@fish.io", password="password1", fullName="Old Name"))
        self_principal = UserData(
            id=created.id, email=created.email, fullName=created.fullName, role=UserRole.USER, isActive=True,
            createdAt="2026-01-01T00:00:00Z", updatedAt="2026-01-01T00:00:00Z", createdBy=created.id,
        )

    async with session_factory() as session:
        service = _service(session)
        updated = await service.update_user(created.id, UserUpdateBody(fullName="New Name"), acting_user=self_principal)
        assert updated.fullName == "New Name"


async def test_self_cannot_change_own_role_or_is_active(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="escalate@fish.io", password="password1", fullName="Fish"))
        self_principal = UserData(
            id=created.id, email=created.email, fullName=created.fullName, role=UserRole.USER, isActive=True,
            createdAt="2026-01-01T00:00:00Z", updatedAt="2026-01-01T00:00:00Z", createdBy=created.id,
        )

    async with session_factory() as session:
        service = _service(session)
        with pytest.raises(ForbiddenError):
            await service.update_user(
                created.id, UserUpdateBody(fullName="Fish", role=UserRole.ADMIN), acting_user=self_principal
            )


async def test_admin_can_change_role_and_is_active(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="promote@fish.io", password="password1", fullName="Fish"))

    async with session_factory() as session:
        service = _service(session)
        admin = _admin_principal(uuid.uuid4())
        updated = await service.update_user(
            created.id, UserUpdateBody(fullName="Fish", role=UserRole.ADMIN, isActive=True), acting_user=admin
        )
        assert updated.role == UserRole.ADMIN


async def test_deactivate_revokes_all_refresh_tokens(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="revoke@fish.io", password="password1", fullName="Fish"))

    async with session_factory() as session:
        await session.execute(
            RefreshToken.__table__.insert().values(
                id=uuid.uuid4(),
                user_id=created.id,
                hashed_token="somehash",
                expires_at=datetime.now(UTC) + timedelta(days=1),
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with session_factory() as session:
        service = _service(session)
        await service.deactivate_by_id(created.id)

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            remaining = await uow.refresh_token_repo.get_by_user_and_hash(created.id, "somehash")
            assert remaining is None


async def test_get_all_users_applies_pagination_and_filters(session_factory):
    async with session_factory() as session:
        service = _service(session)
        await service.create_user(AdminRegisterUserBody(email="page1@fish.io", password="password1", fullName="Fish One"))
        await service.create_user(AdminRegisterUserBody(email="page2@fish.io", password="password1", fullName="Fish Two"))

    async with session_factory() as session:
        service = _service(session)
        page = await service.get_all_users(PaginationParams(page=0, size=20), UserFilterQuery(email="page1"))
        assert page.total == 1
        assert page.items[0].email == "page1@fish.io"
