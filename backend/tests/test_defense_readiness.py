"""M18A formal Defense readiness: workflow truth, tasks, and stable attempts."""

from types import SimpleNamespace

import pytest

from app.services import defense_readiness_service, gate_service, workflow_context_service
from tests.fakes import InMemoryGateSessionRepository, InMemoryProjectRepository
from tests.test_gate_service import USER, run, seed_active_project


def ready_project():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo, defense_ready=True)
    return repo, project, project["roadmap"]["phases"][0]


def test_manual_legacy_workflow_and_completed_tasks_are_formally_ready():
    _, project, phase = ready_project()
    readiness = defense_readiness_service.preparation(project, phase)
    assert readiness == {"state": "ready", "formal_ready": True, "blockers": []}


def test_zero_completed_build_tasks_block_formal_defense():
    _, project, phase = ready_project()
    project["task_progress"] = {}
    readiness = defense_readiness_service.preparation(project, phase)
    assert readiness["formal_ready"] is False
    blocker = next(item for item in readiness["blockers"] if item["code"] == "build_tasks_incomplete")
    assert "remain" in blocker["label"]


@pytest.mark.parametrize(
    ("source", "state", "expected_code"),
    [
        ("change_map", "missing", "change_map_missing"),
        ("change_map", "stale", "change_map_stale"),
        ("review", "missing", "review_missing"),
        ("review", "stale", "review_stale"),
        ("verification", "missing", "verification_missing"),
        ("verification", "stale", "verification_stale"),
        ("evidence", "missing", "evidence_missing"),
        ("evidence", "incomplete", "evidence_incomplete"),
        ("evidence", "stale", "evidence_stale"),
    ],
)
def test_each_current_workflow_source_state_has_an_exact_blocker(
    monkeypatch, source, state, expected_code
):
    _, project, phase = ready_project()
    states = {key: "manual" for key in ("change_map", "review", "verification", "evidence")}
    states[source] = state
    fake = SimpleNamespace(**{
        key: SimpleNamespace(state=value) for key, value in states.items()
    })
    monkeypatch.setattr(workflow_context_service, "build_workflow_context", lambda *_: fake)
    readiness = defense_readiness_service.preparation(project, phase)
    assert readiness["formal_ready"] is False
    assert expected_code in {item["code"] for item in readiness["blockers"]}


def test_import_first_recovery_does_not_require_a_retrospective_prompt():
    _, project, phase = ready_project()
    del project["workflow_artifacts"]["1"]["prompt_builder"]
    assert defense_readiness_service.preparation(project, phase)["formal_ready"] is True


def test_direct_start_is_blocked_before_a_session_is_created():
    repo, project, _ = ready_project()
    project["task_progress"] = {}
    run(repo.update_project(USER, project["id"], {"task_progress": {}}))
    gates = InMemoryGateSessionRepository()
    with pytest.raises(gate_service.GatePreparationError, match="not ready yet"):
        run(gate_service.start_gate(repo, gates, USER))
    assert gates._rows == []


def test_active_attempt_remains_resumable_after_upstream_work_changes():
    repo, project, _ = ready_project()
    gates = InMemoryGateSessionRepository()
    started = run(gate_service.start_gate(repo, gates, USER))
    run(repo.update_project(USER, project["id"], {"task_progress": {}}))
    current = run(gate_service.get_current_gate(repo, gates, USER))
    assert current["gate_session_id"] == started["gate_session_id"]
    assert current["state"] == "in_progress"
    assert current["readiness"]["state"] == "in_progress"
