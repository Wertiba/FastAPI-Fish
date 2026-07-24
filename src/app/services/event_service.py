from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import ValidationError

from app.core.exceptions.base import DuplicateError, RelationNotFoundError
from app.core.exceptions.event_exs import EventAlreadyExistsError, EventNotFoundError
from app.core.exceptions.experiment_exs import ExperimentInvalidStatusError, ExperimentNotFoundError
from app.core.schemas.event import (
    EventBatchBody,
    EventBatchResponse,
    EventCreateBody,
    EventErrorDetail,
    EventReadResponse,
    SendEventData,
)
from app.core.schemas.experiment import ExperimentStatus
from app.core.schemas.metric import GuardrailAction
from app.core.schemas.reports import ExperimentReportResponse, MetricReportItem, VariantReportItem
from app.core.schemas.user import TokenData
from app.core.utils.paginated import Page, PaginationParams
from app.infrastructure.models import Event, EventCatalog, GuardrailHistory, Metric
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.variant_service import VariantService


class EventService(VariantService):
    def __init__(self, uow: UnitOfWork):
        super().__init__(uow)

    @staticmethod
    def _format_validation_error(e: ValidationError) -> str:
        errors = []
        for err in e.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            errors.append(f"{field}: {msg}" if field else msg)
        return "; ".join(errors)

    async def _check_guardrails(self, experiment_id: UUID) -> None:
        guardrails = await self.uow.metric_repo.get_guardrails(experiment_id)
        if not guardrails:
            return

        for guardrail in guardrails:
            links = await self.uow.metric_repo.get_event_metric_link(guardrail.metricCatalog_code)
            if not links:
                continue

            event_codes = [l.eventCatalog_code for l in links]
            time_from = datetime.now(tz=UTC) - timedelta(seconds=guardrail.window or 864000)

            events = await self.uow.event_repo.get_by_experiment_and_event_codes(
                experiment_id=experiment_id,
                event_codes=event_codes,
                time_from=time_from,
            )

            value = self._calculate(guardrail.metric_catalog, links, events)

            if guardrail.threshold is not None and value >= guardrail.threshold:
                await self._trigger_guardrail(guardrail, value, experiment_id)

    async def _trigger_guardrail(self, guardrail: Metric, actual_value: float, experiment_id: UUID) -> None:
        experiment = await self.uow.experiment_repo.get_by_id_with_variants(experiment_id)

        if guardrail.action_code == GuardrailAction.PAUSE:
            experiment.status = ExperimentStatus.PAUSED
        elif guardrail.action_code == GuardrailAction.ROLLBACK:
            experiment.status = ExperimentStatus.ROLLBACK

        await self.uow.metric_repo.add_history(GuardrailHistory(
            metric_id=guardrail.id,
            history={
                "metric_code": guardrail.metricCatalog_code,
                "threshold": guardrail.threshold,
                "actual_value": actual_value,
                "action": guardrail.action_code,
                "window": guardrail.window,
                "triggered_at": datetime.now(tz=UTC).isoformat(),
            }
        ))

    async def create(self, user_data: TokenData, event_data: EventCreateBody) -> EventReadResponse:
        async with self.uow:
            try:
                metric = await self.uow.event_repo.add(EventCatalog(**event_data.model_dump(),
                                                                      createdBy=user_data.id))
                return EventReadResponse(**metric.model_dump())
            except DuplicateError:
                raise EventAlreadyExistsError from DuplicateError

    async def get_all_catalog_events(self, pagination: PaginationParams) -> Page[EventReadResponse]:
        async with self.uow:
            events = await self.uow.event_repo.get_paginated(offset=pagination.offset, limit=pagination.limit)
            valid = [EventReadResponse(**u.model_dump()) for u in events]
            total = await self.uow.event_repo.count()
            return Page.build(items=valid, total=total, pagination=pagination)

    async def get_by_code(self, code: str) -> EventReadResponse | None:
        async with self.uow:
            event_exists = await self.uow.event_repo.get_by_code(code)
            if not event_exists:
                raise EventNotFoundError

            return EventReadResponse(**event_exists.model_dump())

    async def process_batch(self, batch: EventBatchBody) -> EventBatchResponse:
        exceptions: list[EventErrorDetail] = []
        duplicates = 0
        default = 0
        rollback = 0
        accepted = 0
        affected_experiment_ids: set[UUID] = set()

        async with self.uow:
            for i, raw in enumerate(batch.events):
                event_key = raw.get("eventKey", f"index:{i}")
                try:
                    item = SendEventData.model_validate(raw)
                except ValidationError as e:
                    exceptions.append(EventErrorDetail(
                        eventKey=event_key,
                        reason=self._format_validation_error(e),
                    ))
                    continue

                try:
                    decision = await self.uow.decision_repo.get_by_id_with_variant(item.decision_id)
                    if decision:
                        if decision.variant.experiment.status == ExperimentStatus.ROLLBACK:
                            rollback += 1
                            continue
                        elif decision.variant.experiment.status == ExperimentStatus.RUNNING:
                            affected_experiment_ids.add(decision.variant.experiment_id)
                            catalog = await self.uow.event_repo.get_by_code(item.eventCatalog_code)
                            if catalog is None:
                                exceptions.append(EventErrorDetail(
                                    eventKey=item.eventKey,
                                    reason="Invalid event catalog code",
                                ))
                                continue
                            if catalog.requiresExposure and not await self.uow.event_repo.get_exposure(
                                    item.decision_id):
                                exceptions.append(EventErrorDetail(
                                    eventKey=item.eventKey,
                                    reason="Event requires exposure",
                                ))
                                continue

                            async with self.uow.session.begin_nested():
                                await self.uow.event_repo.assign_event(Event(**item.model_dump()))
                                accepted += 1
                        else:
                            default += 1
                    else:
                        default += 1

                except DuplicateError:
                    duplicates += 1
                    continue
                except RelationNotFoundError as ex:
                    exceptions.append(EventErrorDetail(
                        eventKey=item.eventKey,
                        reason=str(ex),
                    ))
                    continue
                except Exception as ex:
                    exceptions.append(EventErrorDetail(
                        eventKey=item.eventKey,
                        reason=str(ex),
                    ))
                    continue

            for experiment_id in affected_experiment_ids:
                await self._check_guardrails(experiment_id)

        return EventBatchResponse(
            accepted=accepted,
            duplicates=duplicates,
            rejected=len(exceptions),
            total=len(batch.events),
            errors=exceptions,
        )

    async def get_report(self, experiment_code: str, time_from: datetime, time_to: datetime):
        async with self.uow:
            experiment = await self.uow.experiment_repo.get_by_code(experiment_code)
            if not experiment:
                raise ExperimentNotFoundError
            if experiment.status not in {ExperimentStatus.RUNNING, ExperimentStatus.COMPLETED,
                                         ExperimentStatus.PAUSED, ExperimentStatus.ARCHIVED,
                                         ExperimentStatus.ROLLBACK}:
                raise ExperimentInvalidStatusError

            variants_report = []
            for variant in experiment.variants:
                metrics_report = []
                for metric in experiment.metrics:
                    value, event_count = await self._get_metric_value(
                        metric, variant.id, time_from, time_to
                    )
                    metrics_report.append(MetricReportItem(
                        metric_code=metric.metricCatalog_code,
                        metric_name=metric.metric_catalog.name,
                        role=metric.role,
                        value=value,
                        event_count=event_count,
                    ))
                variants_report.append(VariantReportItem(
                    variant_id=variant.id,
                    variant_name=variant.name,
                    is_control=variant.isControl,
                    metrics=metrics_report,
                ))

            return ExperimentReportResponse(
                experiment_code=experiment_code,
                time_from=time_from,
                time_to=time_to,
                variants=variants_report,
            )
