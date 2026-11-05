from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Depends, Request

from app.application.auth.interactors import VerifyAccessToken
from app.application.users.dto import UserData
from app.domain.users.errors import InvalidCredentialsError


@inject
async def get_current_user(request: Request, verify: FromDishka[VerifyAccessToken]) -> UserData:
    """``Authorization: Bearer <access token>`` -> the active user, or 401."""
    scheme, _, access_token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not access_token:
        raise InvalidCredentialsError
    return await verify(access_token)


CurrentUserDep = Annotated[UserData, Depends(get_current_user)]
