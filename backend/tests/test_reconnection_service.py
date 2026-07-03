"""Reconnection service tests — the 72-hour rule, controlled states, safe
summary content, acknowledge semantics, and ownership, against the in-memory
fakes. Active projects come through the real roadmap pipeline (stub LLM)."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

from app.services import phase_service
from app.services.reconnection_service import (
    AWAY_THRESHOLD,
    acknowledge,
    get_reconnection_state,
)
from tests.fakes import (
    InMemoryProfileRepository,
    InMemoryProjectRepository,
    InMemoryUnlockRepository,
)
from tests.test_phase_service import (
    OTHER_USER,
    USER,
    seed_active_project,
    seed_intake_only,
)


def run(coro):
    return asyncio.run(coro)


def ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def make_repos():
    return InMemoryProfileRepository(), InMemoryProjectRepository(), InMemoryUnlockRepository()


def state(profiles, projects, unlocks, user=USER):
    return run(get_reconnection_state(profiles, projects, unlocks, user))


# --- the 72-hour rule ------------------------------------------------------------

def test_new_user_with_no_profile_needs_no_reconnection():
    profiles, projects, unlocks = make_repos()
    result = state(profiles, projects, unlocks)
    assert result == {"reconnection_needed": False, "state": "new_user"}


def test_fresh_signup_timestamp_needs_no_reconnection():
    # Live, the signup trigger sets last_login_at = now() — a brand-new user
    # is "recently active" by construction.
    profiles, projects, unlocks = make_repos()
    profiles.seed(USER, ago(0))
    assert state(profiles, projects, unlocks)["reconnection_needed"] is False


def test_no_reconnection_before_72_hours():
    profiles, projects, unlocks = make_repos()
    seed_active_project(projects)
    profiles.seed(USER, ago(71.5))
    result = state(profiles, projects, unlocks)
    assert result == {"reconnection_needed": False, "state": "recently_active"}


def test_reconnection_needed_at_and_after_72_hours():
    profiles, projects, unlocks = make_repos()
    seed_active_project(projects)
    for hours in (72, 100, 24 * 30):
        profiles.seed(USER, ago(hours))
        result = state(profiles, projects, unlocks)
        assert result["reconnection_needed"] is True
        assert result["state"] == "reconnection"


def test_away_but_workspace_not_ready_is_a_controlled_state():
    profiles, projects, unlocks = make_repos()
    profiles.seed(USER, ago(100))
    # no project at all, then intake done but no roadmap yet
    assert state(profiles, projects, unlocks) == {
        "reconnection_needed": False, "state": "workspace_not_ready",
    }
    seed_intake_only(projects)
    assert state(profiles, projects, unlocks)["state"] == "workspace_not_ready"


# --- summary content -------------------------------------------------------------

def away_with_active_project():
    profiles, projects, unlocks = make_repos()
    project = seed_active_project(projects)
    profiles.seed(USER, ago(100))
    return profiles, projects, unlocks, project


def test_summary_shows_verbatim_purpose_and_current_phase_context():
    profiles, projects, unlocks, project = away_with_active_project()
    summary = state(profiles, projects, unlocks)["summary"]
    assert summary["intake_purpose"] == project["intake_purpose"]  # spec: verbatim
    view = phase_service.current_phase_view(project)
    assert summary["current_phase"] == project["current_phase"] == 1
    assert summary["phase_title"] == view["phase_title"]
    assert summary["phase_reminder"] == view["core_concept"]
    assert "Interrogation Gate" in summary["next_action"]


def test_summary_lists_only_incomplete_current_phase_tasks():
    profiles, projects, unlocks, project = away_with_active_project()
    before = state(profiles, projects, unlocks)["summary"]
    total = len(before["incomplete_tasks"])
    assert total > 0 and {"task_id", "description"} == set(before["incomplete_tasks"][0])

    run(phase_service.set_task_completion(projects, USER, 1, "ai-1", True))
    after = state(profiles, projects, unlocks)["summary"]
    assert len(after["incomplete_tasks"]) == total - 1
    assert "ai-1" not in [t["task_id"] for t in after["incomplete_tasks"]]


def test_summary_includes_last_gate_line_and_unlock_views_when_present():
    profiles, projects, unlocks, project = away_with_active_project()
    empty = state(profiles, projects, unlocks)["summary"]
    assert empty["last_gate_summary"] is None
    assert empty["unlocks"] == []

    history = (
        "Phase 1 (Foundation): gate passed on first attempt.\n"
        "Phase 2 (Data Layer): gate passed on attempt 2 (1 failed cooldown attempt(s) before)."
    )
    run(projects.update_project(USER, project["id"], {"gate_history_summary": history}))
    run(unlocks.create_unlock(USER, {
        "project_id": project["id"], "phase_number": 2,
        "unlock_key": "phase-2-functional-unlock",
    }))
    summary = state(profiles, projects, unlocks)["summary"]
    assert summary["last_gate_summary"].startswith("Phase 2 (Data Layer): gate passed")
    assert len(summary["unlocks"]) == 1
    assert set(summary["unlocks"][0]) == {"id", "unlock_key", "project_id",
                                          "phase", "description", "unlocked_at"}


def test_summary_never_contains_scores_thresholds_or_internals():
    profiles, projects, unlocks, project = away_with_active_project()
    # a scored gate history exists in storage, but only the summary line is safe
    run(projects.update_project(USER, project["id"], {
        "gate_history_summary": "Phase 1 (Foundation): gate passed on first attempt.",
    }))
    run(unlocks.create_unlock(USER, {
        "project_id": project["id"], "phase_number": 2,
        "unlock_key": "phase-2-functional-unlock",
    }))
    text = json.dumps(state(profiles, projects, unlocks))
    assert '"score"' not in text
    assert "threshold" not in text.lower()
    assert "QUALIFYING" not in text
    assert "consecutive" not in text.lower()


# --- acknowledge -----------------------------------------------------------------

def test_acknowledge_updates_timestamp_and_clears_reconnection():
    profiles, projects, unlocks, _ = away_with_active_project()
    assert state(profiles, projects, unlocks)["reconnection_needed"] is True

    result = run(acknowledge(profiles, USER))
    assert result["acknowledged"] is True
    assert result["last_login_at"]
    assert state(profiles, projects, unlocks) == {
        "reconnection_needed": False, "state": "recently_active",
    }


def test_acknowledge_is_idempotent_and_creates_missing_profile():
    profiles = InMemoryProfileRepository()  # no row yet — upsert semantics
    first = run(acknowledge(profiles, USER))
    second = run(acknowledge(profiles, USER))
    assert first["acknowledged"] is True and second["acknowledged"] is True
    assert run(profiles.get_profile(USER))["last_login_at"] == second["last_login_at"]


def test_reconnection_state_is_per_user():
    profiles, projects, unlocks, _ = away_with_active_project()
    profiles.seed(OTHER_USER, ago(1))
    assert state(profiles, projects, unlocks, USER)["reconnection_needed"] is True
    # the other user's own state: recently active, and no view of A's project
    assert state(profiles, projects, unlocks, OTHER_USER) == {
        "reconnection_needed": False, "state": "recently_active",
    }
    # acknowledging as B never touches A's timestamp
    run(acknowledge(profiles, OTHER_USER))
    assert state(profiles, projects, unlocks, USER)["reconnection_needed"] is True
