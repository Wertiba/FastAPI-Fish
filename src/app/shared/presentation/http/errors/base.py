from typing import Any
from uuid import uuid4

from fastapi import status

from app.shared.application.exceptions import ApplicationError
from app.shared.presentation.http.middleware.trace_id import get_trace_id
from app.shared.presentation.http.schemas.responses import ErrorResponse


class APIException(ApplicationError):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(
        self,
        path: str,
        *,
        message: str | None = None,
        trace_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.path = path
        self.message = message or self.message
        self.trace_id = trace_id or get_trace_id() or str(uuid4())
        self.details = details or {}

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            code=self.code,
            message=self.message,
            traceId=self.trace_id,
            path=self.path,
            details=self.details or None,
        )
