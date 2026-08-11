from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.dependencies import (
    AdminOrSelfDep,
    AdminUserDep,
    CurrentUserDep,
    PaginationDep,
    UserFilterDep,
    UserServiceDep,
)
from app.core.schemas.user import AdminRegisterUserBody, UserReadResponse, UserUpdateBody
from app.core.utils import Page

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserReadResponse], status_code=status.HTTP_200_OK)
async def get_all(
    _: AdminUserDep,
    user_service: UserServiceDep,
    pagination: PaginationDep,
    filters: UserFilterDep,
) -> Page[UserReadResponse]:
    return await user_service.get_all_users(pagination, filters)


@router.post("", response_model=UserReadResponse, status_code=status.HTTP_201_CREATED)
async def create(_: AdminUserDep, user_service: UserServiceDep, user_data: AdminRegisterUserBody) -> UserReadResponse:
    return await user_service.create_user(user_data)


@router.get("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_me(user: CurrentUserDep, user_service: UserServiceDep) -> UserReadResponse:
    return await user_service.get_by_id(user.id)


@router.put("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_me(user: CurrentUserDep, user_service: UserServiceDep, new_data: UserUpdateBody) -> UserReadResponse:
    return await user_service.update_user(user.id, new_data, acting_user=user)


@router.get("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_by_id(_: AdminOrSelfDep, user_id: UUID, user_service: UserServiceDep) -> UserReadResponse:
    return await user_service.get_by_id(user_id)


@router.put("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_by_id(
    user: AdminOrSelfDep, user_id: UUID, user_service: UserServiceDep, new_data: UserUpdateBody
) -> UserReadResponse:
    return await user_service.update_user(user_id, new_data, acting_user=user)


@router.delete("/{user_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_by_id(_: AdminUserDep, user_id: UUID, user_service: UserServiceDep) -> None:
    await user_service.deactivate_by_id(user_id)
