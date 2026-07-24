from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.uow import UnitOfWorkDep
from app.services import ReviewService


def get_review_service(uow: UnitOfWorkDep) -> ReviewService:
    return ReviewService(uow)


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
