from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.dependencies import AdminUserDep, CurrentUserDep, PaginationDep, UserServiceDep
from app.core.schemas.user import (
    UserCreateBody,
    UserReadResponse,
    UserUpdateBody,
)
from app.core.utils import Page
from app.infrastructure.models import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserReadResponse], status_code=status.HTTP_200_OK)
async def get_all(_: AdminUserDep, user_service: UserServiceDep, pagination: PaginationDep) -> Page[UserReadResponse]:
    return await user_service.get_all_users(pagination)


@router.post("", response_model=UserReadResponse, status_code=status.HTTP_201_CREATED)
async def create(_: AdminUserDep, user_service: UserServiceDep, user_data: UserCreateBody) -> User | None:
    return await user_service.register(user_data)


@router.get("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_me(user: CurrentUserDep, user_service: UserServiceDep) -> UserReadResponse:
    return await user_service.get_current_by_id(user, user.id)


@router.put("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_me(user: CurrentUserDep, user_service: UserServiceDep, new_data: UserUpdateBody) -> User | None:
    return await user_service.update_by_id(user.id, new_data)


@router.get("/{id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_current(user: AdminUserDep, user_id: UUID, user_service: UserServiceDep) -> User | None:
    return await user_service.get_current_by_id(user, user_id)


@router.put("/{id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_current(
    _: AdminUserDep, user_id: UUID, user_service: UserServiceDep, new_data: UserUpdateBody
) -> User | None:
    return await user_service.update_by_id(user_id, new_data)


@router.delete("/{id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_current(_: AdminUserDep, user_id: UUID, user_service: UserServiceDep) -> None:
    return await user_service.deactivate_by_id(user_id)
