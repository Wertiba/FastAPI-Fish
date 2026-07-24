from fastapi import Response

from app.core.schemas.token import Token


def set_auth_cookies(response: Response, tokens: Token | None = None, access_token: str | None = None) -> None:
    if not access_token and not tokens:
        raise ValueError("Either access_token or tokens must be provided")

    response.set_cookie(
        key="access_token",
        value=access_token or tokens.accessToken,  # type: ignore[arg-type]
        httponly=True,
        path="/",
        samesite="lax",
        # secure=True,  # for https  # noqa: ERA001
    )


def delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
