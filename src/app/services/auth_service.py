from typing import TYPE_CHECKING
from uuid import UUID

from app.core.exceptions.user_exs import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserNotActiveError,
    UserNotFoundError,
)
from app.core.schemas.role import RoleCode, RoleRead
from app.core.schemas.token import Token
from app.core.schemas.user import TokenData, UserLoginBody, UserReadResponse, UserWithTokenResponse
from app.infrastructure.models import User
from app.infrastructure.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from app.services import JWTService


class AuthService:
    def __init__(self, uow: UnitOfWork, jwt_service: "JWTService"):
        self.uow = uow
        self.jwt_service = jwt_service

    async def _authenticate_user(self, email: str, password: str) -> User:
        user = await self.uow.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundError
        if not self.jwt_service.verify_password(password, str(user.password)):
            raise InvalidPasswordError
        if not user.isActive:
            raise UserNotActiveError
        return user

    def _create_tokens_for_user(self, user: User) -> Token:
        data = {"sub": str(user.id)}
        access_token = self.jwt_service.create_access_token(data=data)
        return Token(accessToken=access_token)

    async def verify_token(self, token: str) -> TokenData:
        async with self.uow:
            payload = self.jwt_service.decode_token(token)
            user_id = UUID(payload["sub"])
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise InvalidCredentialsError
            return TokenData(
                **user.model_dump(exclude={"roles"}),
                token_type=payload.get("token_type"),
                roles=[r.code for r in user.roles]
            )

    async def login_user(self, login_body: UserLoginBody) -> UserWithTokenResponse:
        async with self.uow:
            user = await self._authenticate_user(login_body.email, login_body.password)
            tokens = self._create_tokens_for_user(user)

            return UserWithTokenResponse(
                user=UserReadResponse(
                    roles=[
                        RoleRead(
                            id=role.id,
                            code=RoleCode(role.code),
                            value=role.value,
                            description=role.description,
                        )
                        for role in user.roles
                    ],
                    **user.model_dump(exclude={"roles"}),
                ),
                **tokens.model_dump(),
            )
