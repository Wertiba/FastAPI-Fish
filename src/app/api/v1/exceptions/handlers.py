from uuid import UUID, uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.exceptions import APIException
from app.api.v1.exceptions.exc_map import DOMAIN_TO_API
from app.core.exceptions.user_exs import EntityError
from app.core.schemas.responses import FieldError, ValidationErrorResponse
from app.core.utils import loc_to_field, now_iso_z
from app.core.utils.loc2field import priority, rejected_value


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(EntityError)
    async def handle_domain_exception(request: Request, exc: EntityError):  # noqa: RUF029
        factory = None
        for exc_cls, fac in DOMAIN_TO_API.items():
            if isinstance(exc, exc_cls):
                factory = fac
                break

        if factory:
            api_exc = factory(request.url.path, exc)  # noqa
        else:
            api_exc = APIException(
                path=request.url.path,
                message="Domain error",
            )

        return JSONResponse(
            status_code=api_exc.status_code,
            content=api_exc.to_response().model_dump(exclude_none=True, mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):  # noqa: RUF029
        trace_id = request.headers.get("X-Request-Id") or str(uuid4())

        field_errors = [
            FieldError(
                field=loc_to_field(tuple(err.get("loc", ()))),
                issue=err.get("msg"),
                rejectedValue=rejected_value(err),
            )
            for err in sorted(exc.errors(), key=priority)
        ]

        payload = ValidationErrorResponse(
            traceId=UUID(trace_id),
            path=request.url.path,
            fieldErrors=field_errors,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(mode="json"),
        )
