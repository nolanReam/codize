"""M18C.1 bounded-assignment Prompt persistence and authority boundaries."""

import copy
import inspect
from pathlib import Path

import pytest

from app.services import phase_service, workflow_service
from app.services.workflow_service import InvalidArtifactError
from tests.fakes import InMemoryProjectRepository
from tests.test_phase_routes import (
    USER_A,
    USER_B,
    activate_project,
    auth_headers,
    client,
)
from tests.test_phase_service import USER, run, seed_active_project
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, SCOPE_PRACTICE


def assigned_prompt(task_id="ai-1", **changes):
    payload = {
        **PROMPT_BUILDER,
        "assignment_task_id": task_id,
        "scope_practice": copy.deepcopy(SCOPE_PRACTICE),
    }
    payload.update(changes)
    return payload


def test_valid_scope_save_derives_objective_and_assignment_authority():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))

    before = copy.deepcopy(run(repo.get_project(USER)))
    saved = run(
        workflow_service.save_section(
            repo, USER, 1, "prompt_builder", assigned_prompt()
        )
    )["artifact"]

    assert saved["scope_practice"] == {
        "objective_id": "bounded_assignment_v1",
        "objective_version": 1,
        "assignment_task_id": "ai-1",
        "assignment_revision": phase_service.assignment_revision(before),
        **SCOPE_PRACTICE,
    }
    assert saved["inputs"] == PROMPT_BUILDER["inputs"]
    after = run(repo.get_project(USER))
    assert after["task_progress"] == before["task_progress"]
    assert after["current_phase"] == before["current_phase"]
    assert after["roadmap"] == before["roadmap"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("finish_condition", " "),
        ("excluded_work", "\n\t"),
        ("inspection_condition", ""),
        ("finish_condition", "x" * 801),
        ("excluded_work", "keep\u0000out"),
        ("inspection_condition", "key sb_secret_example"),
    ],
)
def test_scope_fields_fail_closed_with_field_specific_errors(field, value):
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    scope = {**SCOPE_PRACTICE, field: value}

    with pytest.raises(InvalidArtifactError, match=field):
        run(
            workflow_service.save_section(
                repo,
                USER,
                1,
                "prompt_builder",
                assigned_prompt(scope_practice=scope),
            )
        )


def test_new_assigned_prompt_requires_scope_and_rejects_client_authority_claims():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))

    with pytest.raises(InvalidArtifactError, match="three scope-planning fields"):
        run(
            workflow_service.save_section(
                repo,
                USER,
                1,
                "prompt_builder",
                {**PROMPT_BUILDER, "assignment_task_id": "ai-1"},
            )
        )
    with pytest.raises(InvalidArtifactError, match="objective_id"):
        run(
            workflow_service.save_section(
                repo,
                USER,
                1,
                "prompt_builder",
                assigned_prompt(
                    scope_practice={
                        **SCOPE_PRACTICE,
                        "objective_id": "client_claim",
                        "checklist_complete": True,
                    }
                ),
            )
        )


def test_assignment_mismatch_student_owned_and_old_phase_are_rejected():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-2"))
    with pytest.raises(InvalidArtifactError):
        run(
            workflow_service.save_section(
                repo, USER, 1, "prompt_builder", assigned_prompt("ai-1")
            )
        )

    run(phase_service.select_current_assignment(repo, USER, "human-1"))
    with pytest.raises(InvalidArtifactError):
        run(
            workflow_service.save_section(
                repo, USER, 1, "prompt_builder", assigned_prompt("ai-1")
            )
        )

    run(repo.update_project(USER, project["id"], {"current_phase": 2}))
    with pytest.raises(InvalidArtifactError, match="current phase"):
        run(
            workflow_service.save_section(
                repo, USER, 1, "prompt_builder", assigned_prompt("ai-1")
            )
        )


def test_legacy_bound_prompt_remains_editable_but_scoped_prompt_cannot_strip_scope():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    old = {
        **PROMPT_BUILDER,
        "assignment_task_id": "ai-1",
        "saved_at": "2026-07-20T00:00:00+00:00",
    }
    run(
        repo.update_project(
            USER,
            project["id"],
            {"workflow_artifacts": {"1": {"prompt_builder": old}}},
        )
    )
    edited = run(
        workflow_service.save_section(
            repo,
            USER,
            1,
            "prompt_builder",
            {
                **PROMPT_BUILDER,
                "generated_prompt": "Edited historical Prompt.",
                "assignment_task_id": "ai-1",
            },
        )
    )["artifact"]
    assert edited["generated_prompt"] == "Edited historical Prompt."
    assert edited["scope_practice"] is None

    run(
        workflow_service.save_section(
            repo, USER, 1, "prompt_builder", assigned_prompt()
        )
    )
    with pytest.raises(InvalidArtifactError, match="scope-planning"):
        run(
            workflow_service.save_section(
                repo,
                USER,
                1,
                "prompt_builder",
                {**PROMPT_BUILDER, "assignment_task_id": "ai-1"},
            )
        )


def test_scope_save_preserves_siblings_and_never_completes_a_task():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(workflow_service.save_section(repo, USER, 1, "evidence", EVIDENCE))
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    before_phase = run(phase_service.get_current_phase(repo, USER))

    run(
        workflow_service.save_section(
            repo, USER, 1, "prompt_builder", assigned_prompt()
        )
    )
    state = run(workflow_service.get_phase_artifacts(repo, USER, 1))
    after_phase = run(phase_service.get_current_phase(repo, USER))
    assert state["sections"]["evidence"]["summary"] == EVIDENCE["summary"]
    assert after_phase["completed_task_count"] == before_phase["completed_task_count"] == 0


def test_replaced_roadmap_task_id_gets_a_new_scope_binding_and_preserves_history():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    first = run(
        workflow_service.save_section(
            repo, USER, 1, "prompt_builder", assigned_prompt()
        )
    )["artifact"]

    changed = copy.deepcopy(project["roadmap"])
    changed["phases"][0]["ai_appropriate_tasks"][0] = (
        "Create the replacement study-session form"
    )
    run(repo.update_project(USER, project["id"], {"roadmap": changed}))
    invalidated = phase_service.current_assignment_view(run(repo.get_project(USER)))
    assert invalidated["invalidated_selection"] is True
    assert invalidated["assignment"]["task_id"] == "ai-1"
    assert invalidated["assignment_revision"] != first["scope_practice"]["assignment_revision"]

    run(phase_service.select_current_assignment(repo, USER, "ai-1"))
    second = run(
        workflow_service.save_section(
            repo,
            USER,
            1,
            "prompt_builder",
            assigned_prompt(
                generated_prompt="Prompt for the replacement assignment."
            ),
        )
    )

    assert (
        second["artifact"]["scope_practice"]["assignment_revision"]
        == invalidated["assignment_revision"]
    )
    assert len(second["prompt_history"]) == 1
    assert (
        second["prompt_history"][0]["scope_practice"]["assignment_revision"]
        == first["scope_practice"]["assignment_revision"]
    )


def test_scope_routes_require_auth_and_preserve_user_project_isolation(client):
    assert (
        client.put("/workflow/1/prompt_builder", json=assigned_prompt()).status_code
        == 401
    )
    activate_project(client, USER_A)
    assert client.put(
        "/phases/current/assignment",
        json={"task_id": "ai-1"},
        headers=auth_headers(USER_A),
    ).status_code == 200
    saved = client.put(
        "/workflow/1/prompt_builder",
        json=assigned_prompt(),
        headers=auth_headers(USER_A),
    )
    assert saved.status_code == 200
    assert saved.json()["artifact"]["scope_practice"]["objective_id"] == (
        "bounded_assignment_v1"
    )

    assert client.get("/workflow/1", headers=auth_headers(USER_B)).status_code == 409
    assert client.put(
        "/workflow/1/prompt_builder",
        json=assigned_prompt(),
        headers=auth_headers(USER_B),
    ).status_code == 409
    mine = client.get("/workflow/1", headers=auth_headers(USER_A)).json()
    assert mine["sections"]["prompt_builder"]["assignment_task_id"] == "ai-1"


def test_scope_path_has_no_provider_or_migration():
    source = inspect.getsource(workflow_service)
    assert "llm_service" not in source
    migration_names = [
        path.name
        for path in Path(__file__).parents[2].joinpath("supabase", "migrations").glob("*")
    ]
    assert not any("bounded" in name or "scope_practice" in name for name in migration_names)
