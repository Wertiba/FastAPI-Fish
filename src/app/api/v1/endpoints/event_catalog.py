from fastapi import APIRouter, status

from app.api.v1.dependencies import AdminUserDep, AnyViewUserDep, EventServiceDep, PaginationDep
from app.core.schemas.event import EventCreateBody, EventReadResponse
from app.core.utils import Page

router = APIRouter(prefix="/event-catalog", tags=["Event Catalog"])


@router.post("", response_model=EventReadResponse, status_code=status.HTTP_201_CREATED)
async def create(user_data: AdminUserDep, event_service: EventServiceDep,
                 event_data: EventCreateBody) -> EventReadResponse | None:
    return await event_service.create(user_data, event_data)


@router.get("", response_model=Page[EventReadResponse], status_code=status.HTTP_200_OK)
async def get_all(_: AnyViewUserDep, event_service: EventServiceDep,
                  pagination: PaginationDep) -> Page[EventReadResponse]:
    return await event_service.get_all_catalog_events(pagination)


@router.get("/{code}", response_model=EventReadResponse, status_code=status.HTTP_200_OK)
async def get_current(_: AnyViewUserDep, code: str, event_service: EventServiceDep) -> EventReadResponse | None:
    return await event_service.get_by_code(code)
