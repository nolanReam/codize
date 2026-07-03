"""Unlock route tests: auth-enforced, ownership-scoped, and no score /
threshold / secret leakage over HTTP. Reuses the gate-route harness — projects
become active through the real intake + roadmap routes, gates run through the
real HTTP flow with a scripted LLM, and unlocks fall out of gate PASSes."""

from app.core.config import get_settings
from tests.test_gate_routes import (  # noqa: F401  (client/gate_llm fixtures)
    USER_A,
    USER_B,
    activate_project,
    auth_headers,
    client,
    gate_llm,
    run_gate_to_evaluation,
    use_gate_llm,
)

HIGH_PASS = '{"verdict": "PASS", "reason": "Strong specific answer.", "score": 8}'
LOW_PASS = '{"verdict": "PASS", "reason": "Barely enough.", "score": 5}'
FAIL = '{"verdict": "FAIL", "reason": "Generic textbook answer.", "score": 2}'


def test_unlock_route_requires_auth(client):
    resp = client.get("/unlocks")
    assert resp.status_code == 401
    assert resp.json()["error"]["status"] == 401


def test_unlocks_empty_before_any_project_or_gates(client):
    assert client.get("/unlocks", headers=auth_headers()).json() == {"unlocks": []}
    activate_project(client)
    assert client.get("/unlocks", headers=auth_headers()).json() == {"unlocks": []}


def test_two_consecutive_qualifying_passes_unlock_over_http(client):
    activate_project(client)
    use_gate_llm(client)

    _, resp = run_gate_to_evaluation(client, verdict=HIGH_PASS)
    assert resp.status_code == 200
    assert resp.json()["new_unlocks"] == []  # one qualifying gate is not enough
    assert client.get("/unlocks", headers=auth_headers()).json() == {"unlocks": []}

    _, resp = run_gate_to_evaluation(client, verdict=HIGH_PASS)
    new = resp.json()["new_unlocks"]
    assert len(new) == 1 and new[0]["phase"] == 2

    body = client.get("/unlocks", headers=auth_headers()).json()
    assert len(body["unlocks"]) == 1
    unlock = body["unlocks"][0]
    assert set(unlock) == {"id", "unlock_key", "project_id", "phase",
                           "description", "unlocked_at"}
    assert unlock["unlock_key"] == "phase-2-functional-unlock"
    assert unlock["description"]  # the roadmap's personalized reward text


def test_no_unlock_when_a_consecutive_score_is_below_threshold(client):
    activate_project(client)
    use_gate_llm(client)
    for verdict in (HIGH_PASS, LOW_PASS, HIGH_PASS):  # 8, 5, 8
        _, resp = run_gate_to_evaluation(client, verdict=verdict)
        assert resp.json()["new_unlocks"] == []
    assert client.get("/unlocks", headers=auth_headers()).json() == {"unlocks": []}


def test_failed_gate_grants_nothing(client):
    activate_project(client)
    use_gate_llm(client)
    _, resp = run_gate_to_evaluation(client, verdict=FAIL)
    body = resp.json()
    assert body["verdict"] == "FAIL"
    assert "new_unlocks" not in body
    assert client.get("/unlocks", headers=auth_headers()).json() == {"unlocks": []}


def test_user_cannot_read_anothers_unlocks(client):
    activate_project(client, USER_A)
    activate_project(client, USER_B)  # roadmaps need the stub LLM, so before the swap
    use_gate_llm(client)
    run_gate_to_evaluation(client, USER_A, verdict=HIGH_PASS)
    run_gate_to_evaluation(client, USER_A, verdict=HIGH_PASS)
    assert len(client.get("/unlocks", headers=auth_headers(USER_A)).json()["unlocks"]) == 1

    assert client.get("/unlocks", headers=auth_headers(USER_B)).json() == {"unlocks": []}


def test_unlock_responses_leak_no_scores_thresholds_or_secrets(client, monkeypatch):
    activate_project(client)
    use_gate_llm(client)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_fake-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    get_settings.cache_clear()

    _, first = run_gate_to_evaluation(client, verdict=HIGH_PASS)
    _, second = run_gate_to_evaluation(client, verdict=HIGH_PASS)
    listing = client.get("/unlocks", headers=auth_headers())
    for text in (first.text, second.text, listing.text):
        assert '"score"' not in text
        assert "threshold" not in text.lower()
        assert "QUALIFYING" not in text
        assert "sb_secret_fake-for-tests" not in text
        assert "fake-gemini-key-for-tests" not in text
