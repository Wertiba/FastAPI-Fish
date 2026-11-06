import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.shared.infra.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_IN_PROGRESS, HTTP_REQUESTS_TOTAL

logger = logging.getLogger(__name__)

_QUIET_PATHS = frozenset({"/health/liveness", "/health/readiness", "/metrics"})
_UNMATCHED = "<unmatched>"
_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "CONNECT", "TRACE"})


def _route_template(request: Request) -> str:
    """Route path like /api/v1/users/{user_id}: keeps metric label cardinality bounded.

    Read after routing: FastAPI includes routers lazily, so the full template is not on any route
    object. The router leaves the matched route and its path params in the scope; every path
    segment holding a param value is put back as ``{name}``.
    """
    if request.scope.get("route") is None:
        return _UNMATCHED
    names = {str(value): f"{{{name}}}" for name, value in request.path_params.items()}
    return "/".join(names.get(segment, segment) for segment in request.url.path.split("/"))


def request_log_context(request: Request) -> dict[str, Any]:
    return {
        "http_method": request.method if request.method in _METHODS else "OTHER",
        "route": _route_template(request),
        **{key: value for key, value in request.path_params.items() if key == "user_id"},
    }


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Prometheus request metrics plus one access-log line per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        method = request.method if request.method in _METHODS else "OTHER"
        status_code = 500
        started = time.perf_counter()
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()
        error = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error = exc
            raise
        finally:
            elapsed = time.perf_counter() - started
            template = _route_template(request)
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()
            HTTP_REQUESTS_TOTAL.labels(method=method, path=template, status=str(status_code)).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=template).observe(elapsed)
            if path not in _QUIET_PATHS or status_code >= 400:
                failed = status_code >= 500
                logger.log(
                    logging.ERROR if failed else logging.INFO,
                    "http_request_failed" if failed else "http_request_completed",
                    extra={
                        **request_log_context(request),
                        "status_code": status_code,
                        "duration_ms": round(elapsed * 1000, 3),
                    },
                    exc_info=error,
                )
