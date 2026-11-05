import logging
from collections.abc import Mapping
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.application.exceptions import ApplicationError, DuplicateError
from app.domain.errors import EntityError
from app.presentation.http.api.v1.exceptions import APIException, Conflict, MethodNotAllowed, NotFound
from app.presentation.http.api.v1.exceptions.exc_map import DOMAIN_TO_API
from app.presentation.http.loc2field import loc_to_field, priority, rejected_value
from app.presentation.http.middleware.observability import request_log_context
from app.presentation.http.middleware.trace_id import get_trace_id
from app.presentation.http.schemas.responses import FieldError, ValidationErrorResponse

logger = logging.getLogger(__name__)

_HTTP_ERRORS: dict[int, type[APIException]] = {
    status.HTTP_404_NOT_FOUND: NotFound,
    status.HTTP_405_METHOD_NOT_ALLOWED: MethodNotAllowed,
}


def _json(api_exc: APIException, headers: Mapping[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=api_exc.status_code,
        content=api_exc.to_response().model_dump(exclude_none=True, mode="json"),
        headers=headers or api_exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Unhandled exceptions become a 500 in ``TraceIdMiddleware``, which also keeps the trace id header."""

    @app.exception_handler(EntityError)
    async def handle_domain_exception(request: Request, exc: EntityError) -> JSONResponse:  # noqa: RUF029
        factory = next((fac for exc_cls, fac in DOMAIN_TO_API.items() if isinstance(exc, exc_cls)), None)
        if factory is not None:
            api_exc = factory(request.url.path, exc)
        else:
            logger.warning("unmapped_domain_error", extra=request_log_context(request), exc_info=exc)
            api_exc = APIException(path=request.url.path, message="Domain error")
        return _json(api_exc)

    @app.exception_handler(APIException)
    async def handle_api_exception(request: Request, exc: APIException) -> JSONResponse:  # noqa: RUF029
        return _json(exc)

    @app.exception_handler(DuplicateError)
    async def handle_duplicate(request: Request, exc: DuplicateError) -> JSONResponse:  # noqa: RUF029
        return _json(Conflict(path=request.url.path))

    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:  # noqa: RUF029
        logger.error("application_error", extra=request_log_context(request), exc_info=exc)
        return _json(APIException(path=request.url.path))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:  # noqa: RUF029
        api_cls = _HTTP_ERRORS.get(exc.status_code)
        if api_cls is not None:
            api_exc = api_cls(path=request.url.path)
        else:
            api_exc = APIException(path=request.url.path, message=str(exc.detail))
            api_exc.status_code, api_exc.code = exc.status_code, f"HTTP_{exc.status_code}"
        return _json(api_exc, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: RUF029
        field_errors = [
            FieldError(
                field=loc_to_field(tuple(err.get("loc", ()))),
                issue=err.get("msg", ""),
                rejectedValue=rejected_value(err),
            )
            for err in sorted(exc.errors(), key=priority)
        ]
        payload = ValidationErrorResponse(
            traceId=get_trace_id() or str(uuid4()),
            path=request.url.path,
            fieldErrors=field_errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(mode="json"),
        )
