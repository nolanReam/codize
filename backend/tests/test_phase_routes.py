"""Phase workspace route tests: auth-enforced, thin handlers, controlled errors.

Repository is overridden with the in-memory fake; auth uses the offline ES256
pattern. Projects reach the 'active' state through the real intake + roadmap
routes (no-key stub LLM path), so the workspace is tested against exactly the
state the rest of the API produces.
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

PHASE_ROUTES = (
    ("GET", "/phases"),
    ("GET", "/phases/current"),
    ("GET", "/phases/1"),
    ("PATCH", "/phases/1/tasks/ai-1"),
    ("GET", "/phases/current/assignment"),
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
    fake = InMemoryProjectRepository()
    app.dependency_overrides[get_project_repository] = lambda: fake
    return TestClient(app)


def activate_project(client, user_id=USER_A):
    """Complete intake and generate a roadmap through the real routes."""
    for n in (1, 2, 3, 4, 5):
        resp = client.post(
            "/intake/answers",
            json={"question": n, "answer": FIVE_ANSWERS[n]},
            headers=auth_headers(user_id),
        )
        assert resp.status_code == 200
    assert client.post("/intake/complete", headers=auth_headers(user_id)).status_code == 200
    resp = client.post("/roadmap/generate", headers=auth_headers(user_id))
    assert resp.status_code == 200
    return resp.json()["roadmap"]


def test_phase_routes_require_auth(client):
    for method, path in PHASE_ROUTES:
        resp = client.request(method, path, json={"completed": True})
        assert resp.status_code == 401
        assert resp.json()["error"]["status"] == 401
    assert client.put(
        "/phases/current/assignment", json={"task_id": "ai-1"}
    ).status_code == 401


def test_phases_before_roadmap_returns_controlled_409(client):
    for method, path in PHASE_ROUTES:
        resp = client.request(method, path, json={"completed": True}, headers=auth_headers())
        assert resp.status_code == 409
        assert resp.json() == {
            "error": {
                "status": 409,
                "message": "The phase workspace needs an active project with a generated roadmap.",
            }
        }
    assert client.put(
        "/phases/current/assignment",
        json={"task_id": "ai-1"},
        headers=auth_headers(),
    ).status_code == 409


def test_full_phase_workspace_flow(client):
    roadmap = activate_project(client)

    listing = client.get("/phases", headers=auth_headers())
    assert listing.status_code == 200
    body = listing.json()
    assert body["current_phase"] == 1
    assert [p["phase"] for p in body["phases"]] == [p["phase"] for p in roadmap["phases"]]

    current = client.get("/phases/current", headers=auth_headers())
    assert current.status_code == 200
    assert current.json()["phase"] == 1
    assert current.json()["is_current"] is True

    recommended = client.get("/phases/current/assignment", headers=auth_headers())
    assert recommended.status_code == 200
    assert recommended.json()["assignment"]["task_id"] == "ai-1"
    selected = client.put(
        "/phases/current/assignment",
        json={"task_id": "ai-2"},
        headers=auth_headers(),
    )
    assert selected.status_code == 200
    assert selected.json()["state"] == "selected"
    assert selected.json()["assignment"]["description"] == roadmap["phases"][0]["ai_appropriate_tasks"][1]

    phase3 = client.get("/phases/3", headers=auth_headers())
    assert phase3.status_code == 200
    assert phase3.json()["phase_title"] == roadmap["phases"][2]["phase_title"]

    done = client.patch(
        "/phases/3/tasks/ai-1", json={"completed": True}, headers=auth_headers()
    )
    assert done.status_code == 200
    assert done.json()["ai_appropriate_tasks"][0]["completed"] is True

    # Persists across requests, and can be unmarked again.
    reread = client.get("/phases/3", headers=auth_headers()).json()
    assert reread["ai_appropriate_tasks"][0]["completed"] is True
    assert reread["completed_task_count"] == 1
    undone = client.patch(
        "/phases/3/tasks/ai-1", json={"completed": False}, headers=auth_headers()
    )
    assert undone.status_code == 200
    assert undone.json()["completed_task_count"] == 0


def test_invalid_phase_and_task_are_controlled_errors(client):
    activate_project(client)
    resp = client.get("/phases/99", headers=auth_headers())
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {"status": 404, "message": "Phase 99 does not exist in this roadmap."}
    }
    resp = client.get("/phases/not-a-number", headers=auth_headers())
    assert resp.status_code == 422  # int path param, standard error shape
    assert resp.json()["error"]["status"] == 422
    resp = client.patch(
        "/phases/1/tasks/nope-1", json={"completed": True}, headers=auth_headers()
    )
    assert resp.status_code == 404
    assert "does not exist in phase 1" in resp.json()["error"]["message"]
    resp = client.patch("/phases/1/tasks/ai-1", json={}, headers=auth_headers())
    assert resp.status_code == 422
    assert client.put(
        "/phases/current/assignment",
        json={"task_id": "human-999"},
        headers=auth_headers(),
    ).status_code == 404
    assert client.put(
        "/phases/current/assignment",
        json={"task_id": "ai-1", "description": "client-owned"},
        headers=auth_headers(),
    ).status_code == 422


def test_task_updates_do_not_mutate_the_stored_roadmap(client):
    activate_project(client)
    before = client.get("/roadmap", headers=auth_headers()).json()
    assert client.patch(
        "/phases/2/tasks/human-1", json={"completed": True}, headers=auth_headers()
    ).status_code == 200
    assert client.get("/roadmap", headers=auth_headers()).json() == before


def test_user_cannot_access_or_mutate_another_users_phase_state(client):
    activate_project(client, USER_A)
    assert client.patch(
        "/phases/1/tasks/ai-1", json={"completed": True}, headers=auth_headers(USER_A)
    ).status_code == 200

    # B has no active project: every workspace call is refused, and A's
    # progress is untouched by B's attempts.
    assert client.get("/phases", headers=auth_headers(USER_B)).status_code == 409
    assert client.patch(
        "/phases/1/tasks/ai-1", json={"completed": False}, headers=auth_headers(USER_B)
    ).status_code == 409
    phase1 = client.get("/phases/1", headers=auth_headers(USER_A)).json()
    assert phase1["ai_appropriate_tasks"][0]["completed"] is True


def test_phase_responses_contain_no_secrets(client, monkeypatch):
    activate_project(client)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key-for-tests")
    get_settings.cache_clear()  # make the fake keys visible to request-time settings
    for method, path in PHASE_ROUTES:
        text = client.request(
            method, path, json={"completed": True}, headers=auth_headers()
        ).text
        assert "fake-service-role-key-for-tests" not in text
        assert "fake-gemini-key-for-tests" not in text
        assert "fake-openrouter-key-for-tests" not in text
