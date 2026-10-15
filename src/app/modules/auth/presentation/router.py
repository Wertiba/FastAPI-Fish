"""Имена функций = operationId/summary в OpenAPI, совпадают с FastAPI-Fish.

Refresh-кука читается из ``Request``, а не через ``Cookie(...)``: так она не попадает
в OpenAPI как параметр (как и в Fish), а браузер всё равно шлёт её сам.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response, status

from app.modules.auth.application.commands import IssuedTokens, Login, Logout, RefreshSession, Register
from app.modules.auth.config import AuthConfig
from app.modules.auth.presentation.schemas import (
    AccessTokenResponse,
    UserAndAccessTokenResponse,
    UserLoginBody,
    UserRegisterBody,
)

REFRESH_COOKIE = "refreshToken"

router = APIRouter(prefix="/auth", tags=["Auth"], route_class=DishkaRoute)


def _set_refresh_cookie(response: Response, tokens: IssuedTokens, config: AuthConfig) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        max_age=tokens.refresh_expires_in,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterBody,
    response: Response,
    register_user: FromDishka[Register],
    config: FromDishka[AuthConfig],
) -> UserAndAccessTokenResponse:
    session = await register_user(
        email=user_data.email, password=user_data.password, full_name=user_data.full_name
    )
    _set_refresh_cookie(response, session.tokens, config)
    response.headers["Location"] = f"/api/v1/users/{session.user.id}"
    return UserAndAccessTokenResponse.from_session(session)


@router.post("/login", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_200_OK)
async def login(
    user_data: UserLoginBody,
    response: Response,
    login_user: FromDishka[Login],
    config: FromDishka[AuthConfig],
) -> UserAndAccessTokenResponse:
    session = await login_user(email=user_data.email, password=user_data.password)
    _set_refresh_cookie(response, session.tokens, config)
    return UserAndAccessTokenResponse.from_session(session)


@router.post("/refresh", response_model=AccessTokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    request: Request,
    response: Response,
    refresh_session: FromDishka[RefreshSession],
    config: FromDishka[AuthConfig],
) -> AccessTokenResponse:
    tokens = await refresh_session(request.cookies.get(REFRESH_COOKIE))
    _set_refresh_cookie(response, tokens, config)
    return AccessTokenResponse.from_tokens(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    logout_user: FromDishka[Logout],
    config: FromDishka[AuthConfig],
) -> None:
    await logout_user(request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(
        REFRESH_COOKIE, path="/", httponly=True, secure=config.cookie_secure, samesite="lax"
    )
