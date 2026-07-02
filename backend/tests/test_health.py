from fastapi.testclient import TestClient

from app.main import create_app


def test_app_importable():
    from app.main import app  # noqa: F401


def test_health_returns_ok():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "codize-backend"
    assert body["environment"] == "development"


def test_unknown_route_uses_error_shape():
    client = TestClient(create_app())
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.json() == {"error": {"status": 404, "message": "Not Found"}}
