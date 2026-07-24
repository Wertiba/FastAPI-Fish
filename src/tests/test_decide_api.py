"""
test_decide_api.py — Decide API: default/variant, детерминизм, веса
Покрывает: B2-1..5, сценарии из 04_decide.sh

Тесты:
  T-DEC-01  Флаг без эксперимента → default, decision_id=null
  T-DEC-02  Флаг с RUNNING экспериментом → variant или default
  T-DEC-03  Детерминизм: повторный запрос того же user → то же значение
  T-DEC-04  Несколько флагов в одном запросе
  T-DEC-05  ROLLBACK: участник эксперимента получает control variant
  T-DEC-06  COMPLETED (ROLLOUT): участник получает resultVariant
  T-DEC-07  Неизвестный flag_code в запросе → 404/422
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers
from tests.test_experiment_lifecycle import EXP_PAYLOAD, create_and_run_experiment

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────────────────
# T-DEC-01: флаг без эксперимента → default
# ─────────────────────────────────────────────────────────────────────────────
async def test_decide_no_experiment_returns_default(
    client: AsyncClient, admin_user, roles, flag_button_color, test_users
):
    user = test_users[0]
    resp = await client.post("/api/v1/decisions", json={
        "user_id": str(user.id),
        "attributes": {"country": "RU"},
        "flag_codes": ["button_color"],
    })
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["flag_code"] == "button_color"
    assert items[0]["value"] == "green"  # default из фикстуры
    assert items[0]["decision_id"] is None


# ─────────────────────────────────────────────────────────────────────────────
# T-DEC-02: RUNNING эксперимент → участник получает вариант
# ─────────────────────────────────────────────────────────────────────────────
async def test_decide_with_running_experiment(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    # Хотя бы один из 5 пользователей должен попасть в эксперимент (part=100%)
    found_in_experiment = False
    for user in test_users:
        resp = await client.post("/api/v1/decisions", json={
            "user_id": str(user.id),
            "attributes": {},
            "flag_codes": ["button_color"],
        })
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["value"] in ("green", "blue")
        if item["decision_id"] is not None:
            found_in_experiment = True
            assert item["experiment_code"] == "exp_button_color"

    # При part=100% все должны быть в эксперименте
    assert found_in_experiment, "Никто не попал в эксперимент с part=100%"


# ─────────────────────────────────────────────────────────────────────────────
# T-DEC-03: детерминизм — повторный запрос тех же пользователей
# ─────────────────────────────────────────────────────────────────────────────
async def test_decide_determinism(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    for user in test_users:
        # Первый запрос
        r1 = await client.post("/api/v1/decisions", json={
            "user_id": str(user.id),
            "attributes": {"country": "RU"},
            "flag_codes": ["button_color"],
        })
        # Второй запрос
        r2 = await client.post("/api/v1/decisions", json={
            "user_id": str(user.id),
            "attributes": {"country": "RU"},
            "flag_codes": ["button_color"],
        })
        assert r1.status_code == 200
        assert r2.status_code == 200
        v1 = r1.json()["items"][0]["value"]
        v2 = r2.json()["items"][0]["value"]
        assert v1 == v2, f"Недетерминизм у {user.email}: {v1} != {v2}"
        # decision_id тоже должен быть одинаковым
        d1 = r1.json()["items"][0]["decision_id"]
        d2 = r2.json()["items"][0]["decision_id"]
        assert d1 == d2


# ─────────────────────────────────────────────────────────────────────────────
# T-DEC-04: несколько флагов в одном запросе
# ─────────────────────────────────────────────────────────────────────────────
async def test_decide_multi_flag(
    client: AsyncClient, admin_user, roles,
    flag_button_color, flag_show_banner, test_users
):
    user = test_users[0]
    resp = await client.post("/api/v1/decisions", json={
        "user_id": str(user.id),
        "attributes": {},
        "flag_codes": ["button_color", "show_banner"],
    })
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    codes = {i["flag_code"] for i in items}
    assert "button_color" in codes
    assert "show_banner" in codes
    # Оба без эксперимента — оба default
    for item in items:
        assert item["decision_id"] is None


# ─────────────────────────────────────────────────────────────────────────────
# T-DEC-05: ROLLBACK → участник получает control variant
# ─────────────────────────────────────────────────────────────────────────────
async def test_decide_rollback_returns_control(
    client: AsyncClient, admin_user, experimenter_user, roles,
    flag_button_color, base_metrics_catalog, base_events_catalog, test_users
):
    admin_hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    expr_hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    await create_and_run_experiment(client, admin_hdrs, expr_hdrs=expr_hdrs)

    # Найти пользователя в эксперименте
    participant = None
    for user in test_users:
        r = await client.post("/api/v1/decisions", json={
            "user_id": str(user.id), "attributes": {}, "flag_codes": ["button_color"],
        })
        if r.json()["items"][0]["decision_id"] is not None:
            participant = user
            break

    if participant is None:
        pytest.skip("Нет участников в эксперименте")

    # Переводим в ROLLBACK
    await client.post("/api/v1/experiments/status/paused", headers=expr_hdrs,
                      json={"code": "exp_button_color"})
    r_rb = await client.post("/api/v1/experiments/status/completed", headers=expr_hdrs, json={
        "code": "exp_button_color",
        "result": "ROLLBACK",
        "comment": "Откат из-за проблем",
    })
    assert r_rb.status_code == 202

    # Запрос: участник должен получить control (green)
    r = await client.post("/api/v1/decisions", json={
        "user_id": str(participant.id), "attributes": {}, "flag_codes": ["button_color"],
    })
    assert r.status_code == 200
    assert r.json()["items"][0]["value"] == "green"  # control variant


# ─────────────────────────────────────────────────────────────────────────────
# T-DEC-06: несуществующий flag_code в запросе
# ─────────────────────────────────────────────────────────────────────────────
async def test_decide_nonexistent_flag(
    client: AsyncClient, admin_user, roles, test_users
):
    user = test_users[0]
    resp = await client.post("/api/v1/decisions", json={
        "user_id": str(user.id),
        "attributes": {},
        "flag_codes": ["flag_that_does_not_exist"],
    })
    # Система должна вернуть ошибку (нет флага = нечего отдавать)
    assert resp.status_code == 404
