from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.core.schemas.experiment import MetricRole
from app.core.schemas.metric import AggregationUnit, MetricType
from app.infrastructure.models import Experiment, Metric, MetricCatalog
from app.infrastructure.models.event import Event, EventMetricLink
from app.infrastructure.unit_of_work import UnitOfWork


@dataclass
class VariantService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    @staticmethod
    def _strip_tz(dt: datetime) -> datetime:
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    @staticmethod
    def _calculate(catalog: MetricCatalog, links: list[EventMetricLink], events: list[Event]) -> float:
        if not events:
            return 0.0

        match catalog.type:
            case MetricType.COUNT:
                if catalog.aggregationUnit == AggregationUnit.USER:
                    return float(len({e.decision_id for e in events}))
                return float(len(events))

            case MetricType.SUM:
                link = links[0]
                field = link.value_field or "value"
                return float(sum(e.data.get(field, 0) for e in events if e.data))

            case MetricType.AVG:
                link = links[0]
                field = link.value_field or "value"
                values = [e.data.get(field, 0) for e in events if e.data]
                return sum(values) / len(values) if values else 0.0

            case MetricType.MIN:
                link = links[0]
                field = link.value_field or "value"
                values = [e.data.get(field) for e in events if e.data and e.data.get(field) is not None]
                return float(min(values)) if values else 0.0

            case MetricType.MAX:
                link = links[0]
                field = link.value_field or "value"
                values = [e.data.get(field) for e in events if e.data and e.data.get(field) is not None]
                return float(max(values)) if values else 0.0

            case MetricType.RATIO:
                numerator_codes = {l.eventCatalog_code for l in links if l.role == "numerator"}
                denominator_codes = {l.eventCatalog_code for l in links if l.role == "denominator"}
                n = sum(1 for e in events if e.eventCatalog_code in numerator_codes)
                d = sum(1 for e in events if e.eventCatalog_code in denominator_codes)
                return n / d if d else 0.0

            case _:
                return 0.0

    async def _get_metric_value(
            self,
            metric: Metric,
            variant_id: UUID,
            time_from: datetime,
            time_to: datetime,
    ) -> tuple[float, int]:
        links = await self.uow.metric_repo.get_event_metric_link(metric.metricCatalog_code)
        if not links:
            return 0.0, 0

        event_codes = [l.eventCatalog_code for l in links]
        events = await self.uow.event_repo.get_by_variant_and_event_codes(
            variant_id=variant_id,
            event_codes=event_codes,
            time_from=self._strip_tz(time_from),
            time_to=self._strip_tz(time_to),
        )
        value = self._calculate(metric.metric_catalog, links, events)
        return value, len(events)

    async def _get_variant_scores(
        self,
        experiment: Experiment,
        time_from: datetime,
        time_to: datetime,
        role_filter: MetricRole | None = None,
    ) -> dict[UUID, float]:
        metrics = experiment.metrics
        if role_filter:
            metrics = [m for m in metrics if m.role == role_filter]

        scores: dict[UUID, float] = {}
        for variant in experiment.variants:
            total = 0.0
            for metric in metrics:
                value, _ = await self._get_metric_value(
                    metric, variant.id, time_from, time_to
                )
                total += value
            scores[variant.id] = total

        return scores
