from fastapi import Response

from app.infra.config import HttpConfig

REFRESH_COOKIE_NAME = "refreshToken"


def set_refresh_cookie(response: Response, refresh_token: str, max_age_seconds: int, *, config: HttpConfig) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age_seconds,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        path="/",
    )


def delete_refresh_cookie(response: Response, *, config: HttpConfig) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
    )
