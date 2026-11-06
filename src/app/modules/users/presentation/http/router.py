"""Function names are the operationId/summary in OpenAPI: they are part of the API contract."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.users.application.dto import UserCreateData, UserUpdateData
from app.modules.users.application.interactors import CreateUser, DeactivateUser, GetMe, GetUser, ListUsers, UpdateUser
from app.modules.users.application.ports import UserCriteria
from app.modules.users.domain.enums import UserRole
from app.modules.users.presentation.http.schemas import AdminRegisterUserBody, UserReadResponse, UserUpdateBody
from app.shared.application.pagination import Pagination
from app.shared.infra.metrics import track
from app.shared.presentation.http.dependencies import CurrentUserDep, PaginationDep
from app.shared.presentation.http.paginated import Page

router = APIRouter(prefix="/users", tags=["Users"], route_class=DishkaRoute)


def get_user_criteria(
    email: str | None = Query(None),
    fullName: str | None = Query(None),
    role: UserRole | None = Query(None),
    isActive: bool | None = Query(None),
    createdFrom: datetime | None = Query(None),
    createdTo: datetime | None = Query(None),
) -> UserCriteria:
    return UserCriteria(
        email=email,
        full_name=fullName,
        role=role,
        is_active=isActive,
        created_from=createdFrom,
        created_to=createdTo,
    )


@router.get("", response_model=Page[UserReadResponse], status_code=status.HTTP_200_OK)
async def get_all(
    user: CurrentUserDep,
    interactor: FromDishka[ListUsers],
    pagination: PaginationDep,
    criteria: Annotated[UserCriteria, Depends(get_user_criteria)],
) -> Page[UserReadResponse]:
    # Admin only. Active users first, newest first.
    page = await interactor(user.id, Pagination(page=pagination.page, size=pagination.size), criteria)
    return Page[UserReadResponse].model_validate(page, from_attributes=True)


@router.post("", response_model=UserReadResponse, status_code=status.HTTP_201_CREATED)
async def create(
    user: CurrentUserDep, interactor: FromDishka[CreateUser], user_data: AdminRegisterUserBody, response: Response
) -> UserReadResponse:
    created = await interactor(user.id, UserCreateData(**user_data.model_dump()))
    track("user", "created")
    response.headers["Location"] = f"/api/v1/users/{created.id}"
    return UserReadResponse.model_validate(created, from_attributes=True)


@router.get("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_me(user: CurrentUserDep, interactor: FromDishka[GetMe]) -> UserReadResponse:
    return UserReadResponse.model_validate(await interactor(user.id), from_attributes=True)


@router.put("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_me(
    user: CurrentUserDep, interactor: FromDishka[UpdateUser], new_data: UserUpdateBody
) -> UserReadResponse:
    updated = await interactor(user.id, user.id, UserUpdateData(**new_data.model_dump()))
    return UserReadResponse.model_validate(updated, from_attributes=True)


@router.get("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_by_id(user: CurrentUserDep, user_id: UUID, interactor: FromDishka[GetUser]) -> UserReadResponse:
    return UserReadResponse.model_validate(await interactor(user.id, user_id), from_attributes=True)


@router.put("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_by_id(
    user: CurrentUserDep, user_id: UUID, interactor: FromDishka[UpdateUser], new_data: UserUpdateBody
) -> UserReadResponse:
    updated = await interactor(user.id, user_id, UserUpdateData(**new_data.model_dump()))
    return UserReadResponse.model_validate(updated, from_attributes=True)


@router.delete("/{user_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_by_id(user: CurrentUserDep, user_id: UUID, interactor: FromDishka[DeactivateUser]) -> None:
    # The user is deactivated, not deleted, and loses every session.
    await interactor(user.id, user_id)
    track("user", "deactivated")
