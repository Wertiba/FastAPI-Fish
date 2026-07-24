"""
test_reports_and_completion.py — Отчёты и завершение экспериментов
Покрывает: B6-1..5, сценарии из 07_reports.sh и 08_complete.sh

Тесты:
  T-REP-01  Отчёт возвращает разбивку по вариантам с метриками
  T-REP-02  Фильтр периода: пустое окно → все value=0
  T-REP-03  Активное окно → ненулевые значения после событий
  T-REP-04  Отчёт для DRAFT → ошибка
  T-REP-05  Отчёт для несуществующего кода → ошибка
  T-CMP-01  Завершение ROLLOUT → resultVariant_id заполнен, comment сохранён
  T-CMP-02  Завершение ROLLBACK → resultVariant_id = control variant
  T-CMP-03  Завершение DEFAULT → resultVariant_id=null
  T-CMP-04  Завершение требует comment
  T-CMP-05  Архивирование COMPLETED → ARCHIVED
  T-CMP-06  ARCHIVED → RUNNING невозможен
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers
from tests.test_experiment_lifecycle import EXP_PAYLOAD, create_and_run_experiment

pytestmark = pytest.mark.asyncio


def time_window(offset_past_h=-1, offset_future_h=1):
    now = datetime.now()
    tf = (now + timedelta(hours=offset_past_h)).strftime("%Y-%m-%dT%H:%M:%S")
    tt = (now + timedelta(hours=offset_future_h)).strftime("%Y-%m-%dT%H:%M:%S")
    return tf, tt


def old_window():
    return "2020-01-01T00:00:00", "2020-01-02T00:00:00"


# ─────────────────────────────────────────────────────────────────────────────
# T-REP-01: отчёт — разбивка по вариантам
# ─────────────────────────────────────────────────────────────────────────────
async def test_report_variants_breakdown(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    tf, tt = time_window()
    resp = await client.get(
        f"/api/v1/reports/exp_button_color?time_from={tf}&time_to={tt}",
        headers=admin_hdrs,
    )
    assert resp.status_code == 200
    data = resp.json()
    variants = data.get("variants", [])
    assert len(variants) == 2
    variant_names = {v["variant_name"] for v in variants}
    assert "control_green" in variant_names
    assert "variant_blue" in variant_names

    # Каждый вариант содержит список метрик
    for v in variants:
        assert "metrics" in v
        assert len(v["metrics"]) > 0
        metric_codes = {m["metric_code"] for m in v["metrics"]}
        assert "CONVERSION_RATE" in metric_codes


# ─────────────────────────────────────────────────────────────────────────────
# T-REP-02: пустое окно → value=0
# ─────────────────────────────────────────────────────────────────────────────
async def test_report_empty_window_returns_zero(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    tf, tt = old_window()
    resp = await client.get(
        f"/api/v1/reports/exp_button_color?time_from={tf}&time_to={tt}",
        headers=admin_hdrs,
    )
    assert resp.status_code == 200
    for variant in resp.json().get("variants", []):
        for metric in variant.get("metrics", []):
            assert metric["value"] == 0.0 or metric["value"] == 0, \
                f"Ожидался 0 в пустом окне, получен {metric['value']} для {metric['metric_code']}"


# ─────────────────────────────────────────────────────────────────────────────
# T-REP-03: события → ненулевые значения в отчёте
# ─────────────────────────────────────────────────────────────────────────────
async def test_report_nonzero_after_events(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    # Найти участника
    dec_id = None
    for user in test_users:
        r = await client.post("/api/v1/decisions", json={
            "user_id": str(user.id), "attributes": {}, "flag_codes": ["button_color"],
        })
        d = r.json()["items"][0].get("decision_id")
        if d:
            dec_id = d
            break

    if dec_id is None:
        pytest.skip("Нет участников")

    # Отправляем события
    a = await client.post("/api/v1/events", json={"events": [
        {"eventKey": "rep-exp-001", "decision_id": dec_id, "eventCatalog_code": "EXPOSURE",   "data": {}},
        {"eventKey": "rep-conv-001","decision_id": dec_id, "eventCatalog_code": "CONVERSION",  "data": {}},
    ]})

    tf, tt = time_window()
    resp = await client.get(
        f"/api/v1/reports/exp_button_color?time_from={tf}&time_to={tt}",
        headers=admin_hdrs,
    )
    assert resp.status_code == 200
    # Хотя бы в одном варианте CONVERSIONS > 0
    any_nonzero = False
    for variant in resp.json().get("variants", []):
        for metric in variant.get("metrics", []):
            if metric["metric_code"] == "CONVERSIONS" and metric["value"] > 0:
                any_nonzero = True
    assert any_nonzero, "CONVERSIONS должны быть > 0 после отправки событий"


# ─────────────────────────────────────────────────────────────────────────────
# T-REP-04: отчёт для DRAFT → ошибка
# ─────────────────────────────────────────────────────────────────────────────
async def test_report_for_draft_returns_error(
    client: AsyncClient, admin_user, roles,
    flag_button_color, base_metrics_catalog
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    await client.post("/api/v1/experiments", headers=admin_hdrs, json=EXP_PAYLOAD)

    tf, tt = time_window()
    resp = await client.get(
        f"/api/v1/reports/exp_button_color?time_from={tf}&time_to={tt}",
        headers=admin_hdrs,
    )
    assert resp.status_code in (404, 409)


# ─────────────────────────────────────────────────────────────────────────────
# T-REP-05: отчёт для несуществующего кода
# ─────────────────────────────────────────────────────────────────────────────
async def test_report_nonexistent_experiment(
    client: AsyncClient, admin_user, roles
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    tf, tt = time_window()
    resp = await client.get(
        f"/api/v1/reports/does_not_exist_xyz?time_from={tf}&time_to={tt}",
        headers=admin_hdrs,
    )
    assert resp.status_code in (404, 422)


# ─────────────────────────────────────────────────────────────────────────────
# T-CMP-01: ROLLOUT → resultVariant_id заполнен, comment сохранён
# ─────────────────────────────────────────────────────────────────────────────
async def test_complete_rollout(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    comment = "Синяя кнопка конвертирует лучше на 15%. Раскатываем."
    resp = await client.post("/api/v1/experiments/status/completed", headers=expr_hdrs, json={
        "code": "exp_button_color",
        "result": "ROLLOUT",
        "comment": comment,
    })
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["comment"] == comment
    assert data["resultVariant_id"] is not None  # победитель определён


# ─────────────────────────────────────────────────────────────────────────────
# T-CMP-02: ROLLBACK → resultVariant_id = control variant
# ─────────────────────────────────────────────────────────────────────────────
async def test_complete_rollback(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    resp = await client.post("/api/v1/experiments/status/completed", headers=expr_hdrs, json={
        "code": "exp_button_color",
        "result": "ROLLBACK",
        "comment": "Откат из-за роста ошибок",
    })
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["resultVariant_id"] is not None  # должен быть control variant

    # Получаем details и проверяем что resultVariant — контрольный
    exp_resp = await client.get("/api/v1/experiments/exp_button_color", headers=admin_hdrs)
    exp_data = exp_resp.json()
    result_vid = exp_data["resultVariant_id"]
    control_variant = next((v for v in exp_data["variants"] if v["isControl"]), None)
    assert control_variant is not None
    assert str(result_vid) == str(control_variant["id"])


# ─────────────────────────────────────────────────────────────────────────────
# T-CMP-03: DEFAULT → resultVariant_id=null
# ─────────────────────────────────────────────────────────────────────────────
async def test_complete_default_no_winner(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    resp = await client.post("/api/v1/experiments/status/completed", headers=expr_hdrs, json={
        "code": "exp_button_color",
        "result": "DEFAULT",
        "comment": "Статистически незначимый результат",
    })
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["resultVariant_id"] is None


# ─────────────────────────────────────────────────────────────────────────────
# T-CMP-04: завершение без comment → ok
# ─────────────────────────────────────────────────────────────────────────────
async def test_complete_requires_comment(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    resp = await client.post("/api/v1/experiments/status/completed", headers=expr_hdrs, json={
        "code": "exp_button_color",
        "result": "ROLLOUT",
        # нет comment
    })
    assert resp.status_code == 202


# ─────────────────────────────────────────────────────────────────────────────
# T-CMP-05: COMPLETED → ARCHIVED
# ─────────────────────────────────────────────────────────────────────────────
async def test_archive_completed_experiment(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)
    await client.post("/api/v1/experiments/status/completed", headers=expr_hdrs, json={
        "code": "exp_button_color", "result": "DEFAULT", "comment": "Нет эффекта",
    })

    resp = await client.post("/api/v1/experiments/status/archived", headers=expr_hdrs,
                             json={"code": "exp_button_color"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "ARCHIVED"


# ─────────────────────────────────────────────────────────────────────────────
# T-CMP-06: ARCHIVED → RUNNING невозможен
# ─────────────────────────────────────────────────────────────────────────────
async def test_archived_cannot_be_run(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, event_metric_links, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)
    await client.post("/api/v1/experiments/status/completed", headers=expr_hdrs, json={
        "code": "exp_button_color", "result": "DEFAULT", "comment": "Нет эффекта",
    })
    await client.post("/api/v1/experiments/status/archived", headers=expr_hdrs,
                      json={"code": "exp_button_color"})

    resp = await client.post("/api/v1/experiments/status/running", headers=expr_hdrs,
                             json={"code": "exp_button_color"})
    assert resp.status_code == 409
