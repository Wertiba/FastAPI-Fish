from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.uow import UnitOfWorkDep
from app.services import ExperimentService


def get_experiment_service(uow: UnitOfWorkDep) -> ExperimentService:
    return ExperimentService(uow)


ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]
