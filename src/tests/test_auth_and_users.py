"""
test_auth_and_users.py — Авторизация и управление пользователями
Покрывает: B1-5, B3-5 (роли), сценарии из 01_setup.sh

Тесты:
  T-AUTH-01  Успешный логин Admin
  T-AUTH-02  Логин с неверным паролем
  T-AUTH-03  Логин несуществующего пользователя
  T-AUTH-04  Создание пользователей всех ролей (Admin)
  T-AUTH-05  Создание пользователя без прав (Experimenter → 403)
  T-AUTH-06  Дублирование email при создании
  T-AUTH-07  Назначение approver-группы
  T-AUTH-08  Запрос к защищённому ресурсу без токена → 401
  T-AUTH-09  Запрос с невалидным JWT → 401
  T-AUTH-10  Просмотр списка пользователей (Admin)
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


# ── T-AUTH-01: успешный логин ─────────────────────────────────────────────────
async def test_login_admin_success(client: AsyncClient, admin_user, roles):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.ru",
        "password": "adminpass",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "accessToken" in data
    assert data["accessToken"]
    assert data["user"]["email"] == "admin@test.ru"
    assert any(r["code"] == "ADMN" for r in data["user"]["roles"])


# ── T-AUTH-02: неверный пароль ────────────────────────────────────────────────
async def test_login_wrong_password(client: AsyncClient, admin_user, roles):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.ru",
        "password": "WRONG",
    })
    assert resp.status_code == 401


# ── T-AUTH-03: несуществующий пользователь ────────────────────────────────────
async def test_login_nonexistent_user(client: AsyncClient, roles):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.ru",
        "password": "somepass",
    })
    assert resp.status_code == 404


# ── T-AUTH-04: создание пользователей всех ролей ─────────────────────────────
@pytest.mark.parametrize("role,email", [
    ("EXPR", "expr2@test.ru"),
    ("APPR", "appr2@test.ru"),
    ("VIEW", "view2@test.ru"),
])
async def test_create_user_all_roles(client: AsyncClient, admin_user, roles, role, email):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/users", headers=hdrs, json={
        "email": email,
        "password": "password123",
        "fullName": f"Test {role}",
        "roles": [role],
        "required": 0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    assert any(r["code"] == role for r in data["roles"])


# ── T-AUTH-05: создание пользователя без прав (EXPR → 403) ───────────────────
async def test_create_user_forbidden_for_experimenter(client: AsyncClient, experimenter_user, roles):
    hdrs = await auth_headers(client, "experimenter@test.ru", "exprpass")
    resp = await client.post("/api/v1/users", headers=hdrs, json={
        "email": "hacker@evil.ru",
        "password": "hacked123",
        "fullName": "Hacker",
        "roles": ["ADMN"],
        "required": 0,
    })
    # EXPR не является ADMN — должен получить 403
    assert resp.status_code == 403


# ── T-AUTH-06: дублирование email ────────────────────────────────────────────
async def test_create_user_duplicate_email(client: AsyncClient, admin_user, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    payload = {
        "email": "dup@test.ru",
        "password": "pass12345",
        "fullName": "First",
        "roles": ["VIEW"],
        "required": 0,
    }
    r1 = await client.post("/api/v1/users", headers=hdrs, json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/users", headers=hdrs, json=payload)
    assert r2.status_code in (409, 422)


# ── T-AUTH-07: назначение approver-группы ────────────────────────────────────
async def test_assign_approver(client: AsyncClient, admin_user, experimenter_user, approver_user, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.post("/api/v1/users/approvers", headers=hdrs, json={
        "experimenter_id": str(experimenter_user.id),
        "approver_id": str(approver_user.id),
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["experimenter_id"] == str(experimenter_user.id)
    assert data["approver_id"] == str(approver_user.id)


# ── T-AUTH-08: без токена → 401 ───────────────────────────────────────────────
async def test_no_token_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/flags")
    assert resp.status_code == 401


# ── T-AUTH-09: невалидный JWT → 401 ──────────────────────────────────────────
async def test_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/flags", headers={"Authorization": "Bearer totally.invalid.jwt"})
    assert resp.status_code == 401


# ── T-AUTH-10: просмотр списка пользователей ─────────────────────────────────
async def test_list_users(client: AsyncClient, admin_user, experimenter_user, roles):
    hdrs = await auth_headers(client, "admin@test.ru", "adminpass")
    resp = await client.get("/api/v1/users", headers=hdrs)
    assert resp.status_code == 200
    data = resp.json()
    emails = [u["email"] for u in data.get("items", [])]
    assert "admin@test.ru" in emails
    assert "experimenter@test.ru" in emails
