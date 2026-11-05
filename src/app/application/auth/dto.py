from dataclasses import dataclass


@dataclass(kw_only=True)
class AccessTokenResult:
    accessToken: str
    expiresIn: int


@dataclass(kw_only=True)
class RefreshCookie:
    """Raw refresh token for the HttpOnly cookie; it never reaches the response body."""

    token: str
    max_age: int
