"""Focused V2.3A API tests over the deterministic in-memory repository seam."""

from __future__ import annotations

import asyncio
import time
import uuid
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import security
from app.domain.v2 import CurrentChangeState
from app.main import create_app
from app.services.project_repository import get_project_repository
from app.services.v2_repository import get_v2_repository
from tests.fakes import InMemoryProjectRepository, InMemoryV2Repository

USER_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
UNKNOWN_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
_key = ec.generate_private_key(ec.SECP256R1())


def auth_headers(user_id: str = USER_A) -> dict[str, str]:
    claims = {
        "sub": user_id,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    token = pyjwt.encode(claims, _key, algorithm="ES256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://stub-project.supabase.co")
    monkeypatch.setattr(
        security,
        "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=_key.public_key())
        ),
    )
    app = create_app()
    v2_repo = InMemoryV2Repository()
    legacy_repo = InMemoryProjectRepository()
    app.dependency_overrides[get_v2_repository] = lambda: v2_repo
    app.dependency_overrides[get_project_repository] = lambda: legacy_repo
    app.state.test_v2_repo = v2_repo
    app.state.test_legacy_repo = legacy_repo
    return TestClient(app)


def create_project(
    client: TestClient,
    *,
    name: str = "Volleyball Tracker",
    intent: str = "new_idea",
    user_id: str = USER_A,
    command_id: str | None = None,
    activate: bool = True,
) -> dict:
    current_change_command_id = str(uuid.uuid4())
    recovery_context = {
        "project_context": "A volleyball statistics tracker",
        "intended_behavior": "Restore player totals",
        "observed_symptom": "Player totals no longer update",
        "last_known_working_statement": "Totals worked before the last AI edit",
        "last_known_working_certainty": "yes",
        "candidate_change_summary": "The AI changed the totals reducer",
    }
    payload = {
        "workflow_version": "v2",
        "command_id": command_id or str(uuid.uuid4()),
        "display_name": name,
        "creation_intent": intent,
    }
    if intent == "recovery_first":
        payload.update(
            current_change_command_id=current_change_command_id,
            recovery_context=recovery_context,
        )
    response = client.post(
        "/v2/projects",
        headers=auth_headers(user_id),
        json=payload,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    if activate and intent != "recovery_first" and not result["replayed"]:
        repo = client.app.state.test_v2_repo
        repo.activate_project_for_test(user_id, uuid.UUID(result["project"]["project_id"]))
        result["project"] = client.get(
            f"/v2/projects/{result['project']['project_id']}",
            headers=auth_headers(user_id),
        ).json()
    return result


def add_plan_items(
    client: TestClient,
    project: dict,
    *,
    user_id: str = USER_A,
    count: int = 2,
    command_id: str | None = None,
) -> tuple[dict, list[str]]:
    item_ids = [str(uuid.uuid4()) for _ in range(count)]
    response = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(user_id),
        json={
            "workflow_version": "v2",
            "command_id": command_id or str(uuid.uuid4()),
            "expected_project_version": project["version"],
            "expected_plan_version": project["plan_version"],
            "operations": [
                {
                    "action": "add",
                    "plan_item_id": item_id,
                    "label": f"Plan item {index}",
                    "intended_outcome": f"Observable result {index}",
                    "scope_band": "first_version",
                    "status": "ready",
                    "order_key": index * 10,
                }
                for index, item_id in enumerate(item_ids, start=1)
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json(), item_ids


def start_change(
    client: TestClient,
    project_id: str,
    expected_project_version: int,
    *,
    plan_item_id: str | None = None,
    user_id: str = USER_A,
    command_id: str | None = None,
    kind: str = "build",
    goal: str = "Add player totals",
):
    return client.post(
        f"/v2/projects/{project_id}/current-change",
        headers=auth_headers(user_id),
        json={
            "workflow_version": "v2",
            "command_id": command_id or str(uuid.uuid4()),
            "expected_project_version": expected_project_version,
            "plan_item_id": plan_item_id,
            "change_kind": kind,
            "goal_snapshot": goal,
        },
    )


def prepare_v23b_change(client: TestClient) -> tuple[dict, dict]:
    project = create_project(client)["project"]
    started = start_change(client, project["project_id"], project["version"])
    assert started.status_code == 200, started.text
    change = started.json()["current_change"]
    resolved = client.app.state.test_v2_repo.resolve_policy_for_test(
        USER_A, uuid.UUID(project["project_id"]), uuid.UUID(change["id"])
    )
    change["version"] = resolved.version
    change["resume_step"] = resolved.resume_step.value
    return project, change


def test_phase4_manual_loop_completes_only_after_student_check(client):
    created = create_project(client, activate=False)["project"]
    item_id = str(uuid.uuid4())
    setup = client.post(
        f"/v2/projects/{created['project_id']}/manual-setup",
        headers=auth_headers(),
        json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
              "expected_project_version": created["version"],
              "project_context": "A small volleyball score tracker",
              "plan_item_id": item_id, "change_label": "Show the current score",
              "done_condition": "Changing a point updates the visible score"},
    )
    assert setup.status_code == 200, setup.text
    project = setup.json()["project"]
    started = start_change(client, project["project_id"], project["version"],
                           plan_item_id=item_id, goal="ignored client label")
    assert started.status_code == 200, started.text
    change = started.json()["current_change"]
    assert change["goal_snapshot"] == "ignored client label"  # fake preserves legacy seam

    confirmed = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/confirm",
        headers=auth_headers(), json={"workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    change = confirmed.json()["current_change"]
    assert change["done_condition_snapshot"] == "Changing a point updates the visible score"

    selected = select_agent(client, project, change)
    change["version"] = selected["current_change_version"]
    project["version"] = selected["project_version"]
    drafted = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-draft",
        headers=auth_headers(), json={"workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change["prompt_draft_version"],
            "prompt_text": "Add the focused score display change.",
            "done_condition": change["done_condition_snapshot"], "boundaries": []},
    )
    assert drafted.status_code == 200, drafted.text
    change = drafted.json()
    effort = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/effort",
        headers=auth_headers(), json={"workflow_version": "v2",
            "expected_current_change_version": change["version"], "effort": "standard"},
    )
    assert effort.status_code == 200, effort.text
    change = effort.json()
    accepted = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-versions",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change["prompt_draft_version"]},
    )
    assert accepted.status_code == 200, accepted.text
    change = accepted.json()["current_change"]
    prompt = accepted.json()["prompt_version"]
    handed = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/handoff",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "prompt_version_id": prompt["id"], "expected_current_change_version": change["version"],
            "expected_prompt_version": prompt["version"]},
    )
    assert handed.status_code == 200, handed.text
    change = handed.json()["current_change"]

    check_id = str(uuid.uuid4())
    returned = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/return",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"], "outcome": "worked",
            "check_id": check_id},
    )
    assert returned.status_code == 200, returned.text
    change = returned.json()["current_change"]
    check = returned.json()["check"]

    rejected_claim = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/checks/{check_id}",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"], "expected_check_version": check["version"],
            "result": "worked", "observation": "The agent said it passed",
            "performed_by_student": False, "next_check_id": None},
    )
    assert rejected_claim.status_code == 422

    checked = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/checks/{check_id}",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"], "expected_check_version": check["version"],
            "result": "worked", "observation": "I added a point and saw the score change",
            "performed_by_student": True, "next_check_id": None},
    )
    assert checked.status_code == 200, checked.text
    change = checked.json()["current_change"]
    completion_command = str(uuid.uuid4())
    completion_body = {"workflow_version": "v2", "command_id": completion_command,
        "expected_current_change_version": change["version"],
        "expected_plan_version": project["plan_version"], "expected_plan_item_version": 1}
    completion_path = f"/v2/projects/{project['project_id']}/current-change/{change['id']}/complete"
    completion = client.post(
        completion_path, headers=auth_headers(), json=completion_body,
    )
    assert completion.status_code == 200, completion.text
    assert completion.json()["current_change"]["lifecycle_state"] == "completed"
    assert completion.json()["plan"]["items"][0]["status"] == "done"
    assert completion.json()["check"]["student_observation"] == "I added a point and saw the score change"
    replay = client.post(completion_path, headers=auth_headers(), json=completion_body)
    assert replay.status_code == 200, replay.text
    assert replay.json()["replayed"] is True
    assert replay.json()["plan"]["plan_version"] == completion.json()["plan"]["plan_version"]
    recent = client.get(f"/v2/projects/{project['project_id']}/recent-changes",
                        headers=auth_headers()).json()["recent_changes"]
    assert recent[0]["observation"] == "I added a point and saw the score change"


@pytest.mark.parametrize("intent", ["new_idea", "already_building"])
def test_phase4_setup_intents_reach_a_resumable_first_change(client, intent):
    created = create_project(client, intent=intent, activate=False)["project"]
    draft_refs = client.get("/v2/project-refs", headers=auth_headers()).json()["projects"]
    draft_ref = next(ref for ref in draft_refs if ref["project_id"] == created["project_id"])
    assert draft_ref["lifecycle_state"] == "draft"
    assert draft_ref["setup_resume_step"] == created["setup_resume_step"]
    item_id = str(uuid.uuid4())
    setup_path = f"/v2/projects/{created['project_id']}/manual-setup"
    setup_payload = {"workflow_version": "v2", "command_id": str(uuid.uuid4()),
        "expected_project_version": created["version"], "project_context": "A real student project",
        "plan_item_id": item_id, "change_label": "Add one useful interaction",
        "done_condition": "The interaction visibly responds"}
    stale_setup = client.post(setup_path, headers=auth_headers(), json={
        **setup_payload, "command_id": str(uuid.uuid4()),
        "expected_project_version": created["version"] + 1,
    })
    assert stale_setup.status_code == 409
    setup = client.post(setup_path, headers=auth_headers(), json=setup_payload)
    assert setup.status_code == 200, setup.text
    project = setup.json()["project"]

    # Simulate a successful response being lost and a fresh browser session
    # retrying from durable Project state with entirely new client IDs.
    fresh_retry = client.post(setup_path, headers=auth_headers(), json={
        **setup_payload, "command_id": str(uuid.uuid4()),
        "plan_item_id": str(uuid.uuid4()),
    })
    assert fresh_retry.status_code == 200, fresh_retry.text
    assert fresh_retry.json()["replayed"] is True
    assert fresh_retry.json()["plan_item"]["id"] == item_id
    refreshed_plan = client.get(
        f"/v2/projects/{created['project_id']}/plan", headers=auth_headers()
    ).json()
    assert [item["id"] for item in refreshed_plan["items"]] == [item_id]
    assert refreshed_plan["plan_version"] == project["plan_version"]
    mismatched_retry = client.post(setup_path, headers=auth_headers(), json={
        **setup_payload, "command_id": str(uuid.uuid4()),
        "plan_item_id": str(uuid.uuid4()), "change_label": "A different initial item",
    })
    assert mismatched_retry.status_code == 409
    assert len(client.get(
        f"/v2/projects/{created['project_id']}/plan", headers=auth_headers()
    ).json()["items"]) == 1

    started = start_change(client, project["project_id"], project["version"], plan_item_id=item_id)
    assert started.status_code == 200, started.text
    duplicate = start_change(client, project["project_id"], project["version"], plan_item_id=item_id)
    assert duplicate.status_code == 409
    resumed = client.get(f"/v2/projects/{project['project_id']}/current-change",
                         headers=auth_headers()).json()["current_change"]
    assert resumed["id"] == started.json()["current_change"]["id"]


def select_agent(client: TestClient, project: dict, change: dict, choice: str = "codex") -> dict:
    response = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/coding-agent",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_project_version": project["version"],
            "expected_current_change_version": change["version"],
            "choice": choice,
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    project["version"] = result["project_version"]
    change["version"] = result["current_change_version"]
    return result


def save_prompt(
    client: TestClient,
    project: dict,
    change: dict,
    text: str = "Add totals safely",
    done_condition: str | None = "Totals are correct",
    boundaries: list[str] | None = None,
) -> dict:
    if boundaries is None:
        boundaries = ["Keep existing scoring behavior"]
    response = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-draft",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change.get("prompt_draft_version", 1),
            "prompt_text": text,
            "done_condition": done_condition,
            "boundaries": boundaries,
        },
    )
    assert response.status_code == 200, response.text
    change.update(response.json())
    return response.json()


def accept_ready_v23b_prompt(
    client: TestClient,
    project: dict,
    change: dict,
    *,
    agent: str = "codex",
    effort: str = "standard",
    prompt_text: str = "Add totals safely",
) -> dict:
    select_agent(client, project, change, agent)
    save_prompt(client, project, change, prompt_text)
    effort_response = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/effort",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "effort": effort,
        },
    )
    assert effort_response.status_code == 200, effort_response.text
    change.update(effort_response.json())
    accepted = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-versions",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change["prompt_draft_version"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    result = accepted.json()
    change.update(result["current_change"])
    return result


def prepare_handed_off_change(client: TestClient) -> tuple[dict, dict]:
    project, change = prepare_v23b_change(client)
    accepted = accept_ready_v23b_prompt(client, project, change)
    prompt = accepted["prompt_version"]
    handed = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/handoff",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "prompt_version_id": prompt["id"], "expected_current_change_version": change["version"],
            "expected_prompt_version": prompt["version"]},
    )
    assert handed.status_code == 200, handed.text
    return project, handed.json()["current_change"]


def test_phase4_unsure_check_creates_retry_and_duplicate_return_replays(client):
    project, change = prepare_handed_off_change(client)
    check_id = str(uuid.uuid4())
    command_id = str(uuid.uuid4())
    body = {"workflow_version": "v2", "command_id": command_id,
        "expected_current_change_version": change["version"], "outcome": "unsure",
        "check_id": check_id}
    path = f"/v2/projects/{project['project_id']}/current-change/{change['id']}/return"
    first = client.post(path, headers=auth_headers(), json=body)
    replay = client.post(path, headers=auth_headers(), json=body)
    assert first.status_code == replay.status_code == 200
    assert replay.json()["replayed"] is True
    change = first.json()["current_change"]
    check = first.json()["check"]
    next_id = str(uuid.uuid4())
    check_path = f"/v2/projects/{project['project_id']}/current-change/{change['id']}/checks/{check_id}"
    unsure_command = str(uuid.uuid4())
    unsure_body = {"workflow_version": "v2", "command_id": unsure_command,
            "expected_current_change_version": change["version"], "expected_check_version": check["version"],
            "result": "unsure", "observation": "I could not tell whether the number refreshed",
            "performed_by_student": True, "next_check_id": next_id}
    unsure = client.post(check_path, headers=auth_headers(), json=unsure_body)
    assert unsure.status_code == 200, unsure.text
    first_unsure = unsure.json()
    assert first_unsure["check"]["status"] == "performed"
    assert first_unsure["check"]["student_observation"] == "I could not tell whether the number refreshed"
    assert first_unsure["next_check"]["id"] == next_id
    assert first_unsure["current_change"]["version"] == change["version"] + 1

    unsure_replay = client.post(check_path, headers=auth_headers(), json=unsure_body)
    assert unsure_replay.status_code == 200, unsure_replay.text
    assert unsure_replay.json()["replayed"] is True
    assert unsure_replay.json()["current_change"]["version"] == first_unsure["current_change"]["version"]

    second_next_id = str(uuid.uuid4())
    second_command = str(uuid.uuid4())
    second_unsure = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/checks/{next_id}",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": second_command,
            "expected_current_change_version": first_unsure["current_change"]["version"],
            "expected_check_version": first_unsure["next_check"]["version"],
            "result": "unsure", "observation": "The display still does not make the refresh clear",
            "performed_by_student": True, "next_check_id": second_next_id},
    )
    assert second_unsure.status_code == 200, second_unsure.text
    assert second_unsure.json()["check"]["student_observation"] == "The display still does not make the refresh clear"
    assert second_unsure.json()["current_change"]["version"] == change["version"] + 2
    assert second_unsure.json()["next_check"]["id"] == second_next_id
    state = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers()).json()
    assert state["build_stage"] == "check_unsure"
    assert state["active_check"]["id"] == second_next_id
    completion = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/complete",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": state["current_change_version"],
            "expected_plan_version": project["plan_version"], "expected_plan_item_version": 1},
    )
    assert completion.status_code == 409


def test_phase4_failed_check_never_completes_and_cross_owner_cannot_report(client):
    project, change = prepare_handed_off_change(client)
    cross_owner = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/return",
        headers=auth_headers(USER_B), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"], "outcome": "worked",
            "check_id": str(uuid.uuid4())},
    )
    assert cross_owner.status_code == 404
    check_id = str(uuid.uuid4())
    stale_return = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/return",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"] + 1, "outcome": "worked",
            "check_id": check_id},
    )
    assert stale_return.status_code == 409
    returned = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/return",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"], "outcome": "worked", "check_id": check_id},
    )
    change = returned.json()["current_change"]
    check = returned.json()["check"]
    stale_check = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/checks/{check_id}",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"], "expected_check_version": check["version"] + 1,
            "result": "did_not_work", "observation": "The score stayed at zero",
            "performed_by_student": True, "next_check_id": None},
    )
    assert stale_check.status_code == 409
    failed = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/checks/{check_id}",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"], "expected_check_version": check["version"],
            "result": "did_not_work", "observation": "The score stayed at zero",
            "performed_by_student": True, "next_check_id": None},
    )
    assert failed.status_code == 200, failed.text
    change = failed.json()["current_change"]
    state = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers()).json()
    assert state["build_stage"] == "check_failed"
    completion = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/complete",
        headers=auth_headers(), json={"workflow_version": "v2", "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_plan_version": project["plan_version"], "expected_plan_item_version": 1},
    )
    assert completion.status_code == 409


def test_phase4_dialogue_sound_preference_persists_and_is_owner_scoped(client):
    initial = client.get("/v2/preferences", headers=auth_headers()).json()
    assert initial == {"dialogue_sound_enabled": True, "motion_preference": "system", "version": 0}
    saved = client.put("/v2/preferences/dialogue-sound", headers=auth_headers(),
        json={"expected_version": 0, "dialogue_sound_enabled": False})
    assert saved.status_code == 200, saved.text
    assert client.get("/v2/preferences", headers=auth_headers()).json()["dialogue_sound_enabled"] is False
    assert client.get("/v2/preferences", headers=auth_headers(USER_B)).json()["dialogue_sound_enabled"] is True
    replay = client.put("/v2/preferences/dialogue-sound", headers=auth_headers(),
        json={"expected_version": 0, "dialogue_sound_enabled": False})
    assert replay.status_code == 200
    assert replay.json()["version"] == saved.json()["version"]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        (
            "POST",
            "/v2/projects",
            {
                "workflow_version": "v2",
                "command_id": "10000000-0000-4000-8000-000000000001",
                "display_name": "Private Project",
                "creation_intent": "new_idea",
            },
        ),
        ("GET", "/v2/project-refs", None),
        ("GET", f"/v2/projects/{UNKNOWN_ID}", None),
        (
            "POST",
            f"/v2/projects/{UNKNOWN_ID}/promote",
            {
                "workflow_version": "v2",
                "command_id": "10000000-0000-4000-8000-000000000002",
                "expected_project_version": 1,
            },
        ),
        (
            "POST",
            f"/v2/projects/{UNKNOWN_ID}/discard-temporary",
            {"workflow_version": "v2", "expected_project_version": 1},
        ),
        ("GET", f"/v2/projects/{UNKNOWN_ID}/plan", None),
        (
            "POST",
            f"/v2/projects/{UNKNOWN_ID}/plan/mutations",
            {
                "workflow_version": "v2",
                "command_id": "10000000-0000-4000-8000-000000000003",
                "expected_project_version": 1,
                "expected_plan_version": 1,
                "operations": [
                    {
                        "action": "add",
                        "plan_item_id": "10000000-0000-4000-8000-000000000004",
                        "label": "Private",
                        "intended_outcome": "Private outcome",
                        "scope_band": "first_version",
                        "status": "ready",
                        "order_key": 10,
                    }
                ],
            },
        ),
        (
            "POST",
            f"/v2/projects/{UNKNOWN_ID}/current-change",
            {
                "workflow_version": "v2",
                "command_id": "10000000-0000-4000-8000-000000000005",
                "expected_project_version": 1,
                "change_kind": "build",
                "goal_snapshot": "Private goal",
            },
        ),
        ("GET", f"/v2/projects/{UNKNOWN_ID}/current-change", None),
        (
            "POST",
            f"/v2/projects/{UNKNOWN_ID}/current-change/{UNKNOWN_ID}/cancel",
            {
                "workflow_version": "v2",
                "command_id": "10000000-0000-4000-8000-000000000006",
                "expected_current_change_version": 1,
                "reason": "student_cancelled",
            },
        ),
    ],
)
def test_every_v2_route_requires_verified_auth(client, method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 401
    assert response.json()["error"]["status"] == 401


def test_project_create_is_idempotent_and_get_is_explicit_not_newest(client):
    command_id = str(uuid.uuid4())
    first = create_project(client, name="First", command_id=command_id)
    replay = create_project(client, name="First", command_id=command_id)
    second = create_project(client, name="Second")

    assert replay["replayed"] is True
    assert replay["project"]["project_id"] == first["project"]["project_id"]
    first_read = client.get(
        f"/v2/projects/{first['project']['project_id']}",
        headers=auth_headers(),
    )
    second_read = client.get(
        f"/v2/projects/{second['project']['project_id']}",
        headers=auth_headers(),
    )
    assert first_read.json()["display_name"] == "First"
    assert second_read.json()["display_name"] == "Second"
    assert first_read.json()["project_id"] != second_read.json()["project_id"]


def test_absent_and_cross_owner_project_ids_return_the_same_safe_not_found(client):
    project = create_project(client)["project"]
    cross_owner = client.get(
        f"/v2/projects/{project['project_id']}",
        headers=auth_headers(USER_B),
    )
    absent = client.get(
        f"/v2/projects/{UNKNOWN_ID}",
        headers=auth_headers(USER_B),
    )
    assert cross_owner.status_code == absent.status_code == 404
    assert cross_owner.json() == absent.json() == {
        "error": {"status": 404, "message": "V2 Project not found."}
    }


def test_cross_owner_project_plan_and_current_change_writes_fail_safely(client):
    project = create_project(client)["project"]
    project_id = project["project_id"]

    promote = client.post(
        f"/v2/projects/{project_id}/promote",
        headers=auth_headers(USER_B),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": project["version"],
        },
    )
    plan = client.post(
        f"/v2/projects/{project_id}/plan/mutations",
        headers=auth_headers(USER_B),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": project["version"],
            "expected_plan_version": project["plan_version"],
            "operations": [
                {
                    "action": "add",
                    "plan_item_id": str(uuid.uuid4()),
                    "label": "Must stay absent",
                    "intended_outcome": "No other owner can create this item",
                    "scope_band": "first_version",
                    "status": "ready",
                    "order_key": 10,
                }
            ],
        },
    )
    change = start_change(
        client,
        project_id,
        project["version"],
        user_id=USER_B,
    )

    assert promote.status_code == plan.status_code == change.status_code == 404
    owner_plan = client.get(
        f"/v2/projects/{project_id}/plan",
        headers=auth_headers(USER_A),
    )
    assert owner_plan.status_code == 200
    assert owner_plan.json()["items"] == []
    assert client.get(
        f"/v2/projects/{project_id}/current-change",
        headers=auth_headers(USER_A),
    ).json()["current_change"] is None


def test_v1_and_v2_refs_remain_distinct_and_only_one_legacy_row_is_advertised(client):
    legacy = client.app.state.test_legacy_repo
    first_legacy = asyncio.run(legacy.create_project(USER_A, {}))
    second_legacy = asyncio.run(legacy.create_project(USER_A, {}))
    v2 = create_project(client, name="Explicit V2")["project"]

    response = client.get("/v2/project-refs", headers=auth_headers())
    assert response.status_code == 200
    refs = response.json()["projects"]
    legacy_refs = [ref for ref in refs if ref["workflow_version"] == "v1"]
    v2_refs = [ref for ref in refs if ref["workflow_version"] == "v2"]
    assert len(legacy_refs) == 1
    assert legacy_refs[0]["project_id"] == second_legacy["id"]
    assert legacy_refs[0]["project_id"] != first_legacy["id"]
    assert legacy_refs[0]["open_mode"] == "legacy_active_only"
    assert [(ref["project_id"], ref["open_mode"]) for ref in v2_refs] == [
        (v2["project_id"], "explicit")
    ]


@pytest.mark.parametrize("path_kind", ["project", "plan", "current_change"])
def test_v2_mutations_reject_a_v1_workflow_reference(client, path_kind):
    project = create_project(client)["project"]
    if path_kind == "project":
        path = "/v2/projects"
        body = {
            "workflow_version": "v1",
            "command_id": str(uuid.uuid4()),
            "display_name": "Wrong version",
            "creation_intent": "new_idea",
        }
    elif path_kind == "plan":
        path = f"/v2/projects/{project['project_id']}/plan/mutations"
        body = {
            "workflow_version": "v1",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": 1,
            "expected_plan_version": 1,
            "operations": [
                {
                    "action": "add",
                    "plan_item_id": str(uuid.uuid4()),
                    "label": "Wrong",
                    "intended_outcome": "Wrong workflow",
                    "scope_band": "first_version",
                    "status": "ready",
                    "order_key": 10,
                }
            ],
        }
    else:
        path = f"/v2/projects/{project['project_id']}/current-change"
        body = {
            "workflow_version": "v1",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": 1,
            "change_kind": "build",
            "goal_snapshot": "Wrong workflow",
        }
    response = client.post(path, headers=auth_headers(), json=body)
    assert response.status_code == 422
    assert response.json() == {"error": {"status": 422, "message": "Invalid request."}}


def test_temporary_project_can_be_promoted_and_another_can_be_safely_purged(client):
    create_command_id = str(uuid.uuid4())
    temporary = create_project(
        client,
        intent="recovery_first",
        command_id=create_command_id,
    )["project"]
    assert temporary["lifecycle_state"] == "temporary_recovery"
    client.app.state.test_v2_repo.set_recovery_flow_for_test(
        USER_A,
        uuid.UUID(temporary["project_id"]),
        case_statuses=["resolved"],
        change_state=CurrentChangeState.COMPLETED,
    )
    promotion_command_id = str(uuid.uuid4())
    promoted = client.post(
        f"/v2/projects/{temporary['project_id']}/promote",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": promotion_command_id,
            "expected_project_version": temporary["version"],
        },
    )
    assert promoted.status_code == 200
    assert promoted.json()["project"]["lifecycle_state"] == "active"
    assert promoted.json()["project"]["setup_resume_step"] == "existing_project_context"
    assert promoted.json()["project"]["version"] == 2
    create_replay = create_project(
        client,
        intent="recovery_first",
        command_id=create_command_id,
    )
    assert create_replay["replayed"] is True
    assert create_replay["project"]["lifecycle_state"] == "active"
    assert create_replay["project"]["version"] == 2
    promotion_replay = client.post(
        f"/v2/projects/{temporary['project_id']}/promote",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": promotion_command_id,
            "expected_project_version": temporary["version"],
        },
    )
    assert promotion_replay.status_code == 200
    assert promotion_replay.json()["replayed"] is True

    discarded = create_project(client, name="Temporary", intent="recovery_first")["project"]
    path = f"/v2/projects/{discarded['project_id']}/discard-temporary"
    body = {"workflow_version": "v2", "expected_project_version": 1}
    assert client.post(path, headers=auth_headers(), json=body).status_code == 200
    assert client.get(
        f"/v2/projects/{discarded['project_id']}", headers=auth_headers()
    ).status_code == 404
    # Absence and other-owner mismatch intentionally replay the same safe success.
    assert client.post(path, headers=auth_headers(), json=body).status_code == 200
    assert client.post(path, headers=auth_headers(USER_B), json=body).status_code == 200


@pytest.mark.parametrize(
    ("intent", "expected_step"),
    [("new_idea", "idea_capture"), ("already_building", "existing_project_context")],
)
def test_display_name_creation_stays_in_canonical_setup(client, intent, expected_step):
    created = create_project(client, intent=intent, activate=False)["project"]
    assert created["lifecycle_state"] == "draft"
    assert created["setup_resume_step"] == expected_step


def test_recovery_first_requires_context_and_starts_unresolved_recovery_work(client):
    denied = client.post(
        "/v2/projects",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "display_name": "Broken tracker",
            "creation_intent": "recovery_first",
        },
    )
    assert denied.status_code == 422

    temporary = create_project(client, intent="recovery_first")["project"]
    current = client.get(
        f"/v2/projects/{temporary['project_id']}/current-change",
        headers=auth_headers(),
    ).json()["current_change"]
    assert temporary["lifecycle_state"] == "temporary_recovery"
    assert temporary["setup_resume_step"] == "recovery_context"
    assert current["change_kind"] == "recovery"
    assert current["lifecycle_state"] == "preparing"
    assert current["resume_step"] == "confirm_change"


@pytest.mark.parametrize(
    ("case_statuses", "change_state"),
    [
        ([], CurrentChangeState.COMPLETED),
        (["open"], CurrentChangeState.RECOVERING),
        (["abandoned"], CurrentChangeState.CANCELLED),
        (["resolved"], CurrentChangeState.RECOVERING),
    ],
)
def test_temporary_promotion_rejects_unresolved_or_incomplete_recovery(
    client, case_statuses, change_state
):
    project = create_project(client, intent="recovery_first")["project"]
    client.app.state.test_v2_repo.set_recovery_flow_for_test(
        USER_A,
        uuid.UUID(project["project_id"]),
        case_statuses=case_statuses,
        change_state=change_state,
    )
    response = client.post(
        f"/v2/projects/{project['project_id']}/promote",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": project["version"],
        },
    )
    assert response.status_code == 409


def test_active_project_is_not_a_promotion_replay_without_matching_provenance(client):
    project = create_project(client)["project"]
    response = client.post(
        f"/v2/projects/{project['project_id']}/promote",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": project["version"],
        },
    )
    assert response.status_code == 409


def test_plan_add_edit_reorder_move_read_and_one_version_advance_per_command(client):
    project = create_project(client)["project"]
    added, ids = add_plan_items(client, project)
    assert added["project_version"] == 2
    assert added["plan_version"] == 2
    assert [item["version"] for item in added["items"]] == [1, 1]

    edited = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": 2,
            "expected_plan_version": 2,
            "operations": [
                {
                    "action": "edit",
                    "plan_item_id": ids[0],
                    "expected_version": 1,
                    "label": "Edited item",
                    "intended_outcome": "Edited observable outcome",
                    "status": "ready",
                },
                {
                    "action": "move",
                    "plan_item_id": ids[1],
                    "expected_version": 1,
                    "scope_band": "later",
                    "order_key": 5,
                },
            ],
        },
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["project_version"] == 3
    assert body["plan_version"] == 3
    by_id = {item["id"]: item for item in body["items"]}
    assert by_id[ids[0]]["label"] == "Edited item"
    assert by_id[ids[1]]["scope_band"] == "later"

    reordered = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": 3,
            "expected_plan_version": 3,
            "operations": [
                {
                    "action": "reorder",
                    "plan_item_id": ids[0],
                    "expected_version": 2,
                    "order_key": 30,
                }
            ],
        },
    )
    assert reordered.status_code == 200
    refreshed = client.get(
        f"/v2/projects/{project['project_id']}/plan",
        headers=auth_headers(),
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["plan_version"] == 4
    assert {item["id"]: item["order_key"] for item in refreshed.json()["items"]}[ids[0]] == 30


def test_plan_stale_write_fails_and_latest_command_retry_is_safe(client):
    project = create_project(client)["project"]
    command_id = str(uuid.uuid4())
    added, _ = add_plan_items(client, project, count=1, command_id=command_id)
    replay, _ = add_plan_items(client, project, count=1, command_id=command_id)
    # A latest-command retry is a safe no-op and returns canonical current state,
    # even if an untrusted client accidentally resends a different payload.
    assert replay["replayed"] is True
    assert replay["plan_version"] == added["plan_version"] == 2
    assert replay["items"] == added["items"]

    stale = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": 1,
            "expected_plan_version": 1,
            "operations": [
                {
                    "action": "add",
                    "plan_item_id": str(uuid.uuid4()),
                    "label": "Stale",
                    "intended_outcome": "Must not be written",
                    "scope_band": "first_version",
                    "status": "ready",
                    "order_key": 50,
                }
            ],
        },
    )
    assert stale.status_code == 409
    assert "reload" in stale.json()["error"]["message"].lower()
    assert added["plan_version"] == 2


def test_linked_plan_item_removal_requires_detach_or_cancel(client):
    project = create_project(client)["project"]
    plan, ids = add_plan_items(client, project, count=1)
    change = start_change(
        client,
        project["project_id"],
        plan["project_version"],
        plan_item_id=ids[0],
    )
    assert change.status_code == 200

    base = {
        "workflow_version": "v2",
        "expected_project_version": plan["project_version"],
        "expected_plan_version": plan["plan_version"],
        "operations": [
            {
                "action": "remove",
                "plan_item_id": ids[0],
                "expected_version": 1,
            }
        ],
    }
    denied = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json={**base, "command_id": str(uuid.uuid4())},
    )
    assert denied.status_code == 409

    detached = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json={
            **base,
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": 1,
            "linked_item_action": "detach",
        },
    )
    assert detached.status_code == 200, detached.text
    current = client.get(
        f"/v2/projects/{project['project_id']}/current-change",
        headers=auth_headers(),
    ).json()["current_change"]
    assert current["plan_item_id"] is None
    assert current["goal_snapshot"] == "Add player totals"
    assert current["version"] == 2


def test_linked_plan_item_cancel_is_atomic_with_removal(client):
    project = create_project(client)["project"]
    plan, ids = add_plan_items(client, project, count=1)
    change = start_change(
        client,
        project["project_id"],
        plan["project_version"],
        plan_item_id=ids[0],
    ).json()["current_change"]
    removed = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": plan["project_version"],
            "expected_plan_version": plan["plan_version"],
            "expected_current_change_version": change["version"],
            "linked_item_action": "cancel",
            "cancellation_command_id": str(uuid.uuid4()),
            "cancellation_reason_key": "plan_item_removed",
            "operations": [
                {
                    "action": "remove",
                    "plan_item_id": ids[0],
                    "expected_version": 1,
                }
            ],
        },
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["items"] == []
    assert client.get(
        f"/v2/projects/{project['project_id']}/current-change",
        headers=auth_headers(),
    ).json()["current_change"] is None


@pytest.mark.parametrize("linked_action", ["detach", "cancel"])
def test_fake_plan_mutation_rolls_back_linked_change_when_later_operation_fails(
    client, linked_action
):
    project = create_project(client)["project"]
    plan, ids = add_plan_items(client, project, count=1)
    change = start_change(
        client,
        project["project_id"],
        plan["project_version"],
        plan_item_id=ids[0],
    ).json()["current_change"]
    payload = {
        "workflow_version": "v2",
        "command_id": str(uuid.uuid4()),
        "expected_project_version": plan["project_version"],
        "expected_plan_version": plan["plan_version"],
        "expected_current_change_version": change["version"],
        "linked_item_action": linked_action,
        "operations": [
            {"action": "remove", "plan_item_id": ids[0], "expected_version": 1},
            {
                "action": "edit",
                "plan_item_id": str(uuid.uuid4()),
                "expected_version": 1,
                "label": "Missing",
                "intended_outcome": "Force the later operation to fail",
                "status": "ready",
            },
        ],
    }
    if linked_action == "cancel":
        payload.update(
            cancellation_command_id=str(uuid.uuid4()),
            cancellation_reason_key="plan_item_removed",
        )
    response = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json=payload,
    )
    assert response.status_code == 404

    current = client.get(
        f"/v2/projects/{project['project_id']}/current-change",
        headers=auth_headers(),
    ).json()["current_change"]
    current_plan = client.get(
        f"/v2/projects/{project['project_id']}/plan",
        headers=auth_headers(),
    ).json()
    assert current["lifecycle_state"] == "preparing"
    assert current["plan_item_id"] == ids[0]
    assert current["version"] == change["version"]
    assert [item["id"] for item in current_plan["items"]] == ids
    assert current_plan["plan_version"] == plan["plan_version"]


def test_current_change_start_resume_singleton_goal_snapshot_and_retry(client):
    project = create_project(client)["project"]
    command_id = str(uuid.uuid4())
    started = start_change(
        client,
        project["project_id"],
        project["version"],
        command_id=command_id,
        goal="Immutable goal",
    )
    assert started.status_code == 200
    first = started.json()["current_change"]
    assert first["lifecycle_state"] == "preparing"
    assert first["resume_step"] == "confirm_change"
    assert first["resume"] == {
        "lifecycle_state": "preparing",
        "resume_step": "confirm_change",
        "available_commands": ["cancel"],
    }

    replay = start_change(
        client,
        project["project_id"],
        project["version"],
        command_id=command_id,
        goal="Immutable goal",
    )
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["current_change"]["id"] == first["id"]

    competing = start_change(
        client,
        project["project_id"],
        project["version"],
        goal="Another goal",
    )
    assert competing.status_code == 409
    resumed = client.get(
        f"/v2/projects/{project['project_id']}/current-change",
        headers=auth_headers(),
    ).json()["current_change"]
    assert resumed["id"] == first["id"]
    assert resumed["goal_snapshot"] == "Immutable goal"
    assert "owner_user_id" not in resumed
    assert "teaching_policy_version" not in resumed
    assert "create_command_id" not in resumed


def test_current_change_stale_cancel_cross_owner_and_retry_behavior(client):
    project = create_project(client)["project"]
    change = start_change(
        client,
        project["project_id"],
        project["version"],
    ).json()["current_change"]
    path = f"/v2/projects/{project['project_id']}/current-change/{change['id']}/cancel"
    command_id = str(uuid.uuid4())
    stale = client.post(
        path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": command_id,
            "expected_current_change_version": 99,
            "reason": "student_cancelled",
        },
    )
    assert stale.status_code == 409
    cross_owner = client.post(
        path,
        headers=auth_headers(USER_B),
        json={
            "workflow_version": "v2",
            "command_id": command_id,
            "expected_current_change_version": 1,
            "reason": "student_cancelled",
        },
    )
    assert cross_owner.status_code == 404

    body = {
        "workflow_version": "v2",
        "command_id": command_id,
        "expected_current_change_version": 1,
        "reason": "student_cancelled",
    }
    cancelled = client.post(path, headers=auth_headers(), json=body)
    assert cancelled.status_code == 200
    result = cancelled.json()["current_change"]
    assert result["lifecycle_state"] == "cancelled"
    assert result["resume_step"] is None
    assert result["goal_snapshot"] == change["goal_snapshot"]
    assert result["version"] == 2
    assert result["resume"]["available_commands"] == []

    replay = client.post(path, headers=auth_headers(), json=body)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["current_change"]["version"] == 2


def test_temporary_project_starts_one_recovery_change_and_cross_owner_reads_fail(client):
    project = create_project(client, intent="recovery_first")["project"]
    invalid = start_change(
        client,
        project["project_id"],
        project["version"],
        kind="build",
    )
    assert invalid.status_code == 409
    recovery = client.get(
        f"/v2/projects/{project['project_id']}/current-change",
        headers=auth_headers(),
    )
    assert recovery.status_code == 200
    assert recovery.json()["current_change"]["change_kind"] == "recovery"
    assert client.get(
        f"/v2/projects/{project['project_id']}/current-change",
        headers=auth_headers(USER_B),
    ).status_code == 404


def test_v2_responses_never_include_server_secrets_or_internal_policy(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "private-v2-service-key")
    project = create_project(client)["project"]
    started = start_change(
        client,
        project["project_id"],
        project["version"],
    )
    for response_text in (
        client.get(
            f"/v2/projects/{project['project_id']}", headers=auth_headers()
        ).text,
        started.text,
    ):
        assert "private-v2-service-key" not in response_text
        assert "policy_not_evaluated" not in response_text
        assert "unresolved-v0" not in response_text
        assert "owner_user_id" not in response_text
@pytest.mark.parametrize("choice", ["codex", "claude_code", "cursor", "chatgpt", "replit", "other"])
def test_v23b_selects_each_supported_real_agent(client, choice):
    project, change = prepare_v23b_change(client)
    result = select_agent(client, project, change, choice)
    assert result["selected_agent"]["key"] == choice
    assert result["guidance_required"] is False
    assert result["selected_agent"]["mapping_available"] is False


def test_v23b_help_me_choose_does_not_persist_or_default_an_agent(client):
    project, change = prepare_v23b_change(client)
    result = select_agent(client, project, change, "help_me_choose")
    assert result["selected_agent"] is None
    assert result["guidance_required"] is True
    state = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers(),
    ).json()
    assert state["build_stage"] == "choose_agent"
    assert state["selected_agent"] is None


def test_v23b_agent_rejects_invalid_stale_cross_owner_and_unresolved(client):
    project, change = prepare_v23b_change(client)
    path = f"/v2/projects/{project['project_id']}/current-change/{change['id']}/coding-agent"
    body = {
        "workflow_version": "v2",
        "expected_project_version": project["version"],
        "expected_current_change_version": change["version"],
        "choice": "not-a-real-agent",
    }
    assert client.put(path, headers=auth_headers(), json=body).status_code == 422
    body["choice"] = "codex"
    assert client.put(path, headers=auth_headers(USER_B), json=body).status_code == 404
    body["expected_current_change_version"] -= 1
    assert client.put(path, headers=auth_headers(), json=body).status_code == 409

    unresolved_project = create_project(client, name="Unresolved")["project"]
    unresolved = start_change(
        client, unresolved_project["project_id"], unresolved_project["version"]
    ).json()["current_change"]
    body.update(
        expected_project_version=unresolved_project["version"],
        expected_current_change_version=unresolved["version"],
    )
    unresolved_path = (
        f"/v2/projects/{unresolved_project['project_id']}"
        f"/current-change/{unresolved['id']}/coding-agent"
    )
    assert client.put(unresolved_path, headers=auth_headers(), json=body).status_code == 409


def test_v23b_prompt_draft_create_edit_resume_and_bounds(client):
    project, change = prepare_v23b_change(client)
    select_agent(client, project, change)
    first = save_prompt(client, project, change, "  Student's first wording\n")
    assert first["prompt_draft"] == "  Student's first wording\n"
    assert first["prompt_draft_version"] == 2
    assert client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-versions",
        headers=auth_headers(),
    ).json()["prompt_versions"] == []

    second = save_prompt(client, project, change, "Student's revised wording")
    assert second["prompt_draft"] == "Student's revised wording"
    assert second["prompt_draft_version"] == 3
    resume = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers(),
    ).json()
    assert resume["prompt_draft"] == "Student's revised wording"
    assert resume["structured_decisions"]["boundaries"] == ["Keep existing scoring behavior"]
    assert resume["build_stage"] == "choose_effort"
    assert resume["effort_category"] is None

    stale = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-draft",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"] - 1,
            "expected_prompt_draft_version": change["prompt_draft_version"],
            "prompt_text": "stale edit",
        },
    )
    assert stale.status_code == 409
    too_long = stale.request.content
    assert client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-draft",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change["prompt_draft_version"],
            "prompt_text": "x" * 65537,
        },
    ).status_code == 422
    assert too_long is not None


@pytest.mark.parametrize("effort", ["quick", "standard", "deep"])
def test_v23b_effort_is_explicit_valid_and_versioned(client, effort):
    project, change = prepare_v23b_change(client)
    select_agent(client, project, change)
    save_prompt(client, project, change)
    path = f"/v2/projects/{project['project_id']}/current-change/{change['id']}/effort"
    response = client.put(
        path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "effort": effort,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["effort_category"] == effort
    assert client.put(
        path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"] - 1,
            "effort": effort,
        },
    ).status_code == 409
    assert client.put(
        path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": response.json()["version"],
            "effort": "maximum",
        },
    ).status_code == 422


def test_v23b_acceptance_handoff_resume_and_idempotency(client):
    project, change = prepare_v23b_change(client)
    select_agent(client, project, change, "other")
    editing = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers(),
    ).json()
    assert editing["build_stage"] == "edit_prompt"
    save_prompt(client, project, change, "Use exactly this student-edited prompt")
    effort = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/effort",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "effort": "standard",
        },
    ).json()
    change.update(effort)
    reviewing = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers(),
    ).json()
    assert reviewing["build_stage"] == "review_prompt"
    accept_command = str(uuid.uuid4())
    acceptance_body = {
        "workflow_version": "v2",
        "command_id": accept_command,
        "expected_current_change_version": change["version"],
        "expected_prompt_draft_version": change["prompt_draft_version"],
    }
    prompt_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/prompt-versions"
    )
    stale_acceptance = dict(acceptance_body)
    stale_acceptance["expected_current_change_version"] -= 1
    assert client.post(
        prompt_path, headers=auth_headers(), json=stale_acceptance
    ).status_code == 409
    accepted = client.post(prompt_path, headers=auth_headers(), json=acceptance_body)
    assert accepted.status_code == 200, accepted.text
    accepted_json = accepted.json()
    prompt = accepted_json["prompt_version"]
    assert prompt["content"] == "Use exactly this student-edited prompt"
    assert prompt["coding_agent_key"] == "other"
    assert prompt["effort_category"] == "standard"
    assert accepted_json["current_change"]["lifecycle_state"] == "preparing"

    retried = client.post(prompt_path, headers=auth_headers(), json=acceptance_body)
    assert retried.status_code == 200
    assert retried.json()["replayed"] is True
    listed = client.get(prompt_path, headers=auth_headers()).json()["prompt_versions"]
    assert len(listed) == 1

    ready = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers(),
    ).json()
    assert ready["build_stage"] == "ready_to_handoff"
    assert ready["ready_to_handoff"] is True

    handoff_command = str(uuid.uuid4())
    handoff_body = {
        "workflow_version": "v2",
        "command_id": handoff_command,
        "prompt_version_id": prompt["id"],
        "expected_current_change_version": accepted_json["current_change"]["version"],
        "expected_prompt_version": prompt["version"],
    }
    handoff_path = f"/v2/projects/{project['project_id']}/current-change/{change['id']}/handoff"
    stale_handoff = dict(handoff_body)
    stale_handoff["expected_prompt_version"] += 1
    assert client.post(
        handoff_path, headers=auth_headers(), json=stale_handoff
    ).status_code == 409
    handed = client.post(handoff_path, headers=auth_headers(), json=handoff_body)
    assert handed.status_code == 200, handed.text
    assert handed.json()["exact_prompt"] == prompt["content"]
    assert handed.json()["current_change"]["lifecycle_state"] == "awaiting_agent"
    assert handed.json()["current_change"]["resume_step"] == "return_outcome"
    retry = client.post(handoff_path, headers=auth_headers(), json=handoff_body)
    assert retry.status_code == 200
    assert retry.json()["replayed"] is True
    wrong_command = dict(handoff_body)
    wrong_command["command_id"] = str(uuid.uuid4())
    wrong_command["expected_current_change_version"] = handed.json()["current_change"]["version"]
    wrong_command["expected_prompt_version"] = handed.json()["prompt_version"]["version"]
    assert client.post(
        handoff_path, headers=auth_headers(), json=wrong_command
    ).status_code == 409
    waiting = client.get(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/build-state",
        headers=auth_headers(),
    ).json()
    assert waiting["build_stage"] == "waiting_for_return"
    assert waiting["exact_handoff_prompt"] == prompt["content"]
    assert client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/coding-agent",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_project_version": project["version"],
            "expected_current_change_version": waiting["current_change_version"],
            "choice": "codex",
        },
    ).status_code == 409


def test_v23b_plan_detach_preserves_prompt_freshness_and_handoff(client):
    project = create_project(client)["project"]
    plan, item_ids = add_plan_items(client, project, count=1)
    project["version"] = plan["project_version"]
    project["plan_version"] = plan["plan_version"]
    started = start_change(
        client,
        project["project_id"],
        project["version"],
        plan_item_id=item_ids[0],
    )
    assert started.status_code == 200, started.text
    change = started.json()["current_change"]
    resolved = client.app.state.test_v2_repo.resolve_policy_for_test(
        USER_A, uuid.UUID(project["project_id"]), uuid.UUID(change["id"])
    )
    change["version"] = resolved.version
    change["resume_step"] = resolved.resume_step.value
    accepted = accept_ready_v23b_prompt(client, project, change)

    detached = client.post(
        f"/v2/projects/{project['project_id']}/plan/mutations",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_project_version": project["version"],
            "expected_plan_version": project["plan_version"],
            "expected_current_change_version": change["version"],
            "linked_item_action": "detach",
            "operations": [
                {
                    "action": "remove",
                    "plan_item_id": item_ids[0],
                    "expected_version": 1,
                }
            ],
        },
    )
    assert detached.status_code == 200, detached.text

    resume_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/build-state"
    )
    resume = client.get(resume_path, headers=auth_headers())
    assert resume.status_code == 200, resume.text
    state = resume.json()
    assert state["build_stage"] == "ready_to_handoff"
    assert state["ready_to_handoff"] is True
    assert state["current_change_version"] == change["version"] + 1

    prompt = accepted["prompt_version"]
    handed = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/handoff",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "prompt_version_id": prompt["id"],
            "expected_current_change_version": state["current_change_version"],
            "expected_prompt_version": prompt["version"],
        },
    )
    assert handed.status_code == 200, handed.text
    assert handed.json()["current_change"]["lifecycle_state"] == "awaiting_agent"


@pytest.mark.parametrize("mutation", ["draft", "agent", "effort"])
def test_v23b_mutable_prompt_inputs_invalidate_old_acceptance(client, mutation):
    project, change = prepare_v23b_change(client)
    accepted = accept_ready_v23b_prompt(client, project, change)
    prompt = accepted["prompt_version"]

    if mutation == "draft":
        save_prompt(client, project, change, "A newly edited prompt")
    elif mutation == "agent":
        select_agent(client, project, change, "cursor")
    else:
        response = client.put(
            f"/v2/projects/{project['project_id']}/current-change/{change['id']}/effort",
            headers=auth_headers(),
            json={
                "workflow_version": "v2",
                "expected_current_change_version": change["version"],
                "effort": "deep",
            },
        )
        assert response.status_code == 200, response.text
        change.update(response.json())

    resume_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/build-state"
    )
    resume = client.get(resume_path, headers=auth_headers())
    assert resume.status_code == 200, resume.text
    state = resume.json()
    assert state["build_stage"] == "review_prompt"
    assert state["ready_to_handoff"] is False

    stale_handoff = client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/handoff",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "prompt_version_id": prompt["id"],
            "expected_current_change_version": state["current_change_version"],
            "expected_prompt_version": prompt["version"],
        },
    )
    assert stale_handoff.status_code == 409


@pytest.mark.parametrize(
    ("new_done_condition", "new_boundaries"),
    [
        ("A newly edited done condition", ["Keep existing scoring behavior"]),
        ("Totals are correct", ["A newly edited boundary"]),
    ],
    ids=["done-condition-only", "boundaries-only"],
)
def test_v23b_structured_prompt_edits_invalidate_acceptance_until_reaccepted(
    client,
    new_done_condition,
    new_boundaries,
):
    project, change = prepare_v23b_change(client)
    select_agent(client, project, change)
    save_prompt(client, project, change, "Keep this exact prompt text")
    effort = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/effort",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "effort": "standard",
        },
    )
    assert effort.status_code == 200, effort.text
    change.update(effort.json())

    prompt_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/prompt-versions"
    )
    accepted = client.post(
        prompt_path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change["prompt_draft_version"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    first = accepted.json()

    edited = client.put(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/prompt-draft",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "expected_current_change_version": first["current_change"]["version"],
            "expected_prompt_draft_version": first["current_change"]["prompt_draft_version"],
            "prompt_text": "Keep this exact prompt text",
            "done_condition": new_done_condition,
            "boundaries": new_boundaries,
        },
    )
    assert edited.status_code == 200, edited.text
    edited_change = edited.json()

    resume_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/build-state"
    )
    stale_resume = client.get(resume_path, headers=auth_headers())
    assert stale_resume.status_code == 200, stale_resume.text
    assert stale_resume.json()["build_stage"] == "review_prompt"
    assert stale_resume.json()["ready_to_handoff"] is False

    handoff_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/handoff"
    )
    stale_handoff = client.post(
        handoff_path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "prompt_version_id": first["prompt_version"]["id"],
            "expected_current_change_version": edited_change["version"],
            "expected_prompt_version": first["prompt_version"]["version"],
        },
    )
    assert stale_handoff.status_code == 409

    reaccepted = client.post(
        prompt_path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": edited_change["version"],
            "expected_prompt_draft_version": edited_change["prompt_draft_version"],
        },
    )
    assert reaccepted.status_code == 200, reaccepted.text
    second = reaccepted.json()
    assert second["prompt_version"]["ordinal"] == 2
    assert second["prompt_version"]["id"] != first["prompt_version"]["id"]
    ready = client.get(resume_path, headers=auth_headers()).json()
    assert ready["build_stage"] == "ready_to_handoff"
    assert ready["ready_to_handoff"] is True

    handed = client.post(
        handoff_path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "prompt_version_id": second["prompt_version"]["id"],
            "expected_current_change_version": second["current_change"]["version"],
            "expected_prompt_version": second["prompt_version"]["version"],
        },
    )
    assert handed.status_code == 200, handed.text
    assert handed.json()["current_change"]["lifecycle_state"] == "awaiting_agent"


def test_v23b_unresolved_policy_and_missing_handoff_prerequisites_fail_closed(client):
    project = create_project(client)["project"]
    change = start_change(
        client, project["project_id"], project["version"]
    ).json()["current_change"]
    prompt_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/prompt-versions"
    )
    assert client.post(
        prompt_path,
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change["prompt_draft_version"],
        },
    ).status_code == 409
    assert client.post(
        f"/v2/projects/{project['project_id']}/current-change/{change['id']}/handoff",
        headers=auth_headers(),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "prompt_version_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_prompt_version": 1,
        },
    ).status_code == 409


def test_v23b_resolved_acceptance_requires_agent_prompt_and_effort(client):
    project, change = prepare_v23b_change(client)
    prompt_path = (
        f"/v2/projects/{project['project_id']}"
        f"/current-change/{change['id']}/prompt-versions"
    )

    def accept() -> int:
        return client.post(
            prompt_path,
            headers=auth_headers(),
            json={
                "workflow_version": "v2",
                "command_id": str(uuid.uuid4()),
                "expected_current_change_version": change["version"],
                "expected_prompt_draft_version": change.get("prompt_draft_version", 1),
            },
        ).status_code

    assert accept() == 409
    select_agent(client, project, change)
    assert accept() == 409
    save_prompt(client, project, change)
    assert accept() == 409


def test_v23b_cross_owner_cannot_probe_any_build_resource(client):
    project, change = prepare_v23b_change(client)
    select_agent(client, project, change)
    save_prompt(client, project, change)
    root = f"/v2/projects/{project['project_id']}/current-change/{change['id']}"
    headers = auth_headers(USER_B)
    assert client.get(f"{root}/build-state", headers=headers).status_code == 404
    assert client.get(f"{root}/prompt-versions", headers=headers).status_code == 404
    assert client.put(
        f"{root}/effort",
        headers=headers,
        json={
            "workflow_version": "v2",
            "expected_current_change_version": change["version"],
            "effort": "quick",
        },
    ).status_code == 404
    assert client.post(
        f"{root}/prompt-versions",
        headers=headers,
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_prompt_draft_version": change["prompt_draft_version"],
        },
    ).status_code == 404
    assert client.post(
        f"{root}/handoff",
        headers=headers,
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "prompt_version_id": str(uuid.uuid4()),
            "expected_current_change_version": change["version"],
            "expected_prompt_version": 1,
        },
    ).status_code == 404


def test_v23b_build_routes_require_verified_authentication_and_explicit_ids(client):
    project_id = str(uuid.uuid4())
    change_id = str(uuid.uuid4())
    response = client.get(
        f"/v2/projects/{project_id}/current-change/{change_id}/build-state"
    )
    assert response.status_code == 401
    malformed = client.get(
        "/v2/projects/current-change/build-state", headers=auth_headers()
    )
    assert malformed.status_code in {
        404,
        422,
    }
