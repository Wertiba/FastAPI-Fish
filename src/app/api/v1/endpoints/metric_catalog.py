from fastapi import APIRouter, status

from app.api.v1.dependencies import AdminUserDep, AnyViewUserDep, MetricServiceDep, PaginationDep
from app.core.schemas.metric import MetricAssignBody, MetricAssignResponse, MetricCreateBody, MetricReadResponse
from app.core.utils import Page

router = APIRouter(prefix="/metric-catalog", tags=["Metric Catalog"])


@router.post("", response_model=MetricReadResponse, status_code=status.HTTP_201_CREATED)
async def create(user_data: AdminUserDep, metric_service: MetricServiceDep,
                 metric_data: MetricCreateBody) -> MetricReadResponse | None:
    return await metric_service.create(user_data, metric_data)


@router.get("", response_model=Page[MetricReadResponse], status_code=status.HTTP_200_OK)
async def get_all(_: AnyViewUserDep, metric_service: MetricServiceDep,
                  pagination: PaginationDep) -> Page[MetricReadResponse]:
    return await metric_service.get_all_catalog_metrics(pagination)


@router.get("/{code}", response_model=MetricReadResponse, status_code=status.HTTP_200_OK)
async def get_current(_: AnyViewUserDep, code: str, metric_service: MetricServiceDep) -> MetricReadResponse | None:
    return await metric_service.get_by_code(code)


@router.post("/assign", response_model=MetricAssignResponse, status_code=status.HTTP_201_CREATED)
async def assign_event_catalog(_: AdminUserDep, metric_service: MetricServiceDep,
                               assign_data: MetricAssignBody) -> MetricAssignResponse | None:
    return await metric_service.assign(assign_data)
