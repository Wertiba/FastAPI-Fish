from datetime import datetime
from uuid import UUID

from app.core.schemas.base import PyModel
from app.core.schemas.experiment import MetricRole


class MetricReportItem(PyModel):
    metric_code: str
    metric_name: str
    role: MetricRole
    value: float
    event_count: int


class VariantReportItem(PyModel):
    variant_id: UUID
    variant_name: str
    is_control: bool
    metrics: list[MetricReportItem]


class ExperimentReportResponse(PyModel):
    experiment_code: str
    time_from: datetime
    time_to: datetime
    variants: list[VariantReportItem]
