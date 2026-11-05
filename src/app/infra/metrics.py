from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "app_http_requests_total",
    "HTTP requests by method, route template and status code",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "app_http_request_duration_seconds",
    "HTTP request latency by method and route template",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "app_http_requests_in_progress",
    "HTTP requests being processed right now",
    ["method"],
)
DOMAIN_EVENTS_TOTAL = Counter(
    "app_domain_events_total",
    "Business actions: users registered, logins, deactivations...",
    ["entity", "action"],
)


def track(entity: str, action: str) -> None:
    DOMAIN_EVENTS_TOTAL.labels(entity=entity, action=action).inc()
