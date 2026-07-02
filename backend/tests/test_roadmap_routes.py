"""Roadmap route tests: auth-enforced, thin handlers, controlled errors.

Repository is overridden with the in-memory fake; auth uses the offline ES256
pattern. The LLM service is NOT overridden — no provider keys exist in the
test env, so the routes run the real no-key path: build_llm_service → stub.
"""

import time
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import get_settings
from app.main import create_app
from app.services.project_repository import get_project_repository
from tests.fakes import InMemoryProjectRepository

_key = ec.generate_private_key(ec.SECP256R1())

USER_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

FIVE_ANSWERS = {
    1: "Help my study group track shared expenses so nobody loses money.",
    2: "A REST backend exposing expense data through HTTP endpoints.",
    3: "Python and FastAPI.",
    4: "Sometimes, depends",
    5: "About six weeks.",
}

ROADMAP_ROUTES = (
    ("GET", "/roadmap"),
    ("POST", "/roadmap/generate"),
)


def auth_headers(user_id=USER_A):
    claims = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {pyjwt.encode(claims, _key, algorithm='ES256')}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://stub-project.supabase.co")
    for var in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)  # guarantee the no-key stub path
    monkeypatch.setattr(
        security, "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=_key.public_key())
        ),
    )
    app = create_app()
    # One shared fake per test so state persists across requests.
    fake = InMemoryProjectRepository()
    app.dependency_overrides[get_project_repository] = lambda: fake
    return TestClient(app)


def complete_intake(client, user_id=USER_A):
    for n in (1, 2, 3, 4, 5):
        resp = client.post(
            "/intake/answers",
            json={"question": n, "answer": FIVE_ANSWERS[n]},
            headers=auth_headers(user_id),
        )
        assert resp.status_code == 200
    assert client.post("/intake/complete", headers=auth_headers(user_id)).status_code == 200


def test_roadmap_routes_require_auth(client):
    for method, path in ROADMAP_ROUTES:
        resp = client.request(method, path)
        assert resp.status_code == 401
        assert resp.json()["error"]["status"] == 401


def test_full_generation_flow_through_routes(client):
    complete_intake(client)
    resp = client.post("/roadmap/generate", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["archetype_id"] == 2  # backend/API-only intake answers
    assert body["status"] == "active"
    assert len(body["roadmap"]["phases"]) == 7
    assert body["roadmap"]["phases"][-1]["phase_title"] == "Pre-Deployment Security Checklist"

    read = client.get("/roadmap", headers=auth_headers())
    assert read.status_code == 200
    assert read.json() == body


def test_generate_before_intake_complete_returns_controlled_409(client):
    resp = client.post("/roadmap/generate", headers=auth_headers())
    assert resp.status_code == 409
    assert resp.json() == {
        "error": {
            "status": 409,
            "message": "Complete the five intake questions before generating a roadmap.",
        }
    }


def test_get_before_generation_returns_controlled_404(client):
    resp = client.get("/roadmap", headers=auth_headers())
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {"status": 404, "message": "No roadmap has been generated yet."}
    }


def test_duplicate_generate_returns_controlled_409(client):
    complete_intake(client)
    assert client.post("/roadmap/generate", headers=auth_headers()).status_code == 200
    resp = client.post("/roadmap/generate", headers=auth_headers())
    assert resp.status_code == 409
    assert "already been generated" in resp.json()["error"]["message"]


def test_user_cannot_read_or_generate_another_users_roadmap(client):
    complete_intake(client, USER_A)
    assert client.post("/roadmap/generate", headers=auth_headers(USER_A)).status_code == 200
    # B sees no roadmap and cannot generate against A's project.
    assert client.get("/roadmap", headers=auth_headers(USER_B)).status_code == 404
    assert client.post("/roadmap/generate", headers=auth_headers(USER_B)).status_code == 409


def test_roadmap_responses_contain_no_secrets(client, monkeypatch):
    complete_intake(client)
    assert client.post("/roadmap/generate", headers=auth_headers()).status_code == 200
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key-for-tests")
    get_settings.cache_clear()  # make the fake keys visible to request-time settings
    for method, path in ROADMAP_ROUTES:
        text = client.request(method, path, headers=auth_headers()).text
        assert "fake-service-role-key-for-tests" not in text
        assert "fake-gemini-key-for-tests" not in text
        assert "fake-openrouter-key-for-tests" not in text
