from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import RegisterUser


def test_protected_endpoints_require_token(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    invalid = client.get("/api/v1/users/me", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert invalid.status_code == 401


def test_list_users_is_admin_only(
    client: TestClient, register_user: RegisterUser, admin_headers: dict[str, str]
) -> None:
    user = register_user()

    assert client.get("/api/v1/users", headers=user["headers"]).status_code == 403
    response = client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_list_users_pagination_and_filters(
    client: TestClient, register_user: RegisterUser, admin_headers: dict[str, str]
) -> None:
    for i in range(3):
        register_user(email=f"alpha{i}@example.com", full_name=f"Alpha {i}")
    register_user(email="beta@example.com", full_name="Beta")

    page = client.get("/api/v1/users", params={"page": 1, "size": 2}, headers=admin_headers).json()
    alphas = client.get("/api/v1/users", params={"email": "alpha"}, headers=admin_headers).json()
    admins = client.get("/api/v1/users", params={"role": "ADMIN"}, headers=admin_headers).json()
    by_name = client.get("/api/v1/users", params={"fullName": "bet"}, headers=admin_headers).json()

    assert (page["page"], page["size"], page["total"], len(page["items"])) == (1, 2, 5, 2)
    assert alphas["total"] == 3
    assert admins["total"] == 1
    assert [u["email"] for u in by_name["items"]] == ["beta@example.com"]


def test_pagination_limits_are_validated(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users", params={"size": 1000}, headers=admin_headers)
    assert response.status_code == 422
    assert response.json()["fieldErrors"][0]["field"] == "size"


def test_admin_creates_user(client: TestClient, admin_headers: dict[str, str]) -> None:
    admin_id = client.get("/api/v1/users/me", headers=admin_headers).json()["id"]

    response = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"email": "made@example.com", "password": "secret-pass-1", "fullName": "Made", "role": "ADMIN"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "ADMIN"
    assert response.json()["createdBy"] == admin_id


def test_user_cannot_create_users(client: TestClient, register_user: RegisterUser) -> None:
    user = register_user()
    response = client.post(
        "/api/v1/users",
        headers=user["headers"],
        json={"email": "x@example.com", "password": "secret-pass-1", "fullName": "Xx"},
    )
    assert response.status_code == 403


def test_user_reads_and_updates_self(client: TestClient, register_user: RegisterUser) -> None:
    user = register_user()

    me = client.get("/api/v1/users/me", headers=user["headers"])
    updated = client.put("/api/v1/users/me", headers=user["headers"], json={"fullName": "Renamed"})
    by_id = client.get(f"/api/v1/users/{user['user']['id']}", headers=user["headers"])

    assert me.json()["id"] == user["user"]["id"]
    assert updated.status_code == 200
    assert updated.json()["fullName"] == "Renamed"
    assert by_id.json()["fullName"] == "Renamed"


def test_user_cannot_escalate_own_role(client: TestClient, register_user: RegisterUser) -> None:
    user = register_user()
    response = client.put(
        "/api/v1/users/me", headers=user["headers"], json={"fullName": "Hacker", "role": "ADMIN"}
    )
    assert response.status_code == 403
    assert client.get("/api/v1/users/me", headers=user["headers"]).json()["role"] == "USER"


def test_user_cannot_access_other_users(client: TestClient, register_user: RegisterUser) -> None:
    alice, bob = register_user(), register_user()
    bob_url = f"/api/v1/users/{bob['user']['id']}"

    assert client.get(bob_url, headers=alice["headers"]).status_code == 403
    assert client.put(bob_url, headers=alice["headers"], json={"fullName": "Nope"}).status_code == 403
    assert client.delete(bob_url, headers=alice["headers"]).status_code == 403


def test_admin_manages_any_user(
    client: TestClient, register_user: RegisterUser, admin_headers: dict[str, str]
) -> None:
    user = register_user()
    url = f"/api/v1/users/{user['user']['id']}"

    promoted = client.put(url, headers=admin_headers, json={"fullName": "Promoted", "role": "ADMIN"})
    deleted = client.delete(url, headers=admin_headers)
    after = client.get(url, headers=admin_headers)

    assert promoted.json()["role"] == "ADMIN"
    assert deleted.status_code == 204
    assert after.json()["isActive"] is False


def test_deactivated_user_loses_access(
    client: TestClient, register_user: RegisterUser, admin_headers: dict[str, str]
) -> None:
    user = register_user()
    client.delete(f"/api/v1/users/{user['user']['id']}", headers=admin_headers)
    assert client.get("/api/v1/users/me", headers=user["headers"]).status_code == 401


def test_unknown_user_is_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    url = f"/api/v1/users/{uuid4()}"
    assert client.get(url, headers=admin_headers).json()["code"] == "NOT_FOUND"
    assert client.put(url, headers=admin_headers, json={"fullName": "X1"}).status_code == 404
    assert client.delete(url, headers=admin_headers).status_code == 404
