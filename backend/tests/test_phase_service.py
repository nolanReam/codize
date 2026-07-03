"""Phase workspace service tests — eligibility rules, phase reads, task
completion persistence, and roadmap immutability, against the in-memory fake.

Projects are seeded through the real roadmap pipeline (stub LLM) so the phase
workspace is always tested against a roadmap that passed M7's fail-closed
structure validation.
"""

import asyncio
import copy

import pytest

from app.services import roadmap_service, template_service
from app.services.llm_service import LLMService, StubProvider
from app.services.phase_service import (
    PhaseNotFoundError,
    TaskNotFoundError,
    WorkspaceNotReadyError,
    get_current_phase,
    get_phase,
    list_phases,
    set_task_completion,
)
from tests.fakes import InMemoryProjectRepository

USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_USER = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

INTAKE_FIELDS = {
    "intake_purpose": "Help my volleyball league track scores so organizers stop using paper.",
    "intake_scope": "A REST backend exposing match stats through HTTP endpoints.",
    "intake_stack": "Python and FastAPI",
    "intake_self_assessment": "Sometimes, depends",
    "intake_timeline": "About six weeks",
}


def run(coro):
    return asyncio.run(coro)


def seed_intake_only(repo, user=USER, archetype_id=2, **overrides):
    fields = {**INTAKE_FIELDS,
              "intake_completed_at": "2026-07-02T00:00:00+00:00",
              "archetype_id": archetype_id, **overrides}
    return run(repo.create_project(user, fields))


def seed_active_project(repo, user=USER, archetype_id=2):
    """Seed a project and run real roadmap generation (stub LLM) against it."""
    seed_intake_only(repo, user, archetype_id)
    run(roadmap_service.generate_roadmap(repo, LLMService([StubProvider()]), user))
    return run(repo.get_project(user))


# --- eligibility -----------------------------------------------------------------

def test_workspace_refused_with_no_project():
    repo = InMemoryProjectRepository()
    for call in (list_phases(repo, USER), get_current_phase(repo, USER),
                 get_phase(repo, USER, 1), set_task_completion(repo, USER, 1, "ai-1", True)):
        with pytest.raises(WorkspaceNotReadyError):
            run(call)


def test_workspace_refused_before_roadmap_exists():
    repo = InMemoryProjectRepository()
    seed_intake_only(repo)  # intake complete, archetype assigned, no roadmap
    with pytest.raises(WorkspaceNotReadyError):
        run(list_phases(repo, USER))


def test_workspace_refused_when_project_not_active():
    # A stored roadmap alone is not enough: status must be 'active'.
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(repo.update_project(USER, project["id"], {"status": "completed"}))
    with pytest.raises(WorkspaceNotReadyError):
        run(get_current_phase(repo, USER))


def test_other_user_cannot_see_the_workspace():
    repo = InMemoryProjectRepository()
    seed_active_project(repo, USER)
    with pytest.raises(WorkspaceNotReadyError):
        run(list_phases(repo, OTHER_USER))


# --- phase reads -----------------------------------------------------------------

@pytest.mark.parametrize("archetype_id", [1, 2, 3])
def test_list_phases_mirrors_the_stored_roadmap(archetype_id):
    repo = InMemoryProjectRepository()
    seed_active_project(repo, archetype_id=archetype_id)
    template = template_service.get_template(archetype_id)

    listing = run(list_phases(repo, USER))
    assert listing["current_phase"] == 1
    assert [p["phase"] for p in listing["phases"]] == [t["phase"] for t in template["phases"]]
    assert [p["phase_title"] for p in listing["phases"]] == [
        t["phase_title"] for t in template["phases"]
    ]
    assert [p["is_current"] for p in listing["phases"]] == [
        p["phase"] == 1 for p in listing["phases"]
    ]
    assert all(p["completed_task_count"] == 0 for p in listing["phases"])


def test_get_phase_returns_the_stored_phase_content():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    stored = project["roadmap"]["phases"][2]  # phase 3

    view = run(get_phase(repo, USER, 3))
    assert view["phase"] == 3
    assert view["phase_title"] == stored["phase_title"]
    assert view["core_concept"] == stored["core_concept"]
    assert view["gate_depth"] == stored["gate_depth"]
    assert view["unlock_condition"] == stored["unlock_condition"]
    assert view["functional_unlock"] == stored["functional_unlock"]
    assert view["explanation_gate_targets"] == stored["explanation_gate_targets"]
    assert [t["description"] for t in view["ai_appropriate_tasks"]] == stored["ai_appropriate_tasks"]
    assert [t["description"] for t in view["human_required_tasks"]] == stored["human_required_tasks"]
    assert all(not t["completed"] for t in view["ai_appropriate_tasks"] + view["human_required_tasks"])
    assert view["total_task_count"] == len(stored["ai_appropriate_tasks"]) + len(
        stored["human_required_tasks"]
    )


def test_get_current_phase_follows_current_phase_column():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    assert run(get_current_phase(repo, USER))["phase"] == 1
    run(repo.update_project(USER, project["id"], {"current_phase": 3}))
    view = run(get_current_phase(repo, USER))
    assert view["phase"] == 3
    assert view["is_current"] is True


@pytest.mark.parametrize("bad_number", [0, -1, 8, 99])
def test_invalid_phase_number_is_a_controlled_error(bad_number):
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    with pytest.raises(PhaseNotFoundError):
        run(get_phase(repo, USER, bad_number))
    with pytest.raises(PhaseNotFoundError):
        run(set_task_completion(repo, USER, bad_number, "ai-1", True))


# --- task completion -------------------------------------------------------------

def test_task_can_be_marked_complete_and_incomplete():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)

    view = run(set_task_completion(repo, USER, 2, "ai-1", True))
    assert view["ai_appropriate_tasks"][0]["completed"] is True
    assert view["completed_task_count"] == 1

    view = run(set_task_completion(repo, USER, 2, "ai-1", False))
    assert view["ai_appropriate_tasks"][0]["completed"] is False
    assert view["completed_task_count"] == 0


def test_task_completion_persists_across_reads():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(set_task_completion(repo, USER, 2, "human-1", True))
    run(set_task_completion(repo, USER, 3, "ai-2", True))

    phase2 = run(get_phase(repo, USER, 2))
    assert phase2["human_required_tasks"][0]["completed"] is True
    phase3 = run(get_phase(repo, USER, 3))
    assert phase3["ai_appropriate_tasks"][1]["completed"] is True
    # Progress is per-phase: phase 2's ai tasks are untouched.
    assert all(not t["completed"] for t in phase2["ai_appropriate_tasks"])

    listing = run(list_phases(repo, USER))
    by_number = {p["phase"]: p for p in listing["phases"]}
    assert by_number[2]["completed_task_count"] == 1
    assert by_number[3]["completed_task_count"] == 1


def test_marking_complete_is_idempotent():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(set_task_completion(repo, USER, 1, "ai-1", True))
    view = run(set_task_completion(repo, USER, 1, "ai-1", True))
    assert view["completed_task_count"] == 1


@pytest.mark.parametrize("bad_task", ["ai-0", "ai-99", "human-99", "gate-1", "ai1", "AI-1"])
def test_unknown_task_id_is_a_controlled_error(bad_task):
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    with pytest.raises(TaskNotFoundError):
        run(set_task_completion(repo, USER, 1, bad_task, True))


def test_other_user_cannot_mutate_task_state():
    repo = InMemoryProjectRepository()
    seed_active_project(repo, USER)
    with pytest.raises(WorkspaceNotReadyError):
        run(set_task_completion(repo, OTHER_USER, 1, "ai-1", True))
    assert run(get_phase(repo, USER, 1))["completed_task_count"] == 0


# --- structure preservation ------------------------------------------------------

def test_task_updates_never_mutate_the_roadmap():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    roadmap_before = copy.deepcopy(project["roadmap"])

    run(set_task_completion(repo, USER, 1, "ai-1", True))
    run(set_task_completion(repo, USER, 4, "human-1", True))
    run(set_task_completion(repo, USER, 1, "ai-1", False))

    after = run(repo.get_project(USER))
    assert after["roadmap"] == roadmap_before
    assert after["status"] == "active"
    assert after["current_phase"] == project["current_phase"]
    # And the stored roadmap still passes the M7 fail-closed validator.
    template = template_service.get_template(after["archetype_id"])
    assert roadmap_service.validate_roadmap_structure(after["roadmap"], template) == []


def test_corrupted_stored_progress_is_ignored_on_read():
    # Defense in depth: junk in task_progress must never distort the workspace.
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(repo.update_project(USER, project["id"], {
        "task_progress": {"1": ["ai-1", "ai-999", "nonsense", 42], "2": "not-a-list"},
    }))

    phase1 = run(get_phase(repo, USER, 1))
    assert phase1["completed_task_count"] == 1  # only the resolvable id counts
    assert phase1["ai_appropriate_tasks"][0]["completed"] is True
    assert run(get_phase(repo, USER, 2))["completed_task_count"] == 0
    # A write through the service replaces the phase's junk with clean ids.
    run(set_task_completion(repo, USER, 1, "human-1", True))
    stored = run(repo.get_project(USER))["task_progress"]["1"]
    assert stored == ["ai-1", "human-1"]
