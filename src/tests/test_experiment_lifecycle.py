"""
test_experiment_lifecycle.py — Жизненный цикл эксперимента и ревью
Покрывает: B3-1..5, сценарии из 03_experiment_lifecycle.sh

Тесты:
  T-EXP-01  Создание эксперимента (DRAFT) с вариантами и метриками
  T-EXP-02  Нельзя запустить DRAFT → 422
  T-EXP-03  DRAFT → IN_REVIEW
  T-EXP-04  Viewer не может ревьюировать → 403
  T-EXP-05  Завершение ревью без одобрений → REWORK/REJECTED (не APPROVED)
  T-EXP-06  Approver одобряет → APPROVED после stop-review
  T-EXP-07  APPROVED → RUNNING
  T-EXP-08  Второй эксперимент на тот же флаг блокируется → 422
  T-EXP-09  История версий эксперимента
  T-EXP-10  RUNNING → PAUSED → RUNNING
  T-EXP-11  Создание без контрольного варианта → 422
  T-EXP-12  Создание с несовпадением sum(weights) != part → 422
  T-EXP-13  Создание с несуществующим flag_code → 404/422
  T-EXP-14  Просмотр ревью эксперимента
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio

# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

EXP_PAYLOAD = {
    "code": "exp_button_color",
    "flag_code": "button_color",
    "name": "Тест цвета кнопки",
    "description": "Проверяем синяя или зелёная кнопка конвертирует лучше",
    "part": 100,
    "version": 1.0,
    "variants": [
        {"name": "control_green", "value": "green", "weight": 50, "isControl": True},
        {"name": "variant_blue",  "value": "blue",  "weight": 50, "isControl": False},
    ],
    "metrics": [
        {"metricCatalog_code": "CONVERSION_RATE", "role": "MAIN"},
        {"metricCatalog_code": "ERROR_RATE", "role": "GUARDRAIL", "window": 3600, "threshold": 50, "action_code": "PAUSE"},
        {"metricCatalog_code": "CONVERSIONS",     "role": "ADDITIONAL"},
    ],
}


async def create_and_run_experiment(client, admin_hdrs, expr_hdrs=None, payload=None, exp_code="exp_button_color"):
    """Создать (experimenter), одобрить и запустить (admin) эксперимент."""
    pl = payload or EXP_PAYLOAD
    create_hdrs = expr_hdrs or admin_hdrs
    r = await client.post("/api/v1/experiments", headers=create_hdrs, json=pl)
    assert r.status_code == 201, r.text

    await client.post("/api/v1/experiments/status/review", headers=create_hdrs, json={"code": exp_code})
    await client.post("/api/v1/experiments/status/stop-review", headers=create_hdrs, json={"code": exp_code})
    r = await client.post("/api/v1/experiments/status/running", headers=create_hdrs, json={"code": exp_code})
    assert r.status_code == 202, r.text
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-01: создание DRAFT
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_experiment_draft(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog
):
    hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    resp = await client.post("/api/v1/experiments", headers=hdrs, json=EXP_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["code"] == "exp_button_color"
    assert len(data["variants"]) == 2
    assert any(v["isControl"] for v in data["variants"])
    assert len(data["metrics"]) == 3
    assert any(m["role"] == "MAIN" for m in data["metrics"])
    assert any(m["role"] == "GUARDRAIL" for m in data["metrics"])


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-02: DRAFT → RUNNING невозможен
# ─────────────────────────────────────────────────────────────────────────────
async def test_cannot_run_from_draft(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog
):
    hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await client.post("/api/v1/experiments", headers=hdrs, json=EXP_PAYLOAD)

    resp = await client.post("/api/v1/experiments/status/running", headers=hdrs,
                             json={"code": "exp_button_color"})
    assert resp.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-03: DRAFT → IN_REVIEW
# ─────────────────────────────────────────────────────────────────────────────
async def test_draft_to_review(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog
):
    hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await client.post("/api/v1/experiments", headers=hdrs, json=EXP_PAYLOAD)

    resp = await client.post("/api/v1/experiments/status/review", headers=hdrs,
                             json={"code": "exp_button_color"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "IN_REVIEW"


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-04: Viewer не может ревьюировать → 403
# ─────────────────────────────────────────────────────────────────────────────
async def test_viewer_cannot_review(
    client: AsyncClient, admin_user, experimenter_user, viewer_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog
):
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    view_hdrs = await auth_headers(client, "viewer@test.ru", "viewpass")

    await client.post("/api/v1/experiments", headers=expr_hdrs, json=EXP_PAYLOAD)
    await client.post("/api/v1/experiments/status/review", headers=expr_hdrs,
                      json={"code": "exp_button_color"})

    resp = await client.post("/api/v1/reviews", headers=view_hdrs, json={
        "experiment_code": "exp_button_color",
        "result": "APPROVED",
        "comment": "trying to approve",
    })
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-05: stop-review без одобрений → не APPROVED
# ─────────────────────────────────────────────────────────────────────────────
async def test_stop_review_without_approvals_not_approved(
    client: AsyncClient, admin_user, experimenter_with_required, approver_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog
):
    # experimenter_with_required имеет required=1, но approver назначен и не голосовал
    # Сначала назначаем approver (иначе create упадёт с DeficiencyApproversError)
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    await client.post("/api/v1/users/approvers", headers=admin_hdrs, json={
        "experimenter_id": str(experimenter_with_required.id),
        "approver_id": str(approver_user.id),
    })

    expr_hdrs = await auth_headers(client, "experimenter_req@test.ru", "exprreqpass")
    await client.post("/api/v1/experiments", headers=expr_hdrs, json=EXP_PAYLOAD)
    await client.post("/api/v1/experiments/status/review", headers=expr_hdrs,
                      json={"code": "exp_button_color"})

    # Завершаем ревью без голосования — required=1, approved=0
    resp = await client.post("/api/v1/experiments/status/stop-review", headers=expr_hdrs,
                             json={"code": "exp_button_color"})
    assert resp.status_code == 202
    assert resp.json()["status"] in ("REWORK", "REJECTED")
    assert resp.json()["status"] != "APPROVED"


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-06: Approver одобряет → APPROVED
# ─────────────────────────────────────────────────────────────────────────────
async def test_approver_approves_experiment(
    client: AsyncClient, admin_user, experimenter_with_required, approver_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    appr_hdrs  = await auth_headers(client, "approver@test.ru", "apprpass")

    # Назначаем approver ДО создания эксперимента
    await client.post("/api/v1/users/approvers", headers=admin_hdrs, json={
        "experimenter_id": str(experimenter_with_required.id),
        "approver_id": str(approver_user.id),
    })

    expr_hdrs = await auth_headers(client, "experimenter_req@test.ru", "exprreqpass")
    await client.post("/api/v1/experiments", headers=expr_hdrs, json=EXP_PAYLOAD)
    await client.post("/api/v1/experiments/status/review", headers=expr_hdrs,
                      json={"code": "exp_button_color"})

    r = await client.post("/api/v1/reviews", headers=appr_hdrs, json={
        "experiment_code": "exp_button_color",
        "result": "APPROVED",
        "comment": "Всё корректно, одобряю",
    })

    assert r.status_code == 201
    assert r.json()["result"] == "APPROVED"

    stop_r = await client.post("/api/v1/experiments/status/stop-review", headers=expr_hdrs,
                                json={"code": "exp_button_color"})
    assert stop_r.status_code == 202
    assert stop_r.json()["status"] == "APPROVED"


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-07: APPROVED → RUNNING
# ─────────────────────────────────────────────────────────────────────────────
async def test_approved_to_running(
    client: AsyncClient, admin_user, experimenter_user, roles,  # добавь experimenter_user
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs  = await auth_headers(client, "experimenter@test.ru", "exprpass")
    result = await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)
    assert result["status"] == "RUNNING"


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-08: второй эксперимент на тот же флаг блокируется
# ─────────────────────────────────────────────────────────────────────────────
async def test_second_experiment_same_flag_blocked(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    # Второй эксперимент на тот же флаг
    payload2 = {**EXP_PAYLOAD, "code": "exp_button_color_v2",
                "variants": [
                    {"name": "ctrl", "value": "green", "weight": 50, "isControl": True},
                    {"name": "var",  "value": "red",   "weight": 50, "isControl": False},
                ]}
    await client.post("/api/v1/experiments", headers=expr_hdrs, json=payload2)
    await client.post("/api/v1/experiments/status/review", headers=expr_hdrs,
                      json={"code": "exp_button_color_v2"})
    await client.post("/api/v1/experiments/status/stop-review", headers=expr_hdrs,
                      json={"code": "exp_button_color_v2"})

    resp = await client.post("/api/v1/experiments/status/running", headers=expr_hdrs,
                              json={"code": "exp_button_color_v2"})
    assert resp.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-09: история версий
# ─────────────────────────────────────────────────────────────────────────────
async def test_experiment_history(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    resp = await client.get("/api/v1/experiments/history/exp_button_color", headers=admin_hdrs)
    assert resp.status_code == 200
    data = resp.json()
    versions = data.get("versions", [])
    assert len(versions) >= 1
    assert any(v["isCurrent"] for v in versions)


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-10: RUNNING → PAUSED → RUNNING
# ─────────────────────────────────────────────────────────────────────────────
async def test_pause_and_resume(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    # Пауза
    r = await client.post("/api/v1/experiments/status/paused", headers=expr_hdrs,
                          json={"code": "exp_button_color"})
    assert r.status_code == 202
    assert r.json()["status"] == "PAUSED"

    # Возобновление
    r2 = await client.post("/api/v1/experiments/status/running", headers=expr_hdrs,
                           json={"code": "exp_button_color"})
    assert r2.status_code == 202
    assert r2.json()["status"] == "RUNNING"


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-11: без контрольного варианта → 422
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_experiment_no_control_variant(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog
):
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    payload = {**EXP_PAYLOAD, "variants": [
        {"name": "var1", "value": "blue",   "weight": 50, "isControl": False},
        {"name": "var2", "value": "yellow", "weight": 50, "isControl": False},
    ]}
    resp = await client.post("/api/v1/experiments", headers=expr_hdrs, json=payload)
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-12: sum(weights) != part → 422
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_experiment_weight_mismatch(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog
):
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    payload = {**EXP_PAYLOAD, "part": 50, "variants": [
        {"name": "ctrl", "value": "green", "weight": 20, "isControl": True},
        {"name": "var",  "value": "blue",  "weight": 20, "isControl": False},
    ]}
    resp = await client.post("/api/v1/experiments", headers=expr_hdrs, json=payload)
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-13: несуществующий flag_code → 404/422
# ─────────────────────────────────────────────────────────────────────────────
async def test_create_experiment_nonexistent_flag(
    client: AsyncClient, admin_user, experimenter_user, roles, base_metrics_catalog
):
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    payload = {**EXP_PAYLOAD, "flag_code": "nonexistent_flag"}
    resp = await client.post("/api/v1/experiments", headers=expr_hdrs, json=payload)
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# T-EXP-14: просмотр ревью
# ─────────────────────────────────────────────────────────────────────────────
async def test_get_all_reviews(
    client: AsyncClient, admin_user, experimenter_with_required, approver_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    appr_hdrs  = await auth_headers(client, "approver@test.ru", "apprpass")

    await client.post("/api/v1/users/approvers", headers=admin_hdrs, json={
        "experimenter_id": str(experimenter_with_required.id),
        "approver_id": str(approver_user.id),
    })

    expr_hdrs = await auth_headers(client, "experimenter_req@test.ru", "exprreqpass")
    await client.post("/api/v1/experiments", headers=expr_hdrs, json=EXP_PAYLOAD)
    await client.post("/api/v1/experiments/status/review", headers=expr_hdrs,
                      json={"code": "exp_button_color"})
    await client.post("/api/v1/reviews", headers=appr_hdrs, json={
        "experiment_code": "exp_button_color",
        "result": "APPROVED",
        "comment": "ok",
    })

    resp = await client.get("/api/v1/reviews/all/exp_button_color", headers=admin_hdrs)
    assert resp.status_code == 200
    data = resp.json()
    assert data["required"] == 1
    assert any(r["result"] == "APPROVED" for r in data["items"])
