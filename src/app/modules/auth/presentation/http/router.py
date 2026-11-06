"""Function names are the operationId/summary in OpenAPI: they are part of the API contract.

The refresh cookie is read from ``Request`` rather than ``Cookie(...)`` so it does not show up
in OpenAPI as a parameter; the browser sends it anyway.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response, status

from app.modules.auth.application.dto import LoginData, RegisterData
from app.modules.auth.application.interactors import LoginUser, Logout, RefreshTokens, RegisterUser
from app.modules.auth.presentation.http.cookies import REFRESH_COOKIE_NAME, delete_refresh_cookie, set_refresh_cookie
from app.modules.auth.presentation.http.schemas import (
    AccessTokenResponse,
    UserAndAccessTokenResponse,
    UserLoginBody,
    UserRegisterBody,
)
from app.shared.domain.errors import InvalidCredentialsError
from app.shared.infra.config import HttpConfig
from app.shared.infra.metrics import track

router = APIRouter(prefix="/auth", tags=["Auth"], route_class=DishkaRoute)


@router.post("/register", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    interactor: FromDishka[RegisterUser],
    config: FromDishka[HttpConfig],
    user_data: UserRegisterBody,
    response: Response,
) -> UserAndAccessTokenResponse:
    result, cookie = await interactor(RegisterData(**user_data.model_dump()))
    track("user", "registered")
    set_refresh_cookie(response, cookie.token, max_age_seconds=cookie.max_age, config=config)
    response.headers["Location"] = f"/api/v1/users/{result.user.id}"
    return UserAndAccessTokenResponse.model_validate(result, from_attributes=True)


@router.post("/login", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_200_OK)
async def login(
    interactor: FromDishka[LoginUser], config: FromDishka[HttpConfig], user_data: UserLoginBody, response: Response
) -> UserAndAccessTokenResponse:
    try:
        result, cookie = await interactor(LoginData(**user_data.model_dump()))
    except InvalidCredentialsError:
        track("user", "login_failed")
        raise
    track("user", "logged_in")
    set_refresh_cookie(response, cookie.token, max_age_seconds=cookie.max_age, config=config)
    return UserAndAccessTokenResponse.model_validate(result, from_attributes=True)


@router.post("/refresh", response_model=AccessTokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    interactor: FromDishka[RefreshTokens], config: FromDishka[HttpConfig], request: Request, response: Response
) -> AccessTokenResponse:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise InvalidCredentialsError
    result, cookie = await interactor(raw_refresh_token)
    set_refresh_cookie(response, cookie.token, max_age_seconds=cookie.max_age, config=config)
    return AccessTokenResponse.model_validate(result, from_attributes=True)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    interactor: FromDishka[Logout], config: FromDishka[HttpConfig], request: Request, response: Response
) -> None:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise InvalidCredentialsError
    await interactor(raw_refresh_token)
    delete_refresh_cookie(response, config=config)
