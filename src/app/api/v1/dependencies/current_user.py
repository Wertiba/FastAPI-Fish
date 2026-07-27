from typing import Annotated

from fastapi import Depends, Request

from app.api.v1.dependencies.services.auth_service import AuthServiceDep
from app.core.exceptions.user_exs import ForbiddenError, InvalidCredentialsError
from app.core.schemas.user import TokenData, UserRole


async def get_current_user(request: Request, auth_service: AuthServiceDep) -> TokenData:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token:
        raise InvalidCredentialsError

    return await auth_service.verify_token(token)


CurrentUserDep = Annotated[TokenData, Depends(get_current_user)]


def _user_has_role(user: TokenData, role: UserRole) -> bool:
    return role == user.role


async def get_admin_user(current_user: CurrentUserDep) -> TokenData:  # noqa: RUF029
    if not _user_has_role(current_user, UserRole.ADMN):
        raise ForbiddenError
    return current_user


async def get_any_view(current_user: CurrentUserDep) -> TokenData:  # noqa: RUF029
    if not any([_user_has_role(current_user, r) for r in [UserRole.ADMN]]):
        raise ForbiddenError
    return current_user


AdminUserDep = Annotated[TokenData, Depends(get_admin_user)]
AnyViewUserDep = Annotated[TokenData, Depends(get_any_view)]
