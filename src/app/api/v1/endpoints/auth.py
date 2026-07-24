from fastapi import APIRouter, Response, status

from app.api.v1.dependencies import AuthServiceDep
from app.api.v1.utils import set_auth_cookies
from app.core.schemas.user import UserLoginBody, UserWithTokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=UserWithTokenResponse, status_code=status.HTTP_200_OK)
async def login(
    auth_service: AuthServiceDep,
    user_data: UserLoginBody,
    response: Response,
) -> UserWithTokenResponse:
    result = await auth_service.login_user(user_data)
    set_auth_cookies(response, access_token=result.accessToken)
    return result
