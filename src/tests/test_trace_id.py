def test_response_always_includes_trace_id_header(client):
    response = client.get("/api/v1/ping")
    assert "x-trace-id" in {k.lower() for k in response.headers}


def test_trace_id_header_is_echoed_back_when_provided(client):
    response = client.get("/api/v1/ping", headers={"X-Trace-Id": "fixed-trace-1"})
    assert response.headers["x-trace-id"] == "fixed-trace-1"


def test_error_response_trace_id_matches_request_header(client):
    response = client.get("/api/v1/users/me", headers={"X-Trace-Id": "fixed-trace-2"})
    assert response.status_code == 401
    assert response.headers["x-trace-id"] == "fixed-trace-2"
    assert response.json()["traceId"] == "fixed-trace-2"
