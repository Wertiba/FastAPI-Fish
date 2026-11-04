from typing import Any

from pydantic import Field

from app.core.schemas.base import PyModel
from app.core.utils import TimeHelper


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
    message: str = "Some fields are not correct."
    traceId: str
    timestamp: str = Field(default_factory=TimeHelper.now_iso_z)
    path: str
    fieldErrors: list[FieldError]
