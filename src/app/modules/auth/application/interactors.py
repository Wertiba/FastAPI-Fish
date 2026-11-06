from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.modules.auth.application.dto import (
    AccessTokenResult,
    LoginData,
    RefreshCookie,
    RegisterData,
    UserAndAccessTokenResult,
)
from app.modules.auth.application.ports import REFRESH_TOKEN_TYPE, RefreshTokenGateway, TokenService
from app.modules.auth.domain.errors import UserNotActiveError
from app.modules.auth.domain.refresh_token import RefreshToken
from app.modules.users.api.contracts import UserAlreadyExistsError, UserInfo, UsersFacade
from app.shared.application.exceptions import DuplicateError
from app.shared.application.ports.unit_of_work import UnitOfWork
from app.shared.domain.errors import InvalidCredentialsError
from app.shared.domain.ids import UserId


def token_subject(payload: dict[str, Any]) -> UserId:
    try:
        return UUID(str(payload["sub"]))
    except (KeyError, ValueError):
        raise InvalidCredentialsError from None


@dataclass
class _AuthContext:
    uow: UnitOfWork
    users: UsersFacade
    refresh_token_gateway: RefreshTokenGateway
    tokens: TokenService

    async def _issue_refresh_token(self, user_id: UserId) -> RefreshCookie:
        refresh_token = self.tokens.create_refresh_token(str(user_id))
        max_age = self.tokens.refresh_expire_seconds
        token = RefreshToken(
            user_id=user_id,
            token_hash=self.tokens.hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=max_age),
        )
        await self.uow.add(token)
        return RefreshCookie(token=refresh_token, max_age=max_age)

    async def _issue_token_pair(self, user: UserInfo) -> tuple[UserAndAccessTokenResult, RefreshCookie]:
        cookie = await self._issue_refresh_token(user.id)
        response = UserAndAccessTokenResult(
            accessToken=self.tokens.create_access_token(str(user.id)),
            expiresIn=self.tokens.access_expire_seconds,
            user=user,
        )
        return response, cookie


class RegisterUser(_AuthContext):
    async def __call__(self, data: RegisterData) -> tuple[UserAndAccessTokenResult, RefreshCookie]:
        # ``users`` adds the user to the shared unit of work; the user and the session commit together.
        user = await self.users.register(email=data.email, password=data.password, full_name=data.fullName)
        result = await self._issue_token_pair(user)
        try:
            await self.uow.commit()
        except DuplicateError:
            raise UserAlreadyExistsError(email=data.email) from None
        return result


class LoginUser(_AuthContext):
    async def __call__(self, data: LoginData) -> tuple[UserAndAccessTokenResult, RefreshCookie]:
        user = await self.users.check_credentials(data.email, data.password)
        if user is None:
            raise InvalidCredentialsError
        if not user.isActive:
            raise UserNotActiveError
        result = await self._issue_token_pair(user)
        await self.uow.commit()
        return result


class RefreshTokens(_AuthContext):
    """Rotation: the presented refresh token is deleted and a new pair is issued."""

    async def __call__(self, raw_refresh_token: str) -> tuple[AccessTokenResult, RefreshCookie]:
        payload = self.tokens.decode_token(raw_refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        user_id = token_subject(payload)
        stored = await self.refresh_token_gateway.get_by_user_and_hash(
            user_id, self.tokens.hash_token(raw_refresh_token)
        )
        if stored is None or stored.expires_at <= datetime.now(UTC):
            raise InvalidCredentialsError
        user = await self.users.get(user_id)
        if user is None or not user.isActive:
            raise InvalidCredentialsError
        await self.uow.delete(stored)
        cookie = await self._issue_refresh_token(user.id)
        response = AccessTokenResult(
            accessToken=self.tokens.create_access_token(str(user.id)),
            expiresIn=self.tokens.access_expire_seconds,
        )
        await self.uow.commit()
        return response, cookie


class Logout(_AuthContext):
    async def __call__(self, raw_refresh_token: str) -> None:
        stored = await self.refresh_token_gateway.get_by_hash(self.tokens.hash_token(raw_refresh_token))
        if stored is not None:
            await self.uow.delete(stored)
        await self.uow.commit()
