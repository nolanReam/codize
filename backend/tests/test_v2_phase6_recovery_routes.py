"""Phase 6 Recovery route tests over the deterministic repository seam."""

from __future__ import annotations

import uuid

from app.domain.v2 import RecoveryStatus
from tests.test_v2_backend_routes import (
    USER_B,
    auth_headers,
    client,
    create_project,
    select_agent,
    start_change,
)


def _path(project: dict, change: dict, suffix: str) -> str:
    return (
        f"/v2/projects/{project['project_id']}/current-change/"
        f"{change['id']}{suffix}"
    )


def _prepare_linked_handoff(client):
    created = create_project(client, activate=False)["project"]
    item_id = str(uuid.uuid4())
    setup = client.post(
        f"/v2/projects/{created['project_id']}/manual-setup",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": created["version"],
            "project_context": "A small volleyball score tracker",
            "plan_item_id": item_id,
            "change_label": "Show the current score",
            "done_condition": "Changing a point updates the visible score",
        },
    )
    assert setup.status_code == 200, setup.text
    project = setup.json()["project"]
    started = start_change(
        client, project["project_id"], project["version"],
        plan_item_id=item_id, goal="ignored client label",
    )
    assert started.status_code == 200, started.text
    change = started.json()["current_change"]
    confirmed = client.post(
        _path(project, change, "/confirm"), headers=auth_headers(),
        json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
              "expected_current_change_version": change["version"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    change = confirmed.json()["current_change"]
    intervention = client.post(
        _path(project, change, "/teaching/respond"), headers=auth_headers(),
        json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
              "expected_current_change_version": change["version"],
              "context": "prebuild", "response": "Keep point controls working"},
    )
    assert intervention.status_code == 200, intervention.text
    change = intervention.json()["current_change"]
    selected = select_agent(client, project, change)
    change["version"] = selected["current_change_version"]
    project["version"] = selected["project_version"]
    drafted = client.put(
        _path(project, change, "/prompt-draft"), headers=auth_headers(),
        json={"workflow_version": "v2",
              "expected_current_change_version": change["version"],
              "expected_prompt_draft_version": change["prompt_draft_version"],
              "prompt_text": "Add the focused score display change.",
              "done_condition": change["done_condition_snapshot"], "boundaries": []},
    )
    assert drafted.status_code == 200, drafted.text
    change = drafted.json()
    effort = client.post(
        _path(project, change, "/effort-attempts"), headers=auth_headers(),
        json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
              "expected_current_change_version": change["version"], "effort": "quick"},
    )
    assert effort.status_code == 200, effort.text
    change = effort.json()["current_change"]
    accepted = client.post(
        _path(project, change, "/prompt-versions"), headers=auth_headers(),
        json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
              "expected_current_change_version": change["version"],
              "expected_prompt_draft_version": change["prompt_draft_version"]},
    )
    assert accepted.status_code == 200, accepted.text
    change = accepted.json()["current_change"]
    prompt = accepted.json()["prompt_version"]
    handed = client.post(
        _path(project, change, "/handoff"), headers=auth_headers(),
        json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
              "prompt_version_id": prompt["id"],
              "expected_current_change_version": change["version"],
              "expected_prompt_version": prompt["version"]},
    )
    assert handed.status_code == 200, handed.text
    return project, handed.json()["current_change"]


def _enter_recovery(client):
    project, change = _prepare_linked_handoff(client)
    returned = client.post(
        _path(project, change, "/return"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "outcome": "worked",
            "check_id": str(uuid.uuid4()),
        },
    )
    assert returned.status_code == 200, returned.text
    returned_body = returned.json()
    change = returned_body["current_change"]
    check = returned_body["check"]
    failed = client.post(
        _path(project, change, f"/checks/{check['id']}"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_check_version": check["version"],
            "result": "did_not_work",
            "observation": "The score still stays at zero after I add a point.",
            "performed_by_student": True,
            "next_check_id": None,
        },
    )
    assert failed.status_code == 200, failed.text
    change = failed.json()["current_change"]
    recovery_id = str(uuid.uuid4())
    command_id = str(uuid.uuid4())
    symptom_body = {
        "workflow_version": "v2",
        "command_id": command_id,
        "recovery_case_id": recovery_id,
        "expected_current_change_version": change["version"],
        "observed_symptom": "The score still stays at zero after I add a point.",
        "last_known_working_statement": "It updated before the reducer edit.",
        "last_known_working_certainty": "yes",
    }
    cross_owner = client.post(
        _path(project, change, "/recovery/symptom"),
        headers=auth_headers(USER_B),
        json=symptom_body,
    )
    assert cross_owner.status_code == 404
    symptom = client.post(
        _path(project, change, "/recovery/symptom"),
        headers=auth_headers(),
        json=symptom_body,
    )
    replay = client.post(
        _path(project, change, "/recovery/symptom"),
        headers=auth_headers(),
        json=symptom_body,
    )
    assert symptom.status_code == replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["current_change"]["version"] == symptom.json()["current_change"]["version"]
    assert symptom.json()["recovery_case"]["observed_symptom"] == symptom_body["observed_symptom"]
    return project, symptom.json()


def _accept_and_handoff(client, project: dict, state: dict, purpose: str) -> dict:
    change = state["current_change"]
    recovery = state["recovery_case"]
    build = client.get(
        _path(project, change, "/build-state"), headers=auth_headers()
    ).json()
    accept_body = {
        "workflow_version": "v2",
        "command_id": str(uuid.uuid4()),
        "recovery_case_id": recovery["id"],
        "purpose": purpose,
        "expected_current_change_version": change["version"],
        "expected_prompt_draft_version": build["prompt_draft_version"],
    }
    accepted = client.post(
        _path(project, change, "/recovery/prompt"),
        headers=auth_headers(),
        json=accept_body,
    )
    replay = client.post(
        _path(project, change, "/recovery/prompt"),
        headers=auth_headers(),
        json=accept_body,
    )
    assert accepted.status_code == replay.status_code == 200, accepted.text
    assert replay.json()["replayed"] is True
    accepted_body = accepted.json()
    prompt = accepted_body["prompt_version"]
    handed_off = client.post(
        _path(project, change, "/recovery/handoff"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "recovery_case_id": recovery["id"],
            "prompt_version_id": prompt["id"],
            "expected_current_change_version": accepted_body["current_change"]["version"],
            "expected_prompt_version": prompt["version"],
        },
    )
    assert handed_off.status_code == 200, handed_off.text
    return handed_off.json()


def _prepare_recheck(client):
    project, symptom = _enter_recovery(client)
    diagnostic = _accept_and_handoff(client, project, symptom, "diagnostic")
    assert "DO NOT MODIFY FILES YET" in diagnostic["exact_prompt"]
    generic = client.post(
        _path(project, diagnostic["current_change"], "/recovery/investigation-return"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "recovery_case_id": diagnostic["recovery_case"]["id"],
            "expected_current_change_version": diagnostic["current_change"]["version"],
            "finding": "The AI says it fixed it.",
        },
    )
    assert generic.status_code == 409
    finding = "The score action reaches totalsReducer, but the increment branch returns the old state."
    investigated = client.post(
        _path(project, diagnostic["current_change"], "/recovery/investigation-return"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "recovery_case_id": diagnostic["recovery_case"]["id"],
            "expected_current_change_version": diagnostic["current_change"]["version"],
            "finding": finding,
        },
    )
    assert investigated.status_code == 200, investigated.text
    assert investigated.json()["recovery_case"]["investigation_finding_provenance"] == "agent_claimed"
    correction = _accept_and_handoff(client, project, investigated.json(), "correction")
    assert "smallest targeted change" in correction["exact_prompt"]
    assert "Do not claim the bug is fixed" in correction["exact_prompt"]
    check_id = str(uuid.uuid4())
    returned = client.post(
        _path(project, correction["current_change"], "/recovery/correction-return"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "recovery_case_id": correction["recovery_case"]["id"],
            "check_id": check_id,
            "expected_current_change_version": correction["current_change"]["version"],
        },
    )
    assert returned.status_code == 200, returned.text
    return project, returned.json()


def test_phase6_recovery_resolves_only_after_student_recheck_and_atomic_completion(client):
    project, state = _prepare_recheck(client)
    change, recovery, check = (
        state["current_change"], state["recovery_case"], state["check"]
    )
    checked = client.post(
        _path(project, change, f"/recovery/checks/{check['id']}"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "recovery_case_id": recovery["id"],
            "expected_current_change_version": change["version"],
            "expected_check_version": check["version"],
            "result": "worked",
            "observation": "I added a point and personally saw the score change from 0 to 1.",
            "performed_by_student": True,
            "next_check_id": None,
        },
    )
    assert checked.status_code == 200, checked.text
    state = checked.json()
    build = client.get(
        _path(project, state["current_change"], "/build-state"), headers=auth_headers()
    ).json()
    assert build["build_stage"] == "ready_to_complete"
    completion_body = {
        "workflow_version": "v2",
        "command_id": str(uuid.uuid4()),
        "expected_current_change_version": state["current_change"]["version"],
        "expected_plan_version": project["plan_version"],
        "expected_plan_item_version": 1,
    }
    completed = client.post(
        _path(project, state["current_change"], "/complete"),
        headers=auth_headers(),
        json=completion_body,
    )
    replay = client.post(
        _path(project, state["current_change"], "/complete"),
        headers=auth_headers(),
        json=completion_body,
    )
    assert completed.status_code == replay.status_code == 200, completed.text
    assert completed.json()["current_change"]["lifecycle_state"] == "completed"
    assert replay.json()["replayed"] is True
    stored = client.app.state.test_v2_repo._recovery_cases[uuid.UUID(recovery["id"])][1]
    assert stored.status is RecoveryStatus.RESOLVED
    assert stored.resolution_summary == "I added a point and personally saw the score change from 0 to 1."


def test_phase6_unsure_stays_incomplete_and_failed_recheck_loops_to_investigation(client):
    project, state = _prepare_recheck(client)
    change, recovery, check = (
        state["current_change"], state["recovery_case"], state["check"]
    )
    next_check_id = str(uuid.uuid4())
    unsure = client.post(
        _path(project, change, f"/recovery/checks/{check['id']}"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "recovery_case_id": recovery["id"],
            "expected_current_change_version": change["version"],
            "expected_check_version": check["version"],
            "result": "unsure",
            "observation": "The score flashed too quickly for me to tell.",
            "performed_by_student": True,
            "next_check_id": next_check_id,
        },
    )
    assert unsure.status_code == 200, unsure.text
    assert unsure.json()["next_check"]["id"] == next_check_id
    state = unsure.json()
    failed = client.post(
        _path(project, state["current_change"], f"/recovery/checks/{next_check_id}"),
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "recovery_case_id": recovery["id"],
            "expected_current_change_version": state["current_change"]["version"],
            "expected_check_version": state["next_check"]["version"],
            "result": "did_not_work",
            "observation": "I tried again slowly and the score remained zero.",
            "performed_by_student": True,
            "next_check_id": None,
        },
    )
    assert failed.status_code == 200, failed.text
    build = client.get(
        _path(project, failed.json()["current_change"], "/build-state"),
        headers=auth_headers(),
    ).json()
    assert build["build_stage"] == "recovery_investigate"
    assert build["recovery_case"]["status"] == "investigating"
    assert build["recovery_case"]["observed_symptom"] == recovery["observed_symptom"]
