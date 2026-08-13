import pytest

pytestmark = pytest.mark.integration


async def test_admin_can_list_paginate_and_filter_users(client, admin_headers):
    for i in range(3):
        await client.post(
            "/api/v1/users",
            json={"email": f"user{i}@fish.io", "password": "password1", "fullName": f"User {i}"},
            headers=admin_headers,
        )

    page = await client.get("/api/v1/users?page=0&size=2", headers=admin_headers)
    assert page.status_code == 200
    page_body = page.json()
    assert page_body["total"] >= 4  # 3 created here + the admin itself
    assert len(page_body["items"]) == 2

    filtered = await client.get("/api/v1/users?email=user1", headers=admin_headers)
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["total"] == 1
    assert filtered_body["items"][0]["email"] == "user1@fish.io"


async def test_non_admin_cannot_change_own_role(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "self@fish.io", "password": "password1", "fullName": "Self Fish"},
    )
    access_token = register.json()["accessToken"]
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.put(
        "/api/v1/users/me",
        json={"fullName": "Self Fish", "role": "ADMIN", "isActive": True},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


async def test_admin_deactivating_user_revokes_their_refresh_token(client, admin_headers):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "revoke@fish.io", "password": "password1", "fullName": "Revoke Fish"},
    )
    user_id = register.json()["user"]["id"]
    refresh_cookie = register.cookies["refreshToken"]

    deactivate = await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert deactivate.status_code == 204

    client.cookies.set("refreshToken", refresh_cookie)
    refresh_attempt = await client.post("/api/v1/auth/refresh")
    assert refresh_attempt.status_code == 401
