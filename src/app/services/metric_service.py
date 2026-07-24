from app.core.exceptions.base import DuplicateError, RelationNotFoundError
from app.core.exceptions.metric_exs import MetricAlreadyExistsError, MetricNotFoundError
from app.core.schemas.metric import (
    MetricAssignBody,
    MetricAssignDataOut,
    MetricAssignResponse,
    MetricCreateBody,
    MetricReadResponse,
)
from app.core.schemas.user import TokenData
from app.core.utils.paginated import Page, PaginationParams
from app.infrastructure.models import MetricCatalog
from app.infrastructure.models.event import EventMetricLink
from app.infrastructure.unit_of_work import UnitOfWork


class MetricService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, user_data: TokenData, metric_data: MetricCreateBody) -> MetricReadResponse:
        async with self.uow:
            try:
                metric = await self.uow.metric_repo.add(MetricCatalog(**metric_data.model_dump(),
                                                                      createdBy=user_data.id))
                return MetricReadResponse(**metric.model_dump())
            except DuplicateError:
                raise MetricAlreadyExistsError from DuplicateError

    async def get_all_catalog_metrics(self, pagination: PaginationParams) -> Page[MetricReadResponse]:
        async with self.uow:
            metrics = await self.uow.metric_repo.get_paginated(offset=pagination.offset, limit=pagination.limit)
            valid = [MetricReadResponse(**u.model_dump()) for u in metrics]
            total = await self.uow.metric_repo.count()
            return Page.build(items=valid, total=total, pagination=pagination)

    async def get_by_code(self, code: str) -> MetricReadResponse | None:
        async with self.uow:
            metric_exists = await self.uow.metric_repo.get_by_code(code)
            if not metric_exists:
                raise MetricNotFoundError

            return MetricReadResponse(**metric_exists.model_dump())

    async def assign(self, data: MetricAssignBody) -> MetricAssignResponse:
        try:
            async with self.uow:
                items: list[MetricAssignDataOut] = []
                for assign_data in data.items:
                    assign = await self.uow.metric_repo.assign(EventMetricLink(
                        **assign_data.model_dump(),
                        metricCatalog_code=data.metricCatalog_code
                    ))
                    items.append(MetricAssignDataOut(**assign.model_dump()))

                return MetricAssignResponse(items=items)
        except RelationNotFoundError as e:
            raise MetricNotFoundError from e

    async def get_values(self, code: str) -> ...:
        pass
