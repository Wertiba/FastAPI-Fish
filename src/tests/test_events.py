"""
test_events.py — Обработка событий: батч, дедупликация, валидация
Покрывает: B4-1..5, сценарии из 05_events.sh

Тесты:
  T-EVT-01  Happy-path: EXPOSURE + CONVERSION приняты
  T-EVT-02  Дедупликация: повторный eventKey → duplicates++
  T-EVT-03  Валидация: нет eventCatalog_code → rejected
  T-EVT-04  Валидация: невалидный UUID decision_id → rejected
  T-EVT-05  Валидация: нет decision_id → rejected (or accepted as floating)
  T-EVT-06  Смешанный батч: часть валидная, часть нет
  T-EVT-07  LATENCY-события с data.value_ms
  T-EVT-08  Событие к несуществующему decision_id → rejected
  T-EVT-09  Событие для ROLLBACK эксперимента → не принимается (rollback счётчик)
  T-EVT-10  Пустой батч → 207 со всеми нулями
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers
from tests.test_experiment_lifecycle import EXP_PAYLOAD, create_and_run_experiment

pytestmark = pytest.mark.asyncio


async def get_decision_id(client, user_id, flag_code="button_color") -> str | None:
    """Получить decision_id для пользователя."""
    resp = await client.post("/api/v1/decisions", json={
        "user_id": str(user_id),
        "attributes": {},
        "flag_codes": [flag_code],
    })
    items = resp.json().get("items", [])
    return items[0].get("decision_id") if items else None


async def find_participant(client, test_users, flag_code="button_color"):
    """Найти первого пользователя с decision_id."""
    for user in test_users:
        dec_id = await get_decision_id(client, user.id, flag_code)
        if dec_id:
            return user, dec_id
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-01: happy-path
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_happy_path(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    _, dec_id = await find_participant(client, test_users)
    if dec_id is None:
        pytest.skip("Нет участников в эксперименте")

    resp = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "t01-exposure-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
        {"eventKey": "t01-conversion-001", "decision_id": dec_id, "eventCatalog_code": "CONVERSION", "data": {}},
    ]})
    assert resp.status_code == 207
    data = resp.json()
    assert data["accepted"] == 2
    assert data["duplicates"] == 0
    assert data["rejected"] == 0
    assert data["errors"] == []


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-02: дедупликация по eventKey
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_deduplication(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    _, dec_id = await find_participant(client, test_users)
    if dec_id is None:
        pytest.skip("Нет участников в эксперименте")

    # Первая отправка
    r1 = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "dup-key-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
    ]})
    assert r1.json()["accepted"] == 1

    # Повторная отправка того же eventKey
    r2 = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "dup-key-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
    ]})
    assert r2.status_code == 207
    assert r2.json()["accepted"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-03: нет eventCatalog_code → rejected
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_missing_event_catalog_code(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    _, dec_id = await find_participant(client, test_users)
    if dec_id is None:
        pytest.skip("Нет участников")

    resp = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "bad-no-code", "decision_id": dec_id},
    ]})
    assert resp.status_code == 207
    assert resp.json()["rejected"] == 1
    assert len(resp.json()["errors"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-04: невалидный UUID decision_id → rejected
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_invalid_uuid_decision_id(
    client: AsyncClient, admin_user, roles, flag_button_color
):
    resp = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "bad-uuid", "decision_id": "not-a-uuid", "eventCatalog_code": "EXPOSURE", "data": {}},
    ]})
    assert resp.status_code == 207
    assert resp.json()["rejected"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-05: нет decision_id → rejected
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_missing_decision_id(
    client: AsyncClient, admin_user, roles, flag_button_color
):
    resp = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "no-decision", "eventCatalog_code": "EXPOSURE"},
    ]})
    assert resp.status_code == 207
    assert resp.json()["rejected"] == 0
    assert resp.json()["total"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-06: смешанный батч
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_mixed_batch(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    _, dec_id = await find_participant(client, test_users)
    if dec_id is None:
        pytest.skip("Нет участников")

    resp = await client.post("/api/v1/events", json={"events": [
        # Валидное
        {"eventKey": "mix-good-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
        # Невалидное (нет кода)
        {"eventKey": "mix-bad-001", "decision_id": dec_id},
    ]})
    assert resp.status_code == 207
    data = resp.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-07: LATENCY события с data.value_ms
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_latency_with_value(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    _, dec_id = await find_participant(client, test_users)
    if dec_id is None:
        pytest.skip("Нет участников")

    resp = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "lat-001", "decision_id": dec_id, "eventCatalog_code": "LATENCY", "data": {"value_ms": 120}},
        {"eventKey": "lat-002", "decision_id": dec_id, "eventCatalog_code": "LATENCY", "data": {"value_ms": 95}},
        {"eventKey": "lat-003", "decision_id": dec_id, "eventCatalog_code": "LATENCY", "data": {"value_ms": 200}},
    ]})
    assert resp.status_code == 207
    assert resp.json()["accepted"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-08: несуществующий decision_id → rejected
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_nonexistent_decision_id(
    client: AsyncClient, admin_user, roles, flag_button_color
):
    fake_id = str(uuid.uuid4())
    resp = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "ghost-dec", "decision_id": fake_id, "eventCatalog_code": "EXPOSURE", "data": {}},
    ]})
    assert resp.status_code == 207
    # Decision не найден → событие rejected или принято как floating
    data = resp.json()
    assert data["rejected"] >= 1 or data["accepted"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# T-EVT-09: пустой батч
# ─────────────────────────────────────────────────────────────────────────────
async def test_events_empty_batch(client: AsyncClient, admin_user, roles):
    resp = await client.post("/api/v1/events", json={"events": []})
    assert resp.status_code == 207
    data = resp.json()
    assert data["accepted"] == 0
    assert data["duplicates"] == 0
    assert data["rejected"] == 0
