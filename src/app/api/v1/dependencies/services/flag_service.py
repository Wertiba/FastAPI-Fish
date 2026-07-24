from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.uow import UnitOfWorkDep
from app.services import FlagService


def get_flag_service(uow: UnitOfWorkDep) -> FlagService:
    return FlagService(uow)


FlagServiceDep = Annotated[FlagService, Depends(get_flag_service)]
