def test_register_returns_201_sets_cookie_and_location_header(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "flow@fish.io", "password": "password1", "fullName": "Flow Fish"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "flow@fish.io"
    assert body["user"]["role"] == "USER"
    assert response.headers["location"] == f"/api/v1/users/{body['user']['id']}"
    assert "refreshToken" in response.cookies


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@fish.io", "password": "password1", "fullName": "Fish"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "EMAIL_ALREADY_EXISTS"
    assert body["details"] == {"field": "email", "value": "dup@fish.io"}


def test_register_rejects_full_name_with_invalid_characters(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "badname@fish.io", "password": "password1", "fullName": "Fish!!!"},
    )
    assert response.status_code == 422


def test_register_accepts_cyrillic_full_name(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "cyrillic@fish.io", "password": "password1", "fullName": "Иван Иванов"},
    )
    assert response.status_code == 201


def test_login_returns_200_and_sets_refresh_cookie(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@fish.io", "password": "password1", "fullName": "Login Fish"},
    )

    response = client.post("/api/v1/auth/login", json={"email": "login@fish.io", "password": "password1"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "login@fish.io"
    assert "refreshToken" in response.cookies


def test_login_with_wrong_password_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "badpw@fish.io", "password": "password1", "fullName": "Fish"},
    )

    response = client.post("/api/v1/auth/login", json={"email": "badpw@fish.io", "password": "wrong-password"})
    assert response.status_code == 401


def test_refresh_rotates_cookie_and_invalidates_previous_refresh_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "rotate@fish.io", "password": "password1", "fullName": "Fish"},
    )
    old_refresh_cookie = register_response.cookies["refreshToken"]

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    assert "accessToken" in refresh_response.json()
    new_refresh_cookie = refresh_response.cookies["refreshToken"]
    assert new_refresh_cookie != old_refresh_cookie

    client.cookies.set("refreshToken", old_refresh_cookie)
    reuse_response = client.post("/api/v1/auth/refresh")
    assert reuse_response.status_code == 401


def test_refresh_without_cookie_returns_401(client):
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_logout_clears_cookie_and_revokes_refresh_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "logout@fish.io", "password": "password1", "fullName": "Fish"},
    )
    refresh_cookie = register_response.cookies["refreshToken"]

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    client.cookies.set("refreshToken", refresh_cookie)
    reuse_response = client.post("/api/v1/auth/refresh")
    assert reuse_response.status_code == 401


def test_logout_without_cookie_returns_401(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401
