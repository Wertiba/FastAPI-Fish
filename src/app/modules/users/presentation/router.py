"""Имена функций = operationId/summary в OpenAPI, совпадают с FastAPI-Fish."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from app.modules.users.application.commands import CreateUser, DeactivateUser, UpdateUser
from app.modules.users.application.ports import UserFilter
from app.modules.users.application.queries import GetCurrentUser, GetUser, ListUsers
from app.modules.users.presentation.schemas import AdminRegisterUserBody, UserReadResponse, UserUpdateBody
from app.shared.application.identity import IdentityProvider
from app.shared.domain.identity import UserRole
from app.shared.presentation.dependencies import PaginationQuery
from app.shared.presentation.schemas import Page

router = APIRouter(prefix="/users", tags=["Users"], route_class=DishkaRoute)


def _user_filters(
    email: str | None = Query(None),
    full_name: str | None = Query(None, alias="fullName"),
    role: UserRole | None = Query(None),
    is_active: bool | None = Query(None, alias="isActive"),
    created_from: datetime | None = Query(None, alias="createdFrom"),
    created_to: datetime | None = Query(None, alias="createdTo"),
) -> UserFilter:
    return UserFilter(
        email=email,
        full_name=full_name,
        role=role,
        is_active=is_active,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("", response_model=Page[UserReadResponse], status_code=status.HTTP_200_OK)
async def get_all(
    list_users: FromDishka[ListUsers],
    pagination: PaginationQuery,
    filters: Annotated[UserFilter, Depends(_user_filters)],
) -> Page[UserReadResponse]:
    page = await list_users(filters, pagination)
    return Page[UserReadResponse].from_page(page, UserReadResponse.model_validate)


@router.post("", response_model=UserReadResponse, status_code=status.HTTP_201_CREATED)
async def create(user_data: AdminRegisterUserBody, create_user: FromDishka[CreateUser]) -> UserReadResponse:
    user = await create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=user_data.is_active,
    )
    return UserReadResponse.model_validate(user)


@router.get("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_me(get_current_user: FromDishka[GetCurrentUser]) -> UserReadResponse:
    return UserReadResponse.model_validate(await get_current_user())


@router.put("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_me(
    new_data: UserUpdateBody,
    idp: FromDishka[IdentityProvider],
    update_user: FromDishka[UpdateUser],
) -> UserReadResponse:
    identity = await idp.get_identity()
    user = await update_user(
        identity.user_id, full_name=new_data.full_name, role=new_data.role, is_active=new_data.is_active
    )
    return UserReadResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_by_id(user_id: UUID, get_user: FromDishka[GetUser]) -> UserReadResponse:
    return UserReadResponse.model_validate(await get_user(user_id))


@router.put("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_by_id(
    user_id: UUID, new_data: UserUpdateBody, update_user: FromDishka[UpdateUser]
) -> UserReadResponse:
    user = await update_user(
        user_id, full_name=new_data.full_name, role=new_data.role, is_active=new_data.is_active
    )
    return UserReadResponse.model_validate(user)


@router.delete("/{user_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_by_id(user_id: UUID, deactivate_user: FromDishka[DeactivateUser]) -> None:
    await deactivate_user(user_id)
