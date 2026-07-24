"""
test_guardrails.py — Guardrails: порог, срабатывание, аудит
Покрывает: B5-1..5, сценарии из 06_guardrails.sh

Тесты:
  T-GRD-01  GUARDRAIL-метрика сохраняется в эксперименте (threshold, window, action)
  T-GRD-02  Превышение ERROR_RATE → эксперимент переходит в PAUSED
  T-GRD-03  Превышение с action=ROLLBACK → статус ROLLBACK
  T-GRD-04  Аудит: GuardrailHistory создаётся с правильными полями
  T-GRD-05  Guardrail не срабатывает если порог НЕ превышен
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


GUARDRAIL_EXP = {
    "code": "exp_guardrail_demo",
    "flag_code": "show_banner",
    "name": "Демо Guardrail",
    "description": "Низкий порог для теста",
    "part": 100,
    "version": 1.0,
    "variants": [
        {"name": "control_off", "value": "false", "weight": 50, "isControl": True},
        {"name": "variant_on",  "value": "true",  "weight": 50, "isControl": False},
    ],
    "metrics": [
        {"metricCatalog_code": "CONVERSIONS", "role": "MAIN"},
        # ERROR_RATE >= 1 → PAUSE (1 ошибка / 1 exposure = 1.0)
        {"metricCatalog_code": "ERROR_RATE", "role": "GUARDRAIL",
         "window": 86400, "threshold": 1, "action_code": "PAUSE"},
    ],
}

ROLLBACK_EXP = {
    "code": "exp_rollback_guard",
    "flag_code": "show_banner",
    "name": "Демо Guardrail ROLLBACK",
    "description": "Guardrail с action ROLLBACK",
    "part": 100,
    "version": 1.0,
    "variants": [
        {"name": "ctrl", "value": "false", "weight": 50, "isControl": True},
        {"name": "var",  "value": "true",  "weight": 50, "isControl": False},
    ],
    "metrics": [
        {"metricCatalog_code": "CONVERSIONS", "role": "MAIN"},
        {"metricCatalog_code": "ERROR_RATE", "role": "GUARDRAIL",
         "window": 86400, "threshold": 1, "action_code": "ROLLBACK"},
    ],
}


async def run_guardrail_experiment(client, expr_hdrs, payload, code):
    r = await client.post("/api/v1/experiments", headers=expr_hdrs, json=payload)
    assert r.status_code == 201, r.text
    await client.post("/api/v1/experiments/status/review", headers=expr_hdrs, json={"code": code})
    await client.post("/api/v1/experiments/status/stop-review", headers=expr_hdrs, json={"code": code})
    r = await client.post("/api/v1/experiments/status/running", headers=expr_hdrs, json={"code": code})
    assert r.status_code == 202, r.text


async def get_decision_id_for_flag(client, user_id, flag_code):
    resp = await client.post("/api/v1/decisions", json={
        "user_id": str(user_id),
        "attributes": {},
        "flag_codes": [flag_code],
    })
    items = resp.json().get("items", [])
    return items[0].get("decision_id") if items else None


# ─────────────────────────────────────────────────────────────────────────────
# T-GRD-01: guardrail-метрика сохраняется
# ─────────────────────────────────────────────────────────────────────────────
async def test_guardrail_metric_stored(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_show_banner, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    r = await client.post("/api/v1/experiments", headers=expr_hdrs, json=GUARDRAIL_EXP)
    assert r.status_code == 201
    data = r.json()
    guardrail_metrics = [m for m in data["metrics"] if m["role"] == "GUARDRAIL"]
    assert len(guardrail_metrics) == 1
    gm = guardrail_metrics[0]
    assert gm["metricCatalog_code"] == "ERROR_RATE"
    assert gm["threshold"] == 1
    assert gm["action_code"] == "PAUSE"


# ─────────────────────────────────────────────────────────────────────────────
# T-GRD-02: ERROR_RATE > threshold → PAUSED
# ─────────────────────────────────────────────────────────────────────────────
async def test_guardrail_triggers_pause(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_show_banner, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await run_guardrail_experiment(client, expr_hdrs, GUARDRAIL_EXP, "exp_guardrail_demo")

    # Найти участника
    dec_id = None
    for user in test_users:
        dec_id = await get_decision_id_for_flag(client, user.id, "show_banner")
        if dec_id:
            break

    if dec_id is None:
        pytest.skip("Нет участников в эксперименте")

    # Отправляем: 1 EXPOSURE + 2 ERROR → ERROR_RATE = 2/1 = 2.0 > threshold=1
    resp = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "grd-exp-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
        {"eventKey": "grd-err-001", "decision_id": dec_id, "eventCatalog_code": "ERROR",    "data": {"msg": "NPE"}},
        {"eventKey": "grd-err-002", "decision_id": dec_id, "eventCatalog_code": "ERROR",    "data": {"msg": "timeout"}},
    ]})
    assert resp.status_code == 207
    assert resp.json()["accepted"] >= 1

    # Проверяем, что эксперимент перешёл в PAUSED
    r = await client.get("/api/v1/experiments/exp_guardrail_demo", headers=admin_hdrs)
    assert r.status_code == 200
    assert r.json()["status"] == "PAUSED", f"Ожидался PAUSED, получен {r.json()['status']}"


# ─────────────────────────────────────────────────────────────────────────────
# T-GRD-03: action=ROLLBACK → статус ROLLBACK
# ─────────────────────────────────────────────────────────────────────────────
async def test_guardrail_triggers_rollback(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_show_banner, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await run_guardrail_experiment(client, expr_hdrs, ROLLBACK_EXP, "exp_rollback_guard")

    dec_id = None
    for user in test_users:
        dec_id = await get_decision_id_for_flag(client, user.id, "show_banner")
        if dec_id:
            break

    if dec_id is None:
        pytest.skip("Нет участников")

    await client.post("/api/v1/events", json={"events": [
        {"eventKey": "rb-exp-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
        {"eventKey": "rb-err-001", "decision_id": dec_id, "eventCatalog_code": "ERROR",    "data": {}},
        {"eventKey": "rb-err-002", "decision_id": dec_id, "eventCatalog_code": "ERROR",    "data": {}},
    ]})

    r = await client.get("/api/v1/experiments/exp_rollback_guard", headers=admin_hdrs)
    assert r.json()["status"] == "ROLLBACK"


# ─────────────────────────────────────────────────────────────────────────────
# T-GRD-04: аудит — GuardrailHistory с правильными полями
# ─────────────────────────────────────────────────────────────────────────────
async def test_guardrail_audit_history(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_show_banner, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await run_guardrail_experiment(client, expr_hdrs, GUARDRAIL_EXP, "exp_guardrail_demo")

    dec_id = None
    for user in test_users:
        dec_id = await get_decision_id_for_flag(client, user.id, "show_banner")
        if dec_id:
            break

    if dec_id is None:
        pytest.skip("Нет участников")

    await client.post("/api/v1/events", json={"events": [
        {"eventKey": "audit-exp-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
        {"eventKey": "audit-err-001", "decision_id": dec_id, "eventCatalog_code": "ERROR",    "data": {}},
        {"eventKey": "audit-err-002", "decision_id": dec_id, "eventCatalog_code": "ERROR",    "data": {}},
    ]})

    r = await client.get("/api/v1/experiments/guardrails/exp_guardrail_demo", headers=admin_hdrs)
    assert r.status_code == 200
    data = r.json()
    items = data.get("items", [])
    assert len(items) >= 1

    history = items[0].get("history", {})
    assert history.get("metric_code") == "ERROR_RATE"
    assert history.get("threshold") == 1
    assert history.get("actual_value") >= 1
    assert history.get("action") == "PAUSE"
    assert "triggered_at" in history


# ─────────────────────────────────────────────────────────────────────────────
# T-GRD-05: guardrail НЕ срабатывает если порог не превышен
# ─────────────────────────────────────────────────────────────────────────────
async def test_guardrail_does_not_trigger_below_threshold(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_show_banner, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await run_guardrail_experiment(client, expr_hdrs, GUARDRAIL_EXP, "exp_guardrail_demo")

    dec_id = None
    for user in test_users:
        dec_id = await get_decision_id_for_flag(client, user.id, "show_banner")
        if dec_id:
            break

    if dec_id is None:
        pytest.skip("Нет участников")

    # Только EXPOSURE без ERROR → ERROR_RATE = 0 < threshold=1
    await client.post("/api/v1/events", json={"events": [
        {"eventKey": "safe-exp-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {}},
        {"eventKey": "safe-exp-002", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE", "data": {"x": 1}},
    ]})

    r = await client.get("/api/v1/experiments/exp_guardrail_demo", headers=admin_hdrs)
    assert r.json()["status"] == "RUNNING", "Guardrail не должен был сработать"
