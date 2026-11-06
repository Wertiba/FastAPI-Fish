from dataclasses import dataclass

from app.modules.users.api.contracts import UserInfo


@dataclass(kw_only=True)
class RegisterData:
    email: str
    password: str
    fullName: str


@dataclass(kw_only=True)
class LoginData:
    email: str
    password: str


@dataclass(kw_only=True)
class AccessTokenResult:
    accessToken: str
    expiresIn: int


@dataclass(kw_only=True)
class UserAndAccessTokenResult(AccessTokenResult):
    user: UserInfo


@dataclass(kw_only=True)
class RefreshCookie:
    """Raw refresh token for the HttpOnly cookie; it never reaches the response body."""

    token: str
    max_age: int
