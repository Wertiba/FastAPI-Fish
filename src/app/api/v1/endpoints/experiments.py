from fastapi import APIRouter, Query, status

from app.api.v1.dependencies import (
    AnyViewUserDep,
    ExperimenterUserDep,
    ExperimentServiceDep,
    PaginationDep,
)
from app.core.schemas.experiment import (
    ExperimentCreateBody,
    ExperimentGuardrailsResponse,
    ExperimentHistoryResponse,
    ExperimentReadResponse,
    ExperimentSetCompletedSatusBody,
    ExperimentSetStatusBody,
    ExperimentUpdateBody,
)
from app.core.utils import Page

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.post("", response_model=ExperimentReadResponse, status_code=status.HTTP_201_CREATED)
async def create(user_data: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                 experiment_data: ExperimentCreateBody) -> ExperimentReadResponse | None:
    return await experiment_service.create_new(user_data, experiment_data)


@router.get("", response_model=Page[ExperimentReadResponse], status_code=status.HTTP_200_OK)
async def get_all(_: AnyViewUserDep, experiment_service: ExperimentServiceDep,
                  pagination: PaginationDep) -> Page[ExperimentReadResponse]:
    return await experiment_service.get_all_experiments(pagination)


@router.get("/{code}", response_model=ExperimentReadResponse, status_code=status.HTTP_200_OK)
async def get_current(_: AnyViewUserDep, code: str, experiment_service: ExperimentServiceDep,
                      version: float | None = Query(default=None)) -> ExperimentReadResponse | None:
    return await experiment_service.get_by_code(code, version)


@router.get("/history/{code}", response_model=ExperimentHistoryResponse, status_code=status.HTTP_200_OK)
async def get_history(_: AnyViewUserDep, code: str,
                      experiment_service: ExperimentServiceDep) -> ExperimentHistoryResponse | None:
    return await experiment_service.get_history(code)


@router.get("/guardrails/{code}", response_model=ExperimentGuardrailsResponse, status_code=status.HTTP_200_OK)
async def get_guardrails(_: AnyViewUserDep, code: str,
                      experiment_service: ExperimentServiceDep) -> ExperimentGuardrailsResponse | None:
    return await experiment_service.get_guardrails(code)


@router.put("/{code}", response_model=ExperimentReadResponse, status_code=status.HTTP_200_OK)
async def update_current(user_data: ExperimenterUserDep, code: str, experiment_service: ExperimentServiceDep,
                      experiment_data: ExperimentUpdateBody) -> ExperimentReadResponse | None:
    return await experiment_service.update(code, user_data, experiment_data)


@router.post("/status/review", response_model=ExperimentReadResponse, status_code=status.HTTP_202_ACCEPTED)
async def to_review(_: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                    data: ExperimentSetStatusBody) -> ExperimentReadResponse | None:
    return await experiment_service.set_status_review(data.code)


@router.post("/status/draft", response_model=ExperimentReadResponse, status_code=status.HTTP_202_ACCEPTED)
async def to_draft(_: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                    data: ExperimentSetStatusBody) -> ExperimentReadResponse | None:
    return await experiment_service.set_status_draft(data.code)


@router.post("/status/stop-review", response_model=ExperimentReadResponse, status_code=status.HTTP_202_ACCEPTED)
async def stop_review(_: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                    data: ExperimentSetStatusBody) -> ExperimentReadResponse | None:
    return await experiment_service.stop_review(data.code)


@router.post("/status/running", response_model=ExperimentReadResponse, status_code=status.HTTP_202_ACCEPTED)
async def to_running(_: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                    data: ExperimentSetStatusBody) -> ExperimentReadResponse | None:
    return await experiment_service.set_status_running(data.code)


@router.post("/status/paused", response_model=ExperimentReadResponse, status_code=status.HTTP_202_ACCEPTED)
async def to_paused(_: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                    data: ExperimentSetStatusBody) -> ExperimentReadResponse | None:
    return await experiment_service.set_status_paused(data.code)


@router.post("/status/completed", response_model=ExperimentReadResponse, status_code=status.HTTP_202_ACCEPTED)
async def to_completed(_: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                    data: ExperimentSetCompletedSatusBody) -> ExperimentReadResponse | None:
    return await experiment_service.set_status_completed(data.code, data.result, data.comment)


@router.post("/status/archived", response_model=ExperimentReadResponse, status_code=status.HTTP_202_ACCEPTED)
async def to_archived(_: ExperimenterUserDep, experiment_service: ExperimentServiceDep,
                    data: ExperimentSetStatusBody) -> ExperimentReadResponse | None:
    return await experiment_service.set_status_archived(data.code)
