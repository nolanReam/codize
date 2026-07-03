"""Evaluation route tests: auth-enforced, controlled states over HTTP, safe
content, read-only behavior, and per-user isolation. Reuses the gate-route
harness — projects become active through the real intake + roadmap routes,
and gate history / unlocks come from real gate PASSes with a scripted LLM."""

import copy

from app.core.config import get_settings
from tests.test_gate_routes import (  # noqa: F401  (client/gate_llm fixtures)
    FIVE_ANSWERS,
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
FAIL = '{"verdict": "FAIL", "reason": "No implementation specificity.", "score": 3}'


def get_evaluation(client, user_id=USER_A):
    resp = client.get("/evaluation", headers=auth_headers(user_id))
    assert resp.status_code == 200
    return resp


def test_evaluation_requires_auth(client):
    resp = client.get("/evaluation")
    assert resp.status_code == 401
    assert resp.json()["error"]["status"] == 401


def test_readiness_states_track_the_project_lifecycle(client):
    assert get_evaluation(client).json()["state"] == "not_started"

    # two of five intake answers → still intake_needed
    for n in (1, 2):
        client.post("/intake/answers", json={"question": n, "answer": FIVE_ANSWERS[n]},
                    headers=auth_headers())
    assert get_evaluation(client).json()["state"] == "intake_needed"

    for n in (3, 4, 5):
        client.post("/intake/answers", json={"question": n, "answer": FIVE_ANSWERS[n]},
                    headers=auth_headers())
    assert client.post("/intake/complete", headers=auth_headers()).status_code == 200
    assert get_evaluation(client).json()["state"] == "roadmap_needed"

    assert client.post("/roadmap/generate", headers=auth_headers()).status_code == 200
    body = get_evaluation(client).json()
    assert body["state"] == "in_progress"
    assert body["current_phase"] == 1 and body["phase_title"]
    assert body["completed_phases"] == 0 and body["total_phases"] > 1
    assert body["incomplete_tasks"] and body["unlocks"] == []


def test_gate_outcomes_flow_into_the_evaluation(client):
    activate_project(client)
    use_gate_llm(client)

    _, resp = run_gate_to_evaluation(client, verdict=HIGH_PASS)
    assert resp.status_code == 200
    body = get_evaluation(client).json()
    assert body["current_phase"] == 2 and body["completed_phases"] == 1
    assert body["recent_gate"]["outcome"] == "passed"
    assert "Phase 2" in body["next_action"]

    _, resp = run_gate_to_evaluation(client, verdict=FAIL)
    assert resp.status_code == 200
    body = get_evaluation(client).json()
    assert body["state"] == "cooldown"
    assert 0 < body["cooldown_seconds_remaining"] <= 1800
    assert body["recent_gate"]["outcome"] == "failed"
    assert "retried in about" in body["next_action"]


def test_users_cannot_see_anothers_evaluation(client):
    activate_project(client, USER_A)
    body_b = get_evaluation(client, USER_B).json()
    assert body_b["state"] == "not_started"
    assert FIVE_ANSWERS[1] not in get_evaluation(client, USER_B).text


def test_evaluation_is_read_only_and_leaks_nothing(client, monkeypatch):
    activate_project(client)
    use_gate_llm(client)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_fake-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    get_settings.cache_clear()

    # two qualifying passes: gate history + an unlock now exist in storage
    for _ in range(2):
        _, resp = run_gate_to_evaluation(client, verdict=HIGH_PASS)
        assert resp.status_code == 200

    from app.services.project_repository import (
        get_gate_session_repository,
        get_project_repository,
        get_unlock_repository,
    )
    repos = [
        client.app_ref.dependency_overrides[dep]()
        for dep in (get_project_repository, get_gate_session_repository,
                    get_unlock_repository)
    ]
    snapshots = [copy.deepcopy(r._rows) for r in repos]

    resp = get_evaluation(client)
    body = resp.json()
    assert len(body["unlocks"]) == 1
    assert body["recent_gate"]["outcome"] == "passed"

    # pure read: nothing in storage changed
    assert [r._rows for r in repos] == snapshots

    # no hidden scores, thresholds, prompts, or server-only secrets
    assert '"score"' not in resp.text
    assert "threshold" not in resp.text.lower()
    assert "QUALIFYING" not in resp.text
    assert "gate_evaluation" not in resp.text and "gate_turn" not in resp.text
    assert "sb_secret_fake-for-tests" not in resp.text
    assert "fake-gemini-key-for-tests" not in resp.text
