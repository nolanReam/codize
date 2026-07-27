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

import json

from app.core import security
from app.core.config import get_settings
from app.main import create_app
from app.services.llm_service import LLMService, StubProvider, get_llm_service
from app.services.project_repository import get_project_repository
from tests.fakes import InMemoryProjectRepository


class _DriftingProvider:
    """Valid JSON that drops the final security-checklist phase — the exact
    drift that returned 502 during the M13C.1 live smoke pass."""

    name = "drifting"

    async def complete(self, prompt: str, temperature: float) -> str:
        roadmap = json.loads(await StubProvider().complete(prompt, temperature))
        roadmap["phases"] = roadmap["phases"][:-1]
        return json.dumps(roadmap)


class _CountingProvider:
    name = "counting"

    def __init__(self):
        self.calls = 0

    async def complete(self, prompt: str, temperature: float) -> str:
        self.calls += 1
        raise AssertionError("browser-local roadmap must not call a provider")

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


def test_drifting_llm_no_longer_blocks_onboarding(client):
    """M13C.1B regression: the drift that returned 502 in the live smoke pass
    now falls back to a valid roadmap, so POST /roadmap/generate returns 200 and
    the project becomes active — no manual DB seeding required."""
    client.app.dependency_overrides[get_llm_service] = lambda: LLMService([_DriftingProvider()])
    try:
        complete_intake(client)
        resp = client.post("/roadmap/generate", headers=auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "active"
        assert len(body["roadmap"]["phases"]) == 7
        assert body["roadmap"]["phases"][-1]["phase_title"] == "Pre-Deployment Security Checklist"
        # No internal validation detail leaks into the response.
        assert "drift" not in resp.text.lower() and "traceback" not in resp.text.lower()
    finally:
        client.app.dependency_overrides.pop(get_llm_service, None)


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


def test_studyflow_route_generates_browser_only_roadmap_with_zero_provider_calls(client):
    answers = {
        1: (
            "A browser-based homework tracker where students add assignments with a title, "
            "subject, and due date; mark them complete; filter and delete them; and keep "
            "the data after refreshing through browser local storage."
        ),
        2: (
            "No accounts\nNo backend\nNo database\nNo AI product features\n"
            "No notifications\nNo calendar integration"
        ),
        3: (
            "Plain HTML, CSS, and JavaScript. The student understands basic variables, "
            "functions, arrays, conditionals, loops, DOM events, and local storage."
        ),
        4: (
            "The student becomes confused when coding AI changes several connected "
            "functions or modifies several files."
        ),
        5: "Produce a working and understandable first version within one week.",
    }
    for number in range(1, 6):
        assert client.post(
            "/intake/answers",
            json={"question": number, "answer": answers[number]},
            headers=auth_headers(),
        ).status_code == 200
    completed = client.post("/intake/complete", headers=auth_headers())
    assert completed.json()["archetype_name"] == "Browser App"

    provider = _CountingProvider()
    client.app.dependency_overrides[get_llm_service] = lambda: LLMService([provider])
    try:
        response = client.post("/roadmap/generate", headers=auth_headers())
    finally:
        client.app.dependency_overrides.pop(get_llm_service, None)

    assert response.status_code == 200
    assert provider.calls == 0
    roadmap = response.json()["roadmap"]
    assert roadmap["archetype_id"] == 3
    assert roadmap["archetype_name"] == "Browser App"
    assert len(roadmap["phases"]) == 7
    serialized = json.dumps(roadmap).lower()
    for forbidden in (
        "backend",
        "database",
        "authentication",
        "accounts",
        "llm",
        "model provider",
        "api key",
        "python",
        "requirements.txt",
        "conversation history",
    ):
        assert forbidden not in serialized
