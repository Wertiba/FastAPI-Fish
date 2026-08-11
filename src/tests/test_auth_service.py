import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions.user_exs import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.schemas.user import UserLoginBody, UserRegisterBody
from app.infrastructure.models import Base
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _auth_service(session):
    return AuthService(UnitOfWork(session), JWTService())


async def test_register_creates_user_and_returns_token_pair(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        body = UserRegisterBody(email="new@fish.io", password="password1", fullName="New Fish")

        response, refresh_token, max_age = await service.register(body)

        assert response.user.email == "new@fish.io"
        assert response.user.role.value == "USER"
        assert response.user.createdBy == response.user.id
        assert response.accessToken
        assert refresh_token
        assert max_age > 0


async def test_register_rejects_duplicate_email(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        await service.register(UserRegisterBody(email="dup@fish.io", password="password1", fullName="Fish One"))

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(UserAlreadyExistsError):
            await service.register(UserRegisterBody(email="dup@fish.io", password="password2", fullName="Fish Two"))


async def test_login_with_correct_credentials_returns_token_pair(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        await service.register(UserRegisterBody(email="login@fish.io", password="password1", fullName="Login Fish"))

    async with session_factory() as session:
        service = _auth_service(session)
        response, refresh_token, _ = await service.login_user(
            UserLoginBody(email="login@fish.io", password="password1")
        )
        assert response.user.email == "login@fish.io"
        assert refresh_token


async def test_login_with_wrong_password_raises(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        await service.register(UserRegisterBody(email="wrongpw@fish.io", password="password1", fullName="Fish"))

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidPasswordError):
            await service.login_user(UserLoginBody(email="wrongpw@fish.io", password="wrong-password"))


async def test_login_with_unknown_email_raises(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(UserNotFoundError):
            await service.login_user(UserLoginBody(email="ghost@fish.io", password="password1"))


async def test_refresh_rotates_token_and_invalidates_old_one(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        _, refresh_token, _ = await service.register(
            UserRegisterBody(email="rotate@fish.io", password="password1", fullName="Fish")
        )

    async with session_factory() as session:
        service = _auth_service(session)
        new_access, new_refresh, _ = await service.refresh_tokens(refresh_token)
        assert new_access.accessToken
        assert new_refresh != refresh_token

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens(refresh_token)


async def test_refresh_with_unknown_token_raises(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens("not-a-real-refresh-token")


async def test_logout_deletes_refresh_token_and_is_idempotent(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        _, refresh_token, _ = await service.register(
            UserRegisterBody(email="logout@fish.io", password="password1", fullName="Fish")
        )

    async with session_factory() as session:
        service = _auth_service(session)
        await service.logout(refresh_token)

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens(refresh_token)

    async with session_factory() as session:
        service = _auth_service(session)
        await service.logout(refresh_token)  # idempotent — no error


async def test_verify_access_token_returns_current_user_data(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        response, _, _ = await service.register(
            UserRegisterBody(email="verify@fish.io", password="password1", fullName="Fish")
        )
        access_token = response.accessToken

    async with session_factory() as session:
        service = _auth_service(session)
        user_data = await service.verify_access_token(access_token)
        assert user_data.email == "verify@fish.io"
