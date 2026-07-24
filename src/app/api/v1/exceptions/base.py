from typing import Any
from uuid import uuid4

from fastapi import status

from app.core.schemas.responses import ErrorResponse
from app.core.utils import now_iso_z


class APIException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(
        self,
        path: str,
        *,
        message: str | None = None,
        trace_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.path = path
        self.message = message or self.message
        self.trace_id = trace_id or str(uuid4())
        self.timestamp = now_iso_z()
        self.details = details or {}

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            code=self.code,
            message=self.message,
            traceId=self.trace_id,
            timestamp=self.timestamp,
            path=self.path,
            details=self.details or None,
        )
