"""Сквозные вещи: health, metrics, trace-id, формат ошибок."""

from collections.abc import Callable
from uuid import uuid4

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient


def test_liveness_and_readiness(client: TestClient) -> None:
    assert client.get("/health/liveness").json() == {"status": "ok"}
    assert client.get("/health/readiness").json() == {"status": "ready", "checks": {"database": "ready"}}


def test_metrics_exposed_with_route_templates(client: TestClient, admin_headers: dict[str, str]) -> None:
    client.get("/health/liveness")
    client.get(f"/api/v1/users/{uuid4()}", headers=admin_headers)
    client.get("/api/v1/nope")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "python_info" in response.text
    assert 'app_http_requests_total{method="GET",path="/health/liveness",status="200"}' in response.text
    assert 'app_http_requests_total{method="GET",path="/api/v1/users/{user_id}",status="404"}' in response.text
    assert 'app_http_requests_total{method="GET",path="<unmatched>",status="404"}' in response.text


def test_trace_id_is_echoed_or_generated(client: TestClient) -> None:
    echoed = client.get("/health/liveness", headers={"X-Trace-Id": "my-trace-123"})
    unsafe = client.get("/health/liveness", headers={"X-Trace-Id": "bad value\nwith newline"})

    assert echoed.headers["X-Trace-Id"] == "my-trace-123"
    assert unsafe.headers["X-Trace-Id"] != "bad value\nwith newline"
    assert len(unsafe.headers["X-Trace-Id"]) == 36


def test_unknown_route_uses_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.json()["path"] == "/api/v1/nope"


def test_wrong_method_uses_error_format(client: TestClient) -> None:
    response = client.patch("/api/v1/users/me")
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_unhandled_exception_returns_500_with_trace_id(make_app: Callable[[], FastAPI]) -> None:
    boom = APIRouter()

    @boom.get("/api/v1/boom")
    async def explode() -> None:
        raise RuntimeError("kaboom")

    app = make_app()
    app.include_router(boom)
    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/api/v1/boom", headers={"X-Trace-Id": "trace-500"})

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert response.json()["traceId"] == "trace-500"
    assert response.headers["X-Trace-Id"] == "trace-500"
    assert "kaboom" not in response.text
