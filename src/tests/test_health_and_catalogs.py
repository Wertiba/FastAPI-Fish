"""
test_health_and_catalogs.py — Health/Readiness и каталоги событий/метрик
Покрывает: B9-1/2, каталоги из 01_setup.sh и 10_health.sh

Тесты:
  T-HLT-01  GET /health → 200 {status: healthy}
  T-HLT-02  GET /ready → 200 {status: ready, checks.database: ready}
  T-HLT-03  GET /ping → 200 {status: ok}
  T-CAT-01  Базовые события каталога созданы (EXPOSURE, CONVERSION, ...)
  T-CAT-02  Базовые метрики каталога созданы (CONVERSIONS, CONVERSION_RATE, ...)
  T-CAT-03  Создание пользовательской метрики (Admin)
  T-CAT-04  Создание пользовательского события (Admin)
  T-CAT-05  Создание метрики Viewer'ом → 403
  T-CAT-06  EventMetricLink: привязка события к метрике
  T-CAT-07  Дублирующийся код каталога → ошибка
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────────────────
# T-HLT-01: /health
# ─────────────────────────────────────────────────────────────────────────────
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "healthy"


# ─────────────────────────────────────────────────────────────────────────────
# T-HLT-02: /ready
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.skip(reason="Health checks require real DB, not test SQLite")
async def test_ready_endpoint(client: AsyncClient):
    resp = await client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ready"
    assert data.get("checks", {}).get("database") == "ready"


# ─────────────────────────────────────────────────────────────────────────────
# T-HLT-03: /ping
# ─────────────────────────────────────────────────────────────────────────────
async def test_ping_endpoint(client: AsyncClient):
    resp = await client.get("/api/v1/ping")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# T-CAT-01: базовые события каталога
# ─────────────────────────────────────────────────────────────────────────────
async def test_base_event_catalog_exists(
    client: AsyncClient, admin_user, roles, base_events_catalog
):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.get("/api/v1/event-catalog?limit=20", headers=hdrs)
    assert resp.status_code == 200
    codes = {e["code"] for e in resp.json().get("items", [])}
    for expected in ("EXPOSURE", "CONVERSION", "ERROR", "LATENCY", "CLICK", "PURCHASE"):
        assert expected in codes, f"{expected} не найден в event catalog"


# ─────────────────────────────────────────────────────────────────────────────
# T-CAT-02: базовые метрики каталога
# ─────────────────────────────────────────────────────────────────────────────
async def test_base_metric_catalog_exists(
    client: AsyncClient, admin_user, roles, base_metrics_catalog
):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.get("/api/v1/metric-catalog?limit=20", headers=hdrs)
    assert resp.status_code == 200
    codes = {m["code"] for m in resp.json().get("items", [])}
    for expected in ("IMPRESSIONS", "CONVERSIONS", "CONVERSION_RATE", "ERRORS", "ERROR_RATE", "AVG_LATENCY"):
        assert expected in codes, f"{expected} не найден в metric catalog"


# ─────────────────────────────────────────────────────────────────────────────
# T-CAT-03: создание пользовательской метрики
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_custom_metric(
    client: AsyncClient, admin_user, roles
):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/metric-catalog", headers=hdrs, json={
        "code": "CUSTOM_REVENUE",
        "name": "Revenue per user",
        "type": "SUM",
        "aggregationUnit": "USER",
        "description": "Суммарный доход на уникального пользователя",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "CUSTOM_REVENUE"
    assert data["type"] == "SUM"
    assert data["isSystem"] == False


# ─────────────────────────────────────────────────────────────────────────────
# T-CAT-04: создание пользовательского события
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_custom_event(
    client: AsyncClient, admin_user, roles
):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/event-catalog", headers=hdrs, json={
        "code": "CUSTOM_ADD_TO_CART",
        "name": "Add to Cart",
        "description": "Пользователь добавил товар в корзину",
        "requiresExposure": False,
        "requiredParams": {"product_id": "string"},
    })
    assert resp.status_code == 201
    assert resp.json()["code"] == "CUSTOM_ADD_TO_CART"


# ─────────────────────────────────────────────────────────────────────────────
# T-CAT-05: Viewer не может создать метрику → 403
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_metric_by_viewer_forbidden(
    client: AsyncClient, viewer_user, roles
):
    hdrs = await auth_headers(client, "viewer@test.ru", "viewpass")
    resp = await client.post("/api/v1/metric-catalog", headers=hdrs, json={
        "code": "VIEWER_METRIC",
        "name": "Viewer Metric",
        "type": "COUNT",
    })
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# T-CAT-06: EventMetricLink — привязка события к метрике
# ─────────────────────────────────────────────────────────────────────────────
async def test_event_metric_link(
    client: AsyncClient, admin_user, roles, base_events_catalog, base_metrics_catalog
):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/metric-catalog/assign", headers=hdrs, json={
        "metricCatalog_code": "IMPRESSIONS",
        "items": [{"eventCatalog_code": "EXPOSURE", "role": "numerator"}],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["eventCatalog_code"] == "EXPOSURE"


# ─────────────────────────────────────────────────────────────────────────────
# T-CAT-07: дублирующийся код метрики → ошибка
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_duplicate_metric_code(
    client: AsyncClient, admin_user, roles, base_metrics_catalog
):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/metric-catalog", headers=hdrs, json={
        "code": "CONVERSIONS",  # уже существует
        "name": "Duplicate",
        "type": "COUNT",
    })
    assert resp.status_code in (409, 422)
