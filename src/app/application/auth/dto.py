from dataclasses import dataclass

from app.domain.users.entity import User


@dataclass(kw_only=True)
class AccessTokenResult:
    access_token: str
    expires_in: int


@dataclass(kw_only=True)
class AuthResult(AccessTokenResult):
    user: User


@dataclass(kw_only=True)
class RefreshCookie:
    """Raw refresh token for the HttpOnly cookie; it never reaches the response body."""

    token: str
    max_age: int
