from fastapi import APIRouter, status

from app.api.v1.dependencies import AdminUserDep, AnyViewUserDep, FlagServiceDep, PaginationDep
from app.core.schemas.flag import FlagCreateBody, FlagReadResponse, FlagUpdateBody
from app.core.utils import Page
from app.infrastructure.models import Flag

router = APIRouter(prefix="/flags", tags=["Flags"])


@router.get("", response_model=Page[FlagReadResponse], status_code=status.HTTP_200_OK)
async def get_all(_: AnyViewUserDep, flag_service: FlagServiceDep, pagination: PaginationDep) -> Page[Flag]:
    return await flag_service.get_all_flags(pagination)


@router.post("", response_model=FlagReadResponse, status_code=status.HTTP_201_CREATED)
async def create(user_data: AdminUserDep, flag_service: FlagServiceDep, flag_data: FlagCreateBody) -> Flag | None:
    return await flag_service.create(user_data, flag_data)


@router.get("/{code}", response_model=FlagReadResponse, status_code=status.HTTP_200_OK)
async def get_current(_: AnyViewUserDep, code: str, flag_service: FlagServiceDep) -> Flag | None:
    return await flag_service.get_by_code(code)


@router.patch("/{code}", response_model=FlagReadResponse, status_code=status.HTTP_200_OK)
async def update_current(
    _: AdminUserDep, code: str, flag_service: FlagServiceDep, new_data: FlagUpdateBody
) -> Flag | None:
    return await flag_service.update(code, new_data)
