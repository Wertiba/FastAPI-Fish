"""Имена схем совпадают с FastAPI-Fish: в OpenAPI это имена компонент для кодогенерации на фронте."""

from app.modules.auth.application.commands import AuthSession, IssuedTokens
from app.modules.users.public import UserReadResponse
from app.shared.presentation.fields import Email, FullName, Password
from app.shared.presentation.schemas import CamelModel


class UserRegisterBody(CamelModel):
    email: Email
    password: Password
    full_name: FullName


class UserLoginBody(CamelModel):
    email: str
    password: str


class AccessTokenResponse(CamelModel):
    access_token: str
    expires_in: int

    @classmethod
    def from_tokens(cls, tokens: IssuedTokens) -> "AccessTokenResponse":
        return cls(access_token=tokens.access_token, expires_in=tokens.access_expires_in)


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse

    @classmethod
    def from_session(cls, session: AuthSession) -> "UserAndAccessTokenResponse":
        return cls(
            access_token=session.tokens.access_token,
            expires_in=session.tokens.access_expires_in,
            user=UserReadResponse.model_validate(session.user),
        )
