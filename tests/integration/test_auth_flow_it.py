import pytest

pytestmark = pytest.mark.integration


async def test_full_auth_flow_against_real_postgres(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@fish.io", "password": "password1", "fullName": "Flow Fish"},
    )
    assert register.status_code == 201

    # login() issues its own refresh token without revoking register()'s (this app supports
    # concurrent multi-session refresh tokens per user) — the token about to be rotated below
    # is the one login() just issued, not register()'s, so that's the "old" token to capture.
    login = await client.post("/api/v1/auth/login", json={"email": "flow@fish.io", "password": "password1"})
    assert login.status_code == 200
    old_refresh = login.cookies["refreshToken"]

    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    new_refresh = refresh.cookies["refreshToken"]
    assert new_refresh != old_refresh

    client.cookies.set("refreshToken", old_refresh)
    reuse_of_rotated_token = await client.post("/api/v1/auth/refresh")
    assert reuse_of_rotated_token.status_code == 401

    client.cookies.set("refreshToken", new_refresh)
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    reuse_after_logout = await client.post("/api/v1/auth/refresh")
    assert reuse_after_logout.status_code == 401
