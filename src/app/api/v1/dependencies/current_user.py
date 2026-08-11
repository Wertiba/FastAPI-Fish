from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.api.v1.dependencies.services.auth_service import AuthServiceDep
from app.core.exceptions.user_exs import ForbiddenError, InvalidCredentialsError
from app.core.schemas.user import UserData, UserRole


async def get_current_user(request: Request, auth_service: AuthServiceDep) -> UserData:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise InvalidCredentialsError
    token = auth_header.split(" ", 1)[1]
    return await auth_service.verify_access_token(token)


CurrentUserDep = Annotated[UserData, Depends(get_current_user)]


async def get_admin_user(current_user: CurrentUserDep) -> UserData:  # noqa: RUF029
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError
    return current_user


async def get_admin_or_self_user(user_id: UUID, current_user: CurrentUserDep) -> UserData:  # noqa: RUF029
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise ForbiddenError
    return current_user


AdminUserDep = Annotated[UserData, Depends(get_admin_user)]
AdminOrSelfDep = Annotated[UserData, Depends(get_admin_or_self_user)]
