from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.dependencies import AdminUserDep, AnyViewUserDep, CurrentUserDep, PaginationDep, UserServiceDep
from app.core.schemas.user import (
    ApproverAssignBody,
    ApproverReadResponse,
    UserCreateBody,
    UserReadResponse,
    UserUpdateBody,
)
from app.core.utils import Page
from app.infrastructure.models import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserReadResponse], status_code=status.HTTP_200_OK)
async def get_all(_: AdminUserDep, user_service: UserServiceDep, pagination: PaginationDep) -> Page[User]:
    return await user_service.get_all_users(pagination)


@router.post("", response_model=UserReadResponse, status_code=status.HTTP_201_CREATED)
async def create(_: AdminUserDep, user_service: UserServiceDep, user_data: UserCreateBody) -> User | None:
    return await user_service.register(user_data)


@router.get("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_me(user: CurrentUserDep, user_service: UserServiceDep) -> UserReadResponse:
    return await user_service.get_current_by_id(user, user.id)


@router.put("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_me(user: CurrentUserDep, user_service: UserServiceDep, new_data: UserUpdateBody) -> User | None:
    return await user_service.update_me(user, new_data)


@router.get("/{id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_current(user: CurrentUserDep, id: UUID, user_service: UserServiceDep) -> User | None:
    return await user_service.get_current_by_id(user, id)


@router.put("/{id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_current(
    user: CurrentUserDep, id: UUID, user_service: UserServiceDep, new_data: UserUpdateBody
) -> User | None:
    return await user_service.update_current(id, user, new_data)


@router.delete("/{id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_current(_: AdminUserDep, id: UUID, user_service: UserServiceDep) -> None:
    return await user_service.deactivate(id)


@router.post("/approvers", response_model=ApproverReadResponse, status_code=status.HTTP_200_OK)
async def assign_approver(user_data: AdminUserDep, user_service: UserServiceDep,
                          approver_data: ApproverAssignBody) -> User | None:
    return await user_service.assign_approver(user_data, approver_data)


@router.get("/approvers/{id}", response_model=ApproverReadResponse, status_code=status.HTTP_200_OK)
async def get_approver(_: AnyViewUserDep, user_service: UserServiceDep, id: UUID) -> User | None:
    return await user_service.get_approver(id)


@router.delete("/approvers/{id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_approver(_: AdminUserDep, user_service: UserServiceDep, id: UUID) -> None:
    return await user_service.del_approver(id)
