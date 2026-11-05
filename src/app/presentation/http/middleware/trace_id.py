"""Trace id on every request, plus the last line of defence against unhandled exceptions.

A pure ASGI middleware (not ``BaseHTTPMiddleware``): the context variable stays visible to
endpoints and logs, and a 500 response also gets ``X-Trace-Id`` and the ``ErrorResponse`` format.
"""

import logging
import re
from contextvars import ContextVar
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infra.logger import log_trace_id
from app.presentation.http.schemas.responses import ErrorResponse

logger = logging.getLogger(__name__)

TRACE_ID_HEADER = "X-Trace-Id"
# A client-supplied id is echoed back and logged, so it must not carry arbitrary text.
_SAFE_TRACE_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    return _trace_id_ctx.get()


class TraceIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(TRACE_ID_HEADER, "")
        trace_id = incoming if _SAFE_TRACE_ID.match(incoming) else str(uuid4())
        token = _trace_id_ctx.set(trace_id)
        log_token = log_trace_id.set(trace_id)
        response_started = False

        async def send_with_trace_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                MutableHeaders(scope=message)[TRACE_ID_HEADER] = trace_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_id)
        except Exception:
            # ObservabilityMiddleware has already logged the failure with its route and timing.
            if response_started:
                raise
            response = JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    code="INTERNAL_ERROR",
                    message="Internal server error",
                    traceId=trace_id,
                    path=scope.get("path", ""),
                ).model_dump(mode="json", exclude_none=True),
            )
            await response(scope, receive, send_with_trace_id)
        finally:
            _trace_id_ctx.reset(token)
            log_trace_id.reset(log_token)
