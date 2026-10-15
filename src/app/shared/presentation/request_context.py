"""Trace-id на каждый запрос + последняя линия обороны от необработанных исключений.

Чистый ASGI-middleware (не BaseHTTPMiddleware): contextvar виден и в эндпоинтах,
и в логах, а 500-ответ тоже получает ``X-Trace-Id`` и формат ``ErrorResponse``.
"""

import re
from contextvars import ContextVar
from uuid import uuid4

from loguru import logger
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.shared.presentation.schemas import ErrorResponse, timestamp_now

TRACE_ID_HEADER = "X-Trace-Id"
_SAFE_TRACE_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    return _trace_id.get()


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(TRACE_ID_HEADER, "")
        trace_id = incoming if _SAFE_TRACE_ID.match(incoming) else str(uuid4())
        token = _trace_id.set(trace_id)
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
            logger.exception("Unhandled error: {} {}", scope.get("method"), scope.get("path"))
            if response_started:
                raise
            response = JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    code="INTERNAL_ERROR",
                    message="Internal server error",
                    trace_id=trace_id,
                    timestamp=timestamp_now(),
                    path=scope.get("path", ""),
                ).model_dump(mode="json", exclude_none=True),
            )
            await response(scope, receive, send_with_trace_id)
        finally:
            _trace_id.reset(token)
