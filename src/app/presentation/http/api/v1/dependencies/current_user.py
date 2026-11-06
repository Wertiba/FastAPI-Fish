from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Depends, Request

from app.application.auth.interactors import VerifyAccessToken
from app.domain.users.entity import User
from app.domain.users.errors import InvalidCredentialsError


@inject
async def get_current_user(request: Request, verify: FromDishka[VerifyAccessToken]) -> User:
    """``Authorization: Bearer <access token>`` -> the active user, or 401."""
    scheme, _, access_token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not access_token:
        raise InvalidCredentialsError
    return await verify(access_token)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
