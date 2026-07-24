from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.core.schemas.base import PyModel
from app.core.utils import now_iso_z


class MessageResponse(PyModel):
    message: str


class PingResponse(PyModel):
    status: str = "ok"


class ErrorResponse(PyModel):
    code: str
    message: str
    traceId: str
    timestamp: str
    path: str
    details: dict[str, Any] | None = None


class FieldError(PyModel):
    field: str
    issue: str
    rejectedValue: Any


class ValidationErrorResponse(PyModel):
    code: str = "VALIDATION_FAILED"
    message: str = "Некоторые поля не прошли валидацию"
    traceId: UUID = Field(default_factory=uuid4)
    timestamp: str = Field(default_factory=now_iso_z)
    path: str
    fieldErrors: list[FieldError]
