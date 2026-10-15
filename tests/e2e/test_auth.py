from fastapi.testclient import TestClient
from httpx import Response

from tests.conftest import ADMIN_EMAIL, USER_PASSWORD, RegisterUser


def post_with_refresh(client: TestClient, action: str, refresh_token: str) -> Response:
    client.cookies.clear()
    client.cookies.set("refreshToken", refresh_token)
    return client.post(f"/api/v1/auth/{action}")


def test_register_returns_user_tokens_cookie_and_location(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "secret-pass-1", "fullName": "Новый Юзер"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["accessToken"]
    assert body["expiresIn"] == 900
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["role"] == "USER"
    assert body["user"]["createdBy"] == body["user"]["id"]
    assert body["user"]["createdAt"].endswith("Z")
    assert response.headers["Location"] == f"/api/v1/users/{body['user']['id']}"
    assert "refreshToken" in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()


def test_register_duplicate_email_is_409(client: TestClient, register_user: RegisterUser) -> None:
    register_user(email="dup@example.com")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "secret-pass-1", "fullName": "Dup"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "EMAIL_ALREADY_EXISTS"
    assert body["details"] == {"field": "email", "value": "dup@example.com"}
    assert body["traceId"] == response.headers["X-Trace-Id"]


def test_register_validation_error_format(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={"email": "bad", "password": "short"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    fields = {error["field"] for error in body["fieldErrors"]}
    assert fields == {"email", "password", "fullName"}


def test_login_success_and_failures(client: TestClient, register_user: RegisterUser) -> None:
    user = register_user()
    email = user["user"]["email"]

    ok = client.post("/api/v1/auth/login", json={"email": email, "password": USER_PASSWORD})
    wrong = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-pass-1"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x"})

    assert ok.status_code == 200
    assert ok.json()["user"]["id"] == user["user"]["id"]
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json()["code"] == unknown.json()["code"] == "UNAUTHORIZED"


def test_login_inactive_user_is_423(
    client: TestClient, register_user: RegisterUser, admin_headers: dict[str, str]
) -> None:
    user = register_user()
    client.delete(f"/api/v1/users/{user['user']['id']}", headers=admin_headers)

    response = client.post(
        "/api/v1/auth/login", json={"email": user["user"]["email"], "password": USER_PASSWORD}
    )

    assert response.status_code == 423
    assert response.json()["code"] == "USER_INACTIVE"


def test_refresh_rotates_token(client: TestClient, register_user: RegisterUser) -> None:
    old_token = register_user()["refreshToken"]

    first = post_with_refresh(client, "refresh", old_token)
    reused = post_with_refresh(client, "refresh", old_token)

    assert first.status_code == 200
    assert set(first.json()) == {"accessToken", "expiresIn"}
    assert first.cookies["refreshToken"] != old_token
    assert reused.status_code == 401


def test_refresh_without_cookie_is_401(client: TestClient) -> None:
    client.cookies.clear()
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_rejects_access_token(client: TestClient, register_user: RegisterUser) -> None:
    user = register_user()
    response = post_with_refresh(client, "refresh", user["accessToken"])
    assert response.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient, register_user: RegisterUser) -> None:
    token = register_user()["refreshToken"]

    logout = post_with_refresh(client, "logout", token)
    refresh = post_with_refresh(client, "refresh", token)

    assert logout.status_code == 204
    assert refresh.status_code == 401


def test_deactivation_revokes_sessions_via_event(
    client: TestClient, register_user: RegisterUser, admin_headers: dict[str, str]
) -> None:
    """users публикует UserDeactivated -> auth удаляет refresh-токены.

    После повторной активации старый токен всё равно не работает: значит,
    его удалил обработчик события, а не проверка is_active.
    """
    user = register_user()
    user_id = user["user"]["id"]

    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    client.put(f"/api/v1/users/{user_id}", headers=admin_headers, json={"fullName": "Back", "isActive": True})
    response = post_with_refresh(client, "refresh", user["refreshToken"])

    assert response.status_code == 401


def test_admin_is_bootstrapped(client: TestClient, admin_headers: dict[str, str]) -> None:
    me = client.get("/api/v1/users/me", headers=admin_headers).json()
    assert me["email"] == ADMIN_EMAIL
    assert me["role"] == "ADMIN"
