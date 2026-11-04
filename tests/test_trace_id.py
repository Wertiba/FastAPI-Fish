def test_response_always_includes_trace_id_header(client):
    response = client.get("/health/liveness")
    assert "x-trace-id" in {k.lower() for k in response.headers}


def test_trace_id_header_is_echoed_back_when_provided(client):
    response = client.get("/health/liveness", headers={"X-Trace-Id": "fixed-trace-1"})
    assert response.headers["x-trace-id"] == "fixed-trace-1"


def test_error_response_trace_id_matches_request_header(client):
    response = client.get("/api/v1/users/me", headers={"X-Trace-Id": "fixed-trace-2"})
    assert response.status_code == 401
    assert response.headers["x-trace-id"] == "fixed-trace-2"
    assert response.json()["traceId"] == "fixed-trace-2"


def test_cors_allows_configured_origin(client):
    response = client.get("/health/liveness", headers={"Origin": "http://localhost"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost"


def test_cors_rejects_unconfigured_origin(client):
    response = client.get("/health/liveness", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_validation_error_accepts_non_uuid_trace_id(client):
    response = client.post("/api/v1/auth/login", json={}, headers={"X-Trace-Id": "my-trace-123"})
    assert response.status_code == 422
    assert response.json()["traceId"] == "my-trace-123"
