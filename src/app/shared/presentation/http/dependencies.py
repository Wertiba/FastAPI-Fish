from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Depends, Query, Request

from app.shared.application.ports.identity import CurrentUser, IdentityProvider
from app.shared.domain.errors import InvalidCredentialsError
from app.shared.presentation.http.paginated import PaginationParams


@inject
async def get_current_user(request: Request, identity: FromDishka[IdentityProvider]) -> CurrentUser:
    """``Authorization: Bearer <access token>`` -> the active user, or 401."""
    scheme, _, access_token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not access_token:
        raise InvalidCredentialsError
    return await identity.authenticate(access_token)


def get_pagination(
    page: int = Query(0, ge=0, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
) -> PaginationParams:
    return PaginationParams(page=page, size=size)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]
