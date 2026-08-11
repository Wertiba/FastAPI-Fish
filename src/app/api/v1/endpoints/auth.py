from fastapi import APIRouter, Request, Response, status

from app.api.v1.dependencies import AuthServiceDep
from app.api.v1.utils.cookies import REFRESH_COOKIE_NAME, delete_refresh_cookie, set_refresh_cookie
from app.core.exceptions.user_exs import InvalidCredentialsError
from app.core.schemas.token import AccessTokenResponse
from app.core.schemas.user import UserAndAccessTokenResponse, UserLoginBody, UserRegisterBody

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    auth_service: AuthServiceDep,
    user_data: UserRegisterBody,
    response: Response,
) -> UserAndAccessTokenResponse:
    result, refresh_token, max_age = await auth_service.register(user_data)
    set_refresh_cookie(response, refresh_token, max_age_seconds=max_age)
    response.headers["Location"] = f"/api/v1/users/{result.user.id}"
    return result


@router.post("/login", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_200_OK)
async def login(
    auth_service: AuthServiceDep,
    user_data: UserLoginBody,
    response: Response,
) -> UserAndAccessTokenResponse:
    result, refresh_token, max_age = await auth_service.login_user(user_data)
    set_refresh_cookie(response, refresh_token, max_age_seconds=max_age)
    return result


@router.post("/refresh", response_model=AccessTokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
) -> AccessTokenResponse:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise InvalidCredentialsError

    result, new_refresh_token, max_age = await auth_service.refresh_tokens(raw_refresh_token)
    set_refresh_cookie(response, new_refresh_token, max_age_seconds=max_age)
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
) -> None:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise InvalidCredentialsError
    await auth_service.logout(raw_refresh_token)
    delete_refresh_cookie(response)
