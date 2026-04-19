"""HTTP API smoke tests for auth and error response shape."""
import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"


def test_chat_requires_authentication(client):
    r = client.post("/chat", data={"message": "hello"})
    assert r.status_code == 401


def test_http_error_json_shape(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
    body = r.json()
    assert "detail" in body
    assert "code" in body
