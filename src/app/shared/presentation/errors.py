"""Единый формат ошибок API.

Модулям не нужно регистрировать свои обработчики: достаточно унаследовать
ошибку от категории из ``shared/domain/errors.py`` — статус подберётся сам.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.domain.errors import (
    AccessDeniedError,
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    DomainError,
    LockedError,
    NotFoundError,
)
from app.shared.presentation.request_context import get_trace_id
from app.shared.presentation.schemas import ErrorResponse, FieldError, ValidationErrorResponse, timestamp_now

STATUS_BY_CATEGORY: tuple[tuple[type[DomainError], int], ...] = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (AccessDeniedError, status.HTTP_403_FORBIDDEN),
    (BusinessRuleError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (LockedError, status.HTTP_423_LOCKED),
)

_HTTP_CODES = {
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
}


def error_payload(
    code: str, message: str, path: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    body = ErrorResponse(
        code=code,
        message=message,
        trace_id=get_trace_id(),
        timestamp=timestamp_now(),
        path=path,
        details=details or None,
    )
    return body.model_dump(mode="json", exclude_none=True)


def status_for(exc: DomainError) -> int:
    for category, code in STATUS_BY_CATEGORY:
        if isinstance(exc, category):
            return code
    return status.HTTP_400_BAD_REQUEST


def _loc_to_field(loc: tuple[Any, ...]) -> str:
    parts = list(loc[1:] if loc and loc[0] in {"body", "query", "path", "header", "cookie"} else loc)
    out: list[str] = []
    for part in parts:
        if isinstance(part, int):
            out.append(f"{out.pop()}[{part}]" if out else f"[{part}]")
        else:
            out.append(str(part))
    return ".".join(out)


def _rejected_value(err: dict[str, Any]) -> Any:
    value, loc = err.get("input"), err.get("loc", ())
    if isinstance(value, dict) and loc:
        return value.get(loc[-1])
    return value


def setup_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        code = status_for(exc)
        headers = {"WWW-Authenticate": "Bearer"} if code == status.HTTP_401_UNAUTHORIZED else None
        return JSONResponse(
            status_code=code,
            content=error_payload(exc.code, exc.message, request.url.path, exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = sorted(exc.errors(), key=lambda e: 0 if "limit_value" in (e.get("ctx") or {}) else 1)
        body = ValidationErrorResponse(
            trace_id=get_trace_id(),
            timestamp=timestamp_now(),
            path=request.url.path,
            field_errors=[
                FieldError(
                    field=_loc_to_field(tuple(err.get("loc", ()))),
                    issue=err.get("msg", ""),
                    rejected_value=_rejected_value(err),
                )
                for err in errors
            ],
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, str(exc.detail), request.url.path),
            headers=exc.headers,
        )
