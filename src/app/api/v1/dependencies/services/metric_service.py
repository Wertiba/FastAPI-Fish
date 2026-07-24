from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.uow import UnitOfWorkDep
from app.services import MetricService


def get_metric_service(uow: UnitOfWorkDep) -> MetricService:
    return MetricService(uow)


MetricServiceDep = Annotated[MetricService, Depends(get_metric_service)]
