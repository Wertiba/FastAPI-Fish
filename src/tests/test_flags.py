"""
test_flags.py — Feature Flags CRUD
Покрывает: B2-1 (default), сценарии из 02_flags.sh

Тесты:
  T-FLAG-01  Создание STRING флага (Admin)
  T-FLAG-02  Создание BOOL флага
  T-FLAG-03  Создание NUMBER флага
  T-FLAG-04  Получение флага по коду
  T-FLAG-05  Список флагов
  T-FLAG-06  Обновление default-значения
  T-FLAG-07  Дублирующийся код флага → ошибка
  T-FLAG-08  Создание флага Viewer'ом → 403
  T-FLAG-09  Несуществующий флаг → 404/422
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


# ── T-FLAG-01: создание STRING флага ─────────────────────────────────────────
async def test_create_string_flag(client: AsyncClient, admin_user, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/flags", headers=hdrs, json={
        "code": "button_color",
        "default": "green",
        "type": "STRING",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "button_color"
    assert data["default"] == "green"
    assert data["type"] == "STRING"
    assert "id" in data


# ── T-FLAG-02: создание BOOL флага ───────────────────────────────────────────
async def test_create_bool_flag(client: AsyncClient, admin_user, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/flags", headers=hdrs, json={
        "code": "show_banner",
        "default": "false",
        "type": "BOOL",
    })
    assert resp.status_code == 201
    assert resp.json()["type"] == "BOOL"


# ── T-FLAG-03: создание NUMBER флага ─────────────────────────────────────────
async def test_create_number_flag(client: AsyncClient, admin_user, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/flags", headers=hdrs, json={
        "code": "checkout_timeout_ms",
        "default": "3000",
        "type": "NUMBER",
    })
    assert resp.status_code == 201
    assert resp.json()["type"] == "NUMBER"


# ── T-FLAG-04: получение флага по коду ───────────────────────────────────────
async def test_get_flag_by_code(client: AsyncClient, admin_user, flag_button_color, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.get("/api/v1/flags/button_color", headers=hdrs)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "button_color"
    assert data["default"] == "green"


# ── T-FLAG-05: список флагов ──────────────────────────────────────────────────
async def test_list_flags(client: AsyncClient, admin_user, flag_button_color, flag_show_banner, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.get("/api/v1/flags", headers=hdrs)
    assert resp.status_code == 200
    codes = [f["code"] for f in resp.json().get("items", [])]
    assert "button_color" in codes
    assert "show_banner" in codes


# ── T-FLAG-06: обновление default-значения ───────────────────────────────────
async def test_update_flag_default(client: AsyncClient, admin_user, flag_button_color, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.patch("/api/v1/flags/button_color", headers=hdrs, json={
        "default": "blue",
    })
    assert resp.status_code == 200
    assert resp.json()["default"] == "blue"

    # Проверяем, что значение действительно изменилось
    get_resp = await client.get("/api/v1/flags/button_color", headers=hdrs)
    assert get_resp.json()["default"] == "blue"


# ── T-FLAG-07: дублирующийся код флага ───────────────────────────────────────
async def test_create_duplicate_flag_code(client: AsyncClient, admin_user, flag_button_color, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/flags", headers=hdrs, json={
        "code": "button_color",
        "default": "red",
        "type": "STRING",
    })
    assert resp.status_code in (409, 422)


# ── T-FLAG-08: создание флага Viewer'ом → 403 ────────────────────────────────
async def test_create_flag_by_viewer_forbidden(client: AsyncClient, viewer_user, roles):
    hdrs = await auth_headers(client, "viewer@test.ru", "viewpass")
    resp = await client.post("/api/v1/flags", headers=hdrs, json={
        "code": "flag_by_viewer",
        "default": "x",
        "type": "STRING",
    })
    assert resp.status_code == 403


# ── T-FLAG-09: несуществующий флаг → 404/422 ─────────────────────────────────
async def test_get_nonexistent_flag(client: AsyncClient, admin_user, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.get("/api/v1/flags/nonexistent_flag_xyz", headers=hdrs)
    assert resp.status_code in (404, 422)
