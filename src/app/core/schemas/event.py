from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.schemas.base import DatetimeResponse, PyModel


class EventCreateBody(PyModel):
    code: Annotated[str, Field(max_length=100)]
    name: Annotated[str, Field(max_length=255)]
    description: Annotated[str | None, Field(max_length=500)] = None
    requiredParams: dict | None = None
    requiresExposure: bool
    inArchive: bool = False


class EventData(EventCreateBody):
    id: UUID
    isSystem: bool
    createdBy: UUID | None = None
    createdAt: datetime


class EventReadResponse(EventData, DatetimeResponse):
    pass


class SendEventData(PyModel):
    eventKey: str
    decision_id: UUID | None = None
    eventCatalog_code: Annotated[str, Field(max_length=100)]
    data: dict | None = None


class SendEventResponse(SendEventData, DatetimeResponse):
    id: UUID
    createdAt: datetime


class EventBatchBody(PyModel):
    events: list[dict]


class EventErrorDetail(PyModel):
    eventKey: str
    reason: str


class EventBatchResponse(PyModel):
    accepted: int
    duplicates: int
    rejected: int
    total: int
    errors: list[EventErrorDetail] = []
