from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE_NAME = "refreshToken"


def set_refresh_cookie(response: Response, refresh_token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age_seconds,
        httponly=True,
        secure=bool(settings.APP_COOKIE_SECURE),
        samesite="lax",
        path="/",
    )


def delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=bool(settings.APP_COOKIE_SECURE),
        samesite="lax",
    )
