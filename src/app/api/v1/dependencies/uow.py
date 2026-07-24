from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.session import SessionDep
from app.infrastructure.unit_of_work import UnitOfWork


def get_uow(session: SessionDep) -> UnitOfWork:
    return UnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_uow)]
