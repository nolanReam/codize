"""Reconnection route tests: auth-enforced, per-user state, safe summary over
HTTP, and acknowledge semantics. Reuses the gate-route harness — projects
become active through the real intake + roadmap routes, and gate history /
unlocks are produced by real gate PASSes with a scripted LLM."""

from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.services.project_repository import get_profile_repository
from tests.fakes import InMemoryProfileRepository
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


def use_profiles(client):
    profiles = InMemoryProfileRepository()
    client.app_ref.dependency_overrides[get_profile_repository] = lambda: profiles
    return profiles


def ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def test_reconnection_routes_require_auth(client):
    use_profiles(client)
    for method, path in (("GET", "/reconnection"), ("POST", "/reconnection/acknowledge")):
        resp = client.request(method, path)
        assert resp.status_code == 401
        assert resp.json()["error"]["status"] == 401


def test_new_user_gets_controlled_not_needed_state(client):
    use_profiles(client)
    body = client.get("/reconnection", headers=auth_headers()).json()
    assert body == {"reconnection_needed": False, "state": "new_user"}


def test_away_user_without_roadmap_gets_workspace_not_ready(client):
    profiles = use_profiles(client)
    profiles.seed(USER_A, ago(100))
    body = client.get("/reconnection", headers=auth_headers()).json()
    assert body == {"reconnection_needed": False, "state": "workspace_not_ready"}


def test_full_reconnection_flow_over_http(client):
    profiles = use_profiles(client)
    activate_project(client)
    profiles.seed(USER_A, ago(1))
    assert client.get("/reconnection", headers=auth_headers()).json() == {
        "reconnection_needed": False, "state": "recently_active",
    }

    profiles.seed(USER_A, ago(100))
    body = client.get("/reconnection", headers=auth_headers()).json()
    assert body["reconnection_needed"] is True and body["state"] == "reconnection"
    summary = body["summary"]
    assert set(summary) == {"intake_purpose", "current_phase", "phase_title",
                            "phase_reminder", "incomplete_tasks", "last_gate_summary",
                            "unlocks", "next_action"}
    assert summary["intake_purpose"] == FIVE_ANSWERS[1]  # verbatim Q1 answer
    assert summary["current_phase"] == 1 and summary["phase_title"]
    assert summary["incomplete_tasks"] and summary["unlocks"] == []

    ack = client.post("/reconnection/acknowledge", headers=auth_headers())
    assert ack.status_code == 200 and ack.json()["acknowledged"] is True
    assert client.get("/reconnection", headers=auth_headers()).json() == {
        "reconnection_needed": False, "state": "recently_active",
    }


def test_acknowledge_is_idempotent_over_http(client):
    use_profiles(client)
    first = client.post("/reconnection/acknowledge", headers=auth_headers())
    second = client.post("/reconnection/acknowledge", headers=auth_headers())
    assert first.status_code == second.status_code == 200
    assert client.get("/reconnection", headers=auth_headers()).json()["state"] == "recently_active"


def test_user_cannot_touch_anothers_reconnection_state(client):
    profiles = use_profiles(client)
    activate_project(client, USER_A)
    profiles.seed(USER_A, ago(100))

    # B's JWT reaches only B's state — never A's summary or project data
    body_b = client.get("/reconnection", headers=auth_headers(USER_B)).json()
    assert body_b == {"reconnection_needed": False, "state": "new_user"}

    # B acknowledging writes B's row only; A still needs reconnection
    assert client.post("/reconnection/acknowledge", headers=auth_headers(USER_B)).status_code == 200
    assert client.get("/reconnection", headers=auth_headers(USER_A)).json()["reconnection_needed"] is True


def test_reconnection_summary_leaks_no_scores_thresholds_or_secrets(client, monkeypatch):
    profiles = use_profiles(client)
    activate_project(client)
    use_gate_llm(client)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_fake-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    get_settings.cache_clear()

    # two qualifying passes: gate history + an unlock now exist in storage
    for _ in range(2):
        _, resp = run_gate_to_evaluation(client, verdict=HIGH_PASS)
        assert resp.status_code == 200
    profiles.seed(USER_A, ago(100))

    resp = client.get("/reconnection", headers=auth_headers())
    summary = resp.json()["summary"]
    assert summary["last_gate_summary"] and "gate passed" in summary["last_gate_summary"]
    assert len(summary["unlocks"]) == 1

    assert '"score"' not in resp.text
    assert "threshold" not in resp.text.lower()
    assert "QUALIFYING" not in resp.text
    assert "sb_secret_fake-for-tests" not in resp.text
    assert "fake-gemini-key-for-tests" not in resp.text
