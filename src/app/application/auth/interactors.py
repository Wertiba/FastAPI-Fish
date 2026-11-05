from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.application.auth.dto import AccessTokenResult, RefreshCookie
from app.application.exceptions import DuplicateError
from app.application.ports.refresh_token_gateway import RefreshTokenGateway
from app.application.ports.tokens import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TokenService
from app.application.ports.unit_of_work import UnitOfWork
from app.application.ports.user_gateway import UserGateway
from app.application.users.dto import (
    UserAndAccessTokenResult,
    UserData,
    UserLoginData,
    UserRegisterData,
    to_user_result,
)
from app.domain.refresh_tokens.entity import RefreshToken
from app.domain.users.entity import User
from app.domain.users.enums import UserRole
from app.domain.users.errors import InvalidCredentialsError, UserAlreadyExistsError, UserNotActiveError
from app.domain.users.ids import UserId


def _subject(payload: dict[str, Any]) -> UserId:
    try:
        return UUID(str(payload["sub"]))
    except (KeyError, ValueError):
        raise InvalidCredentialsError from None


@dataclass
class _AuthContext:
    uow: UnitOfWork
    user_gateway: UserGateway
    refresh_token_gateway: RefreshTokenGateway
    jwt_service: TokenService

    async def _authenticate_user(self, email: str, password: str) -> User:
        user = await self.user_gateway.get_by_email(email)
        if user is None:
            # Spend as long as a real check does, so response time does not reveal which emails exist.
            self.jwt_service.verify_dummy_password(password)
            raise InvalidCredentialsError
        if not self.jwt_service.verify_password(password, user.password_hash):
            raise InvalidCredentialsError
        if not user.is_active:
            raise UserNotActiveError
        return user

    async def _issue_refresh_token(self, user: User) -> RefreshCookie:
        refresh_token = self.jwt_service.create_refresh_token(str(user.id))
        max_age = self.jwt_service.refresh_expire_seconds
        token = RefreshToken(
            user_id=user.id,
            token_hash=self.jwt_service.hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=max_age),
        )
        await self.uow.add(token)
        return RefreshCookie(token=refresh_token, max_age=max_age)

    async def _issue_token_pair(self, user: User) -> tuple[UserAndAccessTokenResult, RefreshCookie]:
        cookie = await self._issue_refresh_token(user)
        response = UserAndAccessTokenResult(
            accessToken=self.jwt_service.create_access_token(str(user.id)),
            expiresIn=self.jwt_service.access_expire_seconds,
            user=to_user_result(user),
        )
        return response, cookie


class RegisterUser(_AuthContext):
    async def __call__(self, user_data: UserRegisterData) -> tuple[UserAndAccessTokenResult, RefreshCookie]:
        if await self.user_gateway.get_by_email(user_data.email) is not None:
            raise UserAlreadyExistsError(email=user_data.email)
        user = User(
            email=user_data.email,
            password_hash=self.jwt_service.get_password_hash(user_data.password),
            full_name=user_data.fullName,
            role=UserRole.USER,
            is_active=True,
        )
        user.created_by = user.id
        await self.uow.add(user)
        result = await self._issue_token_pair(user)
        try:
            await self.uow.commit()
        except DuplicateError:
            raise UserAlreadyExistsError(email=user_data.email) from None
        return result


class LoginUser(_AuthContext):
    async def __call__(self, login_data: UserLoginData) -> tuple[UserAndAccessTokenResult, RefreshCookie]:
        user = await self._authenticate_user(login_data.email, login_data.password)
        result = await self._issue_token_pair(user)
        await self.uow.commit()
        return result


class RefreshTokens(_AuthContext):
    """Rotation: the presented refresh token is deleted and a new pair is issued."""

    async def __call__(self, raw_refresh_token: str) -> tuple[AccessTokenResult, RefreshCookie]:
        payload = self.jwt_service.decode_token(raw_refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        user_id = _subject(payload)
        stored = await self.refresh_token_gateway.get_by_user_and_hash(
            user_id, self.jwt_service.hash_token(raw_refresh_token)
        )
        if stored is None or stored.expires_at <= datetime.now(UTC):
            raise InvalidCredentialsError
        user = await self.user_gateway.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        await self.uow.delete(stored)
        cookie = await self._issue_refresh_token(user)
        response = AccessTokenResult(
            accessToken=self.jwt_service.create_access_token(str(user.id)),
            expiresIn=self.jwt_service.access_expire_seconds,
        )
        await self.uow.commit()
        return response, cookie


class Logout(_AuthContext):
    async def __call__(self, raw_refresh_token: str) -> None:
        stored = await self.refresh_token_gateway.get_by_hash(self.jwt_service.hash_token(raw_refresh_token))
        if stored is not None:
            await self.uow.delete(stored)
        await self.uow.commit()


class VerifyAccessToken(_AuthContext):
    async def __call__(self, access_token: str) -> UserData:
        payload = self.jwt_service.decode_token(access_token, expected_type=ACCESS_TOKEN_TYPE)
        user = await self.user_gateway.get_by_id(_subject(payload))
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        return UserData(
            id=user.id,
            email=user.email,
            fullName=user.full_name,
            role=user.role,
            isActive=user.is_active,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
            createdBy=user.created_by or user.id,
        )
