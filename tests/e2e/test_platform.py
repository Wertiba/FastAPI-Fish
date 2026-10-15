"""Сквозные вещи: health, metrics, trace-id, формат ошибок."""

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.bootstrap.config import Settings
from app.main import create_app
from app.modules.registry import MODULES
from app.shared.module import Module


def test_liveness_and_readiness(client: TestClient) -> None:
    assert client.get("/health/liveness").json() == {"status": "ok"}
    assert client.get("/health/readiness").json() == {"status": "ready", "checks": {"database": "ready"}}


def test_metrics_exposed(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "python_info" in response.text


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


def test_unhandled_exception_returns_500_with_trace_id(settings: Settings) -> None:
    boom = APIRouter()

    @boom.get("/boom")
    async def explode() -> None:
        raise RuntimeError("kaboom")

    app = create_app(settings, modules=(*MODULES, Module(name="boom", routers=[boom])))
    with TestClient(app) as client:
        response = client.get("/api/v1/boom", headers={"X-Trace-Id": "trace-500"})

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert response.json()["traceId"] == "trace-500"
    assert response.headers["X-Trace-Id"] == "trace-500"
    assert "kaboom" not in response.text
