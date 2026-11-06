from typing import Any

from pydantic import BaseModel, Field

from app.shared.presentation.http.schemas.base import PyModel, timestamp_now


class _EchoModel(BaseModel):
    """Error payloads echo the rejected input, so they must not run the PyModel input checks on it."""

    model_config = PyModel.model_config


class PingResponse(PyModel):
    status: str = "ok"


class ErrorResponse(_EchoModel):
    code: str
    message: str
    traceId: str
    timestamp: str = Field(default_factory=timestamp_now)
    path: str
    details: dict[str, Any] | None = None


class FieldError(_EchoModel):
    field: str
    issue: str
    rejectedValue: Any = None


class ValidationErrorResponse(_EchoModel):
    code: str = "VALIDATION_FAILED"
    message: str = "Some fields are not correct."
    traceId: str
    timestamp: str = Field(default_factory=timestamp_now)
    path: str
    fieldErrors: list[FieldError]
