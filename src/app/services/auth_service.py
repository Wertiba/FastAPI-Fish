from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.enums import UserRole
from app.core.exceptions.user_exs import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotActiveError,
    UserNotFoundError,
)
from app.core.schemas.token import AccessTokenResponse
from app.core.schemas.user import UserAndAccessTokenResponse, UserData, UserLoginBody, UserReadResponse, UserRegisterBody
from app.infrastructure.models import RefreshToken, User
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.jwt_service import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, JWTService


def _expiry(seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


def _as_aware_utc(value: datetime) -> datetime:
    # SQLite (aiosqlite) round-trips TIMESTAMP(timezone=True) columns as naive
    # datetimes even though the value was written as UTC-aware; Postgres preserves
    # tzinfo. Normalize so comparisons against datetime.now(UTC) work on both backends.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthService:
    def __init__(self, uow: UnitOfWork, jwt_service: JWTService):
        self.uow = uow
        self.jwt_service = jwt_service

    @staticmethod
    def _to_read_response(user: User) -> UserReadResponse:
        return UserReadResponse(
            id=user.id,
            email=user.email,
            fullName=user.full_name,
            role=user.role,
            isActive=user.is_active,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
            createdBy=user.created_by,
        )

    async def _authenticate_user(self, email: str, password: str) -> User:
        user = await self.uow.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundError
        if not self.jwt_service.verify_password(password, str(user.password)):
            raise InvalidPasswordError
        if not user.is_active:
            raise UserNotActiveError
        return user

    async def _issue_token_pair(self, user: User) -> tuple[UserAndAccessTokenResponse, str, int]:
        access_token = self.jwt_service.create_access_token(str(user.id))
        refresh_token = self.jwt_service.create_refresh_token(str(user.id))
        max_age = self.jwt_service.refresh_expire_seconds

        await self.uow.refresh_token_repo.add(
            RefreshToken(
                user_id=user.id,
                hashed_token=self.jwt_service.hash_token(refresh_token),
                expires_at=_expiry(max_age),
            )
        )

        response = UserAndAccessTokenResponse(
            accessToken=access_token,
            expiresIn=self.jwt_service.access_expire_seconds,
            user=self._to_read_response(user),
        )
        return response, refresh_token, max_age

    async def register(self, user_data: UserRegisterBody) -> tuple[UserAndAccessTokenResponse, str, int]:
        async with self.uow:
            existing_user = await self.uow.user_repo.get_by_email(user_data.email)
            if existing_user:
                raise UserAlreadyExistsError

            hashed_password = self.jwt_service.get_password_hash(user_data.password)
            user = await self.uow.user_repo.add(
                User(
                    email=user_data.email,
                    password=hashed_password,
                    full_name=user_data.fullName,
                    role=UserRole.USER,
                    is_active=True,
                )
            )
            user = await self.uow.user_repo.update(user.id, {"created_by": user.id})
            return await self._issue_token_pair(user)

    async def login_user(self, login_body: UserLoginBody) -> tuple[UserAndAccessTokenResponse, str, int]:
        async with self.uow:
            user = await self._authenticate_user(login_body.email, login_body.password)
            return await self._issue_token_pair(user)

    async def refresh_tokens(self, raw_refresh_token: str) -> tuple[AccessTokenResponse, str, int]:
        async with self.uow:
            payload = self.jwt_service.decode_token(raw_refresh_token, expected_type=REFRESH_TOKEN_TYPE)
            user_id = UUID(payload["sub"])
            hashed = self.jwt_service.hash_token(raw_refresh_token)

            stored = await self.uow.refresh_token_repo.get_by_user_and_hash(user_id, hashed)
            if stored is None or _as_aware_utc(stored.expires_at) < datetime.now(UTC):
                raise InvalidCredentialsError

            user = await self.uow.user_repo.get_by_id(user_id)
            if user is None or not user.is_active:
                raise InvalidCredentialsError

            await self.uow.refresh_token_repo.delete_by_hash(hashed)

            new_access_token = self.jwt_service.create_access_token(str(user.id))
            new_refresh_token = self.jwt_service.create_refresh_token(str(user.id))
            max_age = self.jwt_service.refresh_expire_seconds

            await self.uow.refresh_token_repo.add(
                RefreshToken(
                    user_id=user.id,
                    hashed_token=self.jwt_service.hash_token(new_refresh_token),
                    expires_at=_expiry(max_age),
                )
            )

            response = AccessTokenResponse(
                accessToken=new_access_token,
                expiresIn=self.jwt_service.access_expire_seconds,
            )
            return response, new_refresh_token, max_age

    async def logout(self, raw_refresh_token: str) -> None:
        async with self.uow:
            hashed = self.jwt_service.hash_token(raw_refresh_token)
            await self.uow.refresh_token_repo.delete_by_hash(hashed)

    async def verify_access_token(self, access_token: str) -> UserData:
        async with self.uow:
            payload = self.jwt_service.decode_token(access_token, expected_type=ACCESS_TOKEN_TYPE)
            user_id = UUID(payload["sub"])
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise InvalidCredentialsError
            return UserData(
                id=user.id,
                email=user.email,
                fullName=user.full_name,
                role=user.role,
                isActive=user.is_active,
                createdAt=user.created_at,
                updatedAt=user.updated_at,
                createdBy=user.created_by,
            )
