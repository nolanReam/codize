"""Gate route tests: auth-enforced, thin handlers, controlled errors, and no
score/secret leakage over HTTP.

Repositories and the LLM are overridden with fakes; auth uses the offline
ES256 pattern. Projects reach the 'active' state through the real intake +
roadmap routes (no-key stub LLM path), then the gate flow runs through the
real HTTP surface with a scripted gate LLM.
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
from app.services.llm_service import get_llm_service
from app.services.project_repository import (
    get_gate_session_repository,
    get_project_repository,
    get_unlock_repository,
)
from tests.fakes import (
    InMemoryGateSessionRepository,
    InMemoryProjectRepository,
    InMemoryUnlockRepository,
    ScriptedLLM,
)

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

ANCHOR = "I built an `expenses` table with a `user_id` column and a create_expense() handler."

PASS_VERDICT = '{"verdict": "PASS", "reason": "All three conditions satisfied.", "score": 8}'
FAIL_VERDICT = '{"verdict": "FAIL", "reason": "No implementation specificity.", "score": 3}'


def auth_headers(user_id=USER_A):
    claims = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {pyjwt.encode(claims, _key, algorithm='ES256')}"}


@pytest.fixture
def gate_llm():
    return ScriptedLLM()


@pytest.fixture
def client(monkeypatch, gate_llm):
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
    app.dependency_overrides[get_project_repository] = lambda: InMemoryProjectRepository()
    # one repo instance per test — capture them
    project_repo = InMemoryProjectRepository()
    gate_repo = InMemoryGateSessionRepository()
    unlock_repo = InMemoryUnlockRepository()
    app.dependency_overrides[get_project_repository] = lambda: project_repo
    app.dependency_overrides[get_gate_session_repository] = lambda: gate_repo
    app.dependency_overrides[get_unlock_repository] = lambda: unlock_repo
    test_client = TestClient(app)
    test_client.gate_llm = gate_llm
    test_client.app_ref = app
    return test_client


def use_gate_llm(client):
    """Roadmap generation uses the real no-key stub; the gate flow swaps in the
    scripted LLM afterwards."""
    client.app_ref.dependency_overrides[get_llm_service] = lambda: client.gate_llm


def activate_project(client, user_id=USER_A):
    for n in (1, 2, 3, 4, 5):
        resp = client.post(
            "/intake/answers",
            json={"question": n, "answer": FIVE_ANSWERS[n]},
            headers=auth_headers(user_id),
        )
        assert resp.status_code == 200
    assert client.post("/intake/complete", headers=auth_headers(user_id)).status_code == 200
    assert client.post("/roadmap/generate", headers=auth_headers(user_id)).status_code == 200


def run_gate_to_evaluation(client, user_id=USER_A, verdict=PASS_VERDICT):
    client.gate_llm.responses.extend(["Q1?", "Q2?", "Q3?", verdict])
    sid = client.post("/gate/start", headers=auth_headers(user_id)).json()["gate_session_id"]
    assert client.post(f"/gate/{sid}/turn1", json={"anchor_statement": ANCHOR},
                       headers=auth_headers(user_id)).status_code == 200
    assert client.post(f"/gate/{sid}/turn2", json={"answer": "a1"},
                       headers=auth_headers(user_id)).status_code == 200
    assert client.post(f"/gate/{sid}/turn3", json={"answer": "a2"},
                       headers=auth_headers(user_id)).status_code == 200
    resp = client.post(f"/gate/{sid}/evaluate", json={"answer": "a3"},
                       headers=auth_headers(user_id))
    return sid, resp


GATE_ROUTES = (
    ("POST", "/gate/start"),
    ("GET", "/gate/current"),
    ("POST", "/gate/some-id/turn1"),
    ("POST", "/gate/some-id/turn2"),
    ("POST", "/gate/some-id/turn3"),
    ("POST", "/gate/some-id/evaluate"),
)


def test_gate_routes_require_auth(client):
    for method, path in GATE_ROUTES:
        resp = client.request(method, path, json={"anchor_statement": "x", "answer": "x"})
        assert resp.status_code == 401
        assert resp.json()["error"]["status"] == 401


def test_gate_before_roadmap_is_controlled_409(client):
    for method, path in GATE_ROUTES:
        resp = client.request(method, path,
                              json={"anchor_statement": ANCHOR, "answer": "x"},
                              headers=auth_headers())
        assert resp.status_code == 409, path
        assert resp.json()["error"]["status"] == 409


def test_full_gate_flow_pass_advances_phase(client):
    activate_project(client)
    use_gate_llm(client)

    current = client.get("/gate/current", headers=auth_headers()).json()
    assert current["state"] == "not_started" and current["phase"] == 1

    sid, resp = run_gate_to_evaluation(client, verdict=PASS_VERDICT)
    body = resp.json()
    assert resp.status_code == 200
    assert body["verdict"] == "PASS" and body["current_phase"] == 2
    assert "score" not in body

    # phase workspace agrees: the gate, not the checklist, advanced the phase
    assert client.get("/phases/current", headers=auth_headers()).json()["phase"] == 2
    # and the next phase's gate is fresh
    assert client.get("/gate/current", headers=auth_headers()).json()["state"] == "not_started"


def test_fail_sets_cooldown_and_blocks_restart(client):
    activate_project(client)
    use_gate_llm(client)
    sid, resp = run_gate_to_evaluation(client, verdict=FAIL_VERDICT)
    body = resp.json()
    assert body["verdict"] == "FAIL" and body["current_phase"] == 1
    assert body["cooldown_seconds"] == 1800

    retry = client.post("/gate/start", headers=auth_headers())
    assert retry.status_code == 409
    assert "retry available" in retry.json()["error"]["message"]
    assert 0 < int(retry.headers["Retry-After"]) <= 1800

    current = client.get("/gate/current", headers=auth_headers()).json()
    assert current["state"] == "cooldown"
    assert 0 < current["cooldown_seconds_remaining"] <= 1800


def test_invalid_anchor_is_422_and_out_of_order_is_409(client):
    activate_project(client)
    use_gate_llm(client)
    sid = client.post("/gate/start", headers=auth_headers()).json()["gate_session_id"]

    resp = client.post(f"/gate/{sid}/turn1",
                       json={"anchor_statement": "I built the auth system and it works"},
                       headers=auth_headers())
    assert resp.status_code == 422

    resp = client.post(f"/gate/{sid}/turn1", json={"anchor_statement": "   "},
                       headers=auth_headers())
    assert resp.status_code == 422  # blank rejected at the schema boundary

    resp = client.post(f"/gate/{sid}/turn2", json={"answer": "a1"}, headers=auth_headers())
    assert resp.status_code == 409  # anchor not submitted yet

    resp = client.post("/gate/unknown-session/turn1",
                       json={"anchor_statement": ANCHOR}, headers=auth_headers())
    assert resp.status_code == 404


def test_llm_failure_maps_to_502_and_is_retryable(client):
    activate_project(client)
    use_gate_llm(client)
    sid = client.post("/gate/start", headers=auth_headers()).json()["gate_session_id"]
    # empty script → LLMError → 502
    resp = client.post(f"/gate/{sid}/turn1", json={"anchor_statement": ANCHOR},
                       headers=auth_headers())
    assert resp.status_code == 502
    assert resp.json()["error"]["status"] == 502

    client.gate_llm.responses.append("Q1?")
    resp = client.post(f"/gate/{sid}/turn1", json={"anchor_statement": ANCHOR},
                       headers=auth_headers())
    assert resp.status_code == 200 and resp.json()["question"] == "Q1?"


def test_wrong_user_gets_404_for_anothers_session(client):
    activate_project(client, USER_A)
    activate_project(client, USER_B)
    use_gate_llm(client)
    sid = client.post("/gate/start", headers=auth_headers(USER_A)).json()["gate_session_id"]

    for path, body in ((f"/gate/{sid}/turn1", {"anchor_statement": ANCHOR}),
                       (f"/gate/{sid}/turn2", {"answer": "a"}),
                       (f"/gate/{sid}/turn3", {"answer": "a"}),
                       (f"/gate/{sid}/evaluate", {"answer": "a"})):
        resp = client.post(path, json=body, headers=auth_headers(USER_B))
        assert resp.status_code == 404, path

    # B's own current-gate view never shows A's session
    assert client.get("/gate/current", headers=auth_headers(USER_B)).json()["state"] == "not_started"


def test_gate_responses_leak_no_secrets_or_scores(client, monkeypatch):
    activate_project(client)
    use_gate_llm(client)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_fake-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key-for-tests")
    get_settings.cache_clear()

    sid, resp = run_gate_to_evaluation(client, verdict=PASS_VERDICT)
    texts = [resp.text, client.get("/gate/current", headers=auth_headers()).text]
    for text in texts:
        assert "sb_secret_fake-for-tests" not in text
        assert "fake-gemini-key-for-tests" not in text
        assert "fake-openrouter-key-for-tests" not in text
        assert '"score"' not in text  # hidden threshold data never leaves the server
