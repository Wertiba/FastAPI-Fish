def _register(client, email="user@fish.io", password="password1", full_name="Test User"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "fullName": full_name},
    )
    body = response.json()
    return body["user"]["id"], body["accessToken"]


def test_admin_can_create_user_with_arbitrary_role(client, admin_headers):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "created@fish.io",
            "password": "password1",
            "fullName": "Created Fish",
            "role": "ADMIN",
            "isActive": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "ADMIN"


def test_non_admin_cannot_create_user(client):
    _, access_token = _register(client)
    response = client.post(
        "/api/v1/users",
        json={"email": "x@fish.io", "password": "password1", "fullName": "X"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403


def test_self_can_read_and_update_own_profile(client):
    user_id, access_token = _register(client, email="self@fish.io")
    headers = {"Authorization": f"Bearer {access_token}"}

    get_response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "self@fish.io"

    put_response = client.put(f"/api/v1/users/{user_id}", json={"fullName": "Updated Name"}, headers=headers)
    assert put_response.status_code == 200
    assert put_response.json()["fullName"] == "Updated Name"


def test_me_endpoints_work_for_the_authenticated_user(client):
    _, access_token = _register(client, email="me@fish.io", full_name="Me Fish")
    headers = {"Authorization": f"Bearer {access_token}"}

    get_response = client.get("/api/v1/users/me", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "me@fish.io"

    put_response = client.put("/api/v1/users/me", json={"fullName": "New Me"}, headers=headers)
    assert put_response.status_code == 200
    assert put_response.json()["fullName"] == "New Me"


def test_self_cannot_read_or_update_another_user(client):
    other_id, _ = _register(client, email="other@fish.io")
    _, my_token = _register(client, email="me2@fish.io")
    headers = {"Authorization": f"Bearer {my_token}"}

    get_response = client.get(f"/api/v1/users/{other_id}", headers=headers)
    assert get_response.status_code == 403

    put_response = client.put(f"/api/v1/users/{other_id}", json={"fullName": "Hacked Name"}, headers=headers)
    assert put_response.status_code == 403


def test_self_cannot_escalate_own_role(client):
    user_id, access_token = _register(client, email="escalate@fish.io")
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.put(
        f"/api/v1/users/{user_id}", json={"fullName": "Still Me", "role": "ADMIN"}, headers=headers
    )
    assert response.status_code == 403


def test_admin_can_change_role_and_is_active(client, admin_headers):
    user_id, _ = _register(client, email="promote@fish.io")

    response = client.put(
        f"/api/v1/users/{user_id}",
        json={"fullName": "Promoted Fish", "role": "ADMIN", "isActive": True},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_admin_delete_soft_deactivates_and_revokes_refresh_tokens(client, admin_headers):
    user_id, _ = _register(client, email="delete@fish.io")
    refresh_cookie = client.cookies.get("refreshToken")

    delete_response = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert get_response.json()["isActive"] is False

    client.cookies.set("refreshToken", refresh_cookie)
    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401


def test_admin_lists_users_with_pagination_and_filters(client, admin_headers):
    _register(client, email="alice@fish.io", full_name="Alice Fisher")
    _register(client, email="bob@fish.io", full_name="Bob Carp")

    response = client.get("/api/v1/users", params={"email": "alice"}, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "alice@fish.io"


def test_non_admin_cannot_list_users(client):
    _, access_token = _register(client)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403


def test_create_user_rejects_duplicate_email_with_details(client, admin_headers):
    payload = {"email": "dup2@fish.io", "password": "password1", "fullName": "Fish Two"}
    client.post("/api/v1/users", json=payload, headers=admin_headers)
    response = client.post("/api/v1/users", json=payload, headers=admin_headers)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "EMAIL_ALREADY_EXISTS"
    assert body["details"] == {"field": "email", "value": "dup2@fish.io"}
