"""Evaluation service tests — readiness states, safe progress content, gate
outcome labels, next actions, read-only behavior, and ownership, against the
in-memory fakes. Active projects come through the real roadmap pipeline (stub
LLM); gate history and unlocks come from real gate runs with a scripted LLM."""

import asyncio
import copy
import json

from app.services import phase_service
from app.services.evaluation_service import get_evaluation
from tests.fakes import (
    InMemoryGateSessionRepository,
    InMemoryProjectRepository,
    InMemoryUnlockRepository,
    ScriptedLLM,
)
from tests.test_gate_service import (
    ANCHOR,
    FAIL_VERDICT,
    PASS_VERDICT,
    run_full_gate,
    seed_active_project,
)
from tests.test_phase_service import INTAKE_FIELDS, OTHER_USER, USER, seed_intake_only

ACTIVE_KEYS = {
    "state", "project_status", "current_phase", "phase_title", "total_phases",
    "completed_phases", "completed_task_count", "total_task_count",
    "incomplete_tasks", "recent_gate", "unlocks", "next_action",
}


def run(coro):
    return asyncio.run(coro)


def make_repos():
    return (
        InMemoryProjectRepository(),
        InMemoryGateSessionRepository(),
        InMemoryUnlockRepository(),
    )


def evaluation(projects, gates, unlocks, user=USER):
    return run(get_evaluation(projects, gates, unlocks, user))


def complete_all_current_tasks(projects, user=USER):
    view = run(phase_service.get_current_phase(projects, user))
    for field in ("ai_appropriate_tasks", "human_required_tasks"):
        for task in view[field]:
            run(phase_service.set_task_completion(
                projects, user, view["phase"], task["task_id"], True
            ))


# --- readiness states ---------------------------------------------------------

def test_no_project_is_not_started():
    projects, gates, unlocks = make_repos()
    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "not_started"
    assert result["project_status"] is None
    assert "intake" in result["next_action"]


def test_intake_needed_before_intake_completion():
    projects, gates, unlocks = make_repos()
    run(projects.create_project(USER, {"intake_purpose": INTAKE_FIELDS["intake_purpose"]}))
    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "intake_needed"
    assert result["project_status"] == "intake"
    assert "intake" in result["next_action"]


def test_roadmap_needed_after_intake_before_roadmap():
    projects, gates, unlocks = make_repos()
    seed_intake_only(projects)
    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "roadmap_needed"
    assert "roadmap" in result["next_action"].lower()


def test_active_project_is_in_progress_with_full_phase_context():
    projects, gates, unlocks = make_repos()
    project = seed_active_project(projects)
    view = phase_service.current_phase_view(project)

    result = evaluation(projects, gates, unlocks)
    assert set(result) == ACTIVE_KEYS
    assert result["state"] == "in_progress"
    assert result["project_status"] == "active"
    assert result["current_phase"] == 1
    assert result["phase_title"] == view["phase_title"]
    assert result["total_phases"] == len(project["roadmap"]["phases"])
    assert result["completed_phases"] == 0
    assert result["completed_task_count"] == 0
    assert result["total_task_count"] == view["total_task_count"]
    assert result["incomplete_tasks"] == phase_service.incomplete_tasks(view)
    assert result["recent_gate"] is None
    assert result["unlocks"] == []
    assert "Phase 1" in result["next_action"]


# --- task progress ------------------------------------------------------------

def test_task_completion_summary_tracks_progress():
    projects, gates, unlocks = make_repos()
    seed_active_project(projects)
    before = evaluation(projects, gates, unlocks)
    run(phase_service.set_task_completion(projects, USER, 1, "ai-1", True))

    after = evaluation(projects, gates, unlocks)
    assert after["completed_task_count"] == before["completed_task_count"] + 1
    assert len(after["incomplete_tasks"]) == len(before["incomplete_tasks"]) - 1
    assert "ai-1" not in {t["task_id"] for t in after["incomplete_tasks"]}


def test_all_tasks_complete_is_gate_ready_with_gate_action():
    projects, gates, unlocks = make_repos()
    seed_active_project(projects)
    complete_all_current_tasks(projects)

    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "gate_ready"
    assert result["incomplete_tasks"] == []
    assert "Interrogation Gate" in result["next_action"]


# --- gate outcomes ------------------------------------------------------------

def test_gate_pass_moves_evaluation_to_the_next_phase():
    projects, gates, unlocks = make_repos()
    seed_active_project(projects, defense_ready=True)
    run_full_gate(projects, gates, verdict=PASS_VERDICT, unlocks=unlocks)

    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "gate_ready"
    assert result["current_phase"] == 2
    assert result["completed_phases"] == 1
    assert result["recent_gate"]["outcome"] == "passed"
    assert "gate passed" in result["recent_gate"]["summary"]
    assert "Phase 2" in result["next_action"]


def test_recent_fail_is_cooldown_with_retry_action():
    projects, gates, unlocks = make_repos()
    seed_active_project(projects, defense_ready=True)
    run_full_gate(projects, gates, verdict=FAIL_VERDICT, unlocks=unlocks)

    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "cooldown"
    assert 0 < result["cooldown_seconds_remaining"] <= 1800
    assert result["current_phase"] == 1 and result["completed_phases"] == 0
    assert result["recent_gate"] == {
        "outcome": "failed", "summary": "No implementation specificity.",
    }
    assert "retried in about" in result["next_action"]


def test_mid_flight_gate_session_is_gate_ready_with_resume_action():
    from app.services.gate_service import start_gate, submit_anchor

    projects, gates, unlocks = make_repos()
    seed_active_project(projects, defense_ready=True)
    sid = run(start_gate(projects, gates, USER))["gate_session_id"]
    run(submit_anchor(projects, gates, ScriptedLLM(["Q1?"]), USER, sid, ANCHOR))

    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "gate_ready"
    assert result["recent_gate"] == {"outcome": "in_progress", "summary": None}
    assert "Resume" in result["next_action"]


def test_final_phase_pass_is_complete_with_unlocks_earned():
    projects, gates, unlocks = make_repos()
    project = seed_active_project(projects, defense_ready=True)
    total = len(project["roadmap"]["phases"])
    for _ in range(total):  # PASS_VERDICT scores 8 → consecutive-quality unlocks
        run_full_gate(projects, gates, verdict=PASS_VERDICT, unlocks=unlocks)

    result = evaluation(projects, gates, unlocks)
    assert result["state"] == "complete"
    assert result["current_phase"] == total
    assert result["completed_phases"] == total == result["total_phases"]
    assert result["recent_gate"]["outcome"] == "passed"
    assert result["unlocks"]  # earned along the way, safe views only
    assert all(
        set(u) == {"id", "unlock_key", "project_id", "phase", "description", "unlocked_at"}
        for u in result["unlocks"]
    )
    assert "final phase" in result["next_action"]


# --- safety -------------------------------------------------------------------

def test_evaluation_is_a_pure_read():
    projects, gates, unlocks = make_repos()
    seed_active_project(projects, defense_ready=True)
    run(phase_service.set_task_completion(projects, USER, 1, "ai-1", True))
    run_full_gate(projects, gates, verdict=PASS_VERDICT, unlocks=unlocks)
    run_full_gate(projects, gates, verdict=PASS_VERDICT, unlocks=unlocks)

    snapshots = [copy.deepcopy(r._rows) for r in (projects, gates, unlocks)]
    evaluation(projects, gates, unlocks)
    assert [r._rows for r in (projects, gates, unlocks)] == snapshots


def test_evaluation_leaks_no_scores_thresholds_or_internals():
    projects, gates, unlocks = make_repos()
    seed_active_project(projects, defense_ready=True)
    run_full_gate(projects, gates, verdict=PASS_VERDICT, unlocks=unlocks)
    run_full_gate(projects, gates, verdict=PASS_VERDICT, unlocks=unlocks)

    text = json.dumps(evaluation(projects, gates, unlocks))
    assert '"score"' not in text
    assert "threshold" not in text.lower()
    assert "QUALIFYING" not in text
    assert "consecutive" not in text.lower()
    assert "gate_evaluation" not in text and "gate_turn" not in text  # prompt files
    assert "temperature" not in text.lower()


def test_users_only_see_their_own_evaluation():
    projects, gates, unlocks = make_repos()
    seed_active_project(projects, USER, defense_ready=True)
    run_full_gate(projects, gates, user=USER, verdict=PASS_VERDICT, unlocks=unlocks)

    other = evaluation(projects, gates, unlocks, user=OTHER_USER)
    assert other["state"] == "not_started"
    assert INTAKE_FIELDS["intake_purpose"] not in json.dumps(other)
