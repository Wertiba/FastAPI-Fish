from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.uow import UnitOfWorkDep
from app.services import EventService


def get_event_service(uow: UnitOfWorkDep) -> EventService:
    return EventService(uow)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]
