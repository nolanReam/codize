"""M18B.2 current-phase assignment behavior and persistence boundaries."""

import copy
import inspect

import pytest

from app.services import phase_service
from app.services.phase_service import TaskNotFoundError, WorkspaceNotReadyError
from tests.fakes import InMemoryProjectRepository
from tests.test_phase_service import OTHER_USER, USER, run, seed_active_project


def test_recommendation_is_deterministic_ai_then_student_then_complete():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)

    first = run(phase_service.get_current_assignment(repo, USER))
    assert first["state"] == "recommended"
    assert first["assignment"]["task_id"] == "ai-1"
    assert first["assignment"]["owner_label"] == "Use AI"

    phase = run(phase_service.get_current_phase(repo, USER))
    for task in phase["ai_appropriate_tasks"]:
        run(phase_service.set_task_completion(repo, USER, 1, task["task_id"], True))
    next_up = run(phase_service.get_current_assignment(repo, USER))
    assert next_up["assignment"]["task_id"] == "human-1"
    assert next_up["assignment"]["owner_label"] == "You decide"

    for task in phase["human_required_tasks"]:
        run(phase_service.set_task_completion(repo, USER, 1, task["task_id"], True))
    assert run(phase_service.get_current_assignment(repo, USER))["state"] == "phase_complete"


def test_explicit_selection_persists_by_phase_without_marking_complete():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    before_roadmap = copy.deepcopy(project["roadmap"])

    selected = run(phase_service.select_current_assignment(repo, USER, "ai-2"))
    assert selected["state"] == "selected"
    assert selected["assignment"]["task_id"] == "ai-2"
    assert selected["assignment"]["completed"] is False

    stored = run(repo.get_project(USER))
    selection = stored["task_progress"]["_phase_assignments"]["1"]
    assert selection["task_id"] == "ai-2"
    assert selection["selected_while_completed"] is False
    assert len(selection["roadmap_fingerprint"]) == 64
    assert stored["roadmap"] == before_roadmap
    assert run(phase_service.get_current_phase(repo, USER))["completed_task_count"] == 0

    run(repo.update_project(USER, project["id"], {"current_phase": 2}))
    phase_two = run(phase_service.get_current_assignment(repo, USER))
    assert phase_two["phase"] == 2
    assert phase_two["state"] == "recommended"
    assert phase_two["assignment"]["task_id"] == "ai-1"


def test_completed_selected_task_yields_next_recommendation_until_explicit_revisit():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    run(phase_service.set_task_completion(repo, USER, 1, "ai-1", True))

    fallback = run(phase_service.get_current_assignment(repo, USER))
    assert fallback["state"] == "recommended"
    assert fallback["assignment"]["task_id"] == "ai-2"
    assert fallback["previous_selection"]["task_id"] == "ai-1"

    revisit = run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    assert revisit["state"] == "selected"
    assert revisit["assignment"]["completed"] is True
    assert "revisit" in revisit["assignment"]["reason"]


def test_removed_or_malformed_selection_falls_back_without_text_matching():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-2"))
    roadmap = copy.deepcopy(project["roadmap"])
    roadmap["phases"][0]["ai_appropriate_tasks"] = [
        roadmap["phases"][0]["ai_appropriate_tasks"][0],
        "",
    ]
    run(repo.update_project(USER, project["id"], {"roadmap": roadmap}))

    view = run(phase_service.get_current_assignment(repo, USER))
    assert view["state"] == "recommended"
    assert view["assignment"]["task_id"] == "ai-1"
    assert view["invalidated_selection"] is True


def test_roadmap_revision_invalidates_even_when_the_phase_local_id_still_exists():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    roadmap = copy.deepcopy(project["roadmap"])
    roadmap["phases"][0]["ai_appropriate_tasks"][0] = "A replacement task with the same position"
    run(repo.update_project(USER, project["id"], {"roadmap": roadmap}))

    view = run(phase_service.get_current_assignment(repo, USER))
    assert view["state"] == "recommended"
    assert view["assignment"]["description"] == "A replacement task with the same position"
    assert view["invalidated_selection"] is True


def test_assignment_retries_a_concurrent_completion_and_preserves_both():
    class OneConflictRepo(InMemoryProjectRepository):
        conflict_once = True

        async def update_task_progress_if_current(self, user_id, project_id, expected, replacement):
            if self.conflict_once:
                self.conflict_once = False
                for row in self._rows:
                    if row["id"] == project_id and row["user_id"] == user_id:
                        row["task_progress"] = {**row["task_progress"], "1": ["ai-1"]}
                return None
            return await super().update_task_progress_if_current(
                user_id, project_id, expected, replacement
            )

    repo = OneConflictRepo()
    seed_active_project(repo)
    selected = run(phase_service.select_current_assignment(repo, USER, "ai-2"))
    assert selected["assignment"]["task_id"] == "ai-2"
    after = run(repo.get_project(USER))["task_progress"]
    assert after["1"] == ["ai-1"]
    assert after["_phase_assignments"]["1"]["task_id"] == "ai-2"


def test_invalid_task_and_cross_user_selection_fail_closed():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    with pytest.raises(TaskNotFoundError):
        run(phase_service.select_current_assignment(repo, USER, "ai-99"))
    with pytest.raises(WorkspaceNotReadyError):
        run(phase_service.select_current_assignment(repo, OTHER_USER, "ai-1"))


def test_assignment_preserves_neighboring_task_and_workflow_state():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    neighboring = {"1": {"evidence": {"summary": "keep me"}}}
    run(
        repo.update_project(
            USER,
            project["id"],
            {"task_progress": {"1": ["ai-1"]}, "workflow_artifacts": neighboring},
        )
    )
    run(phase_service.select_current_assignment(repo, USER, "human-1"))
    after = run(repo.get_project(USER))
    assert after["task_progress"]["1"] == ["ai-1"]
    assert after["workflow_artifacts"] == neighboring


def test_assignment_has_no_provider_seam():
    source = inspect.getsource(phase_service)
    assert "llm_service" not in source
    assert "provider" not in source.lower()
