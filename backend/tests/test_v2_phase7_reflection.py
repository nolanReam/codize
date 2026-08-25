"""Focused Phase 7 Learning and derived History read-model tests."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import security
from app.domain.v2 import (
    CheckResult,
    CodingAgentKey,
    CurrentChangeKind,
    CurrentChangeState,
    EffortCategory,
    PromptPurpose,
    RecoveryStatus,
    ResumeStep,
    SupportLevel,
    V2Check,
    V2CurrentChange,
    V2PromptVersion,
    V2RecoveryCase,
)
from app.main import create_app
from app.services.project_repository import get_project_repository
from app.services.v2_repository import get_v2_repository
from tests.fakes import InMemoryProjectRepository, InMemoryV2Repository


USER_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
_key = ec.generate_private_key(ec.SECP256R1())


def auth_headers(user_id: str = USER_A) -> dict[str, str]:
    token = pyjwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600},
        _key,
        algorithm="ES256",
    )
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
    repo = InMemoryV2Repository()
    app.dependency_overrides[get_v2_repository] = lambda: repo
    app.dependency_overrides[get_project_repository] = lambda: InMemoryProjectRepository()
    app.state.test_v2_repo = repo
    return TestClient(app)


def create_project(client: TestClient, user_id: str = USER_A) -> tuple[dict, InMemoryV2Repository]:
    response = client.post(
        "/v2/projects",
        headers=auth_headers(user_id),
        json={
            "workflow_version": "v2",
            "command_id": str(uuid.uuid4()),
            "display_name": "Volleyball Tracker",
            "creation_intent": "new_idea",
        },
    )
    assert response.status_code == 200
    project = response.json()["project"]
    repo = client.app.state.test_v2_repo
    repo.activate_project_for_test(user_id, uuid.UUID(project["project_id"]))
    return project, repo


def seed_change(
    repo: InMemoryV2Repository,
    project_id: uuid.UUID,
    *,
    goal: str,
    state: CurrentChangeState,
    started_at: datetime,
    owner: str = USER_A,
) -> V2CurrentChange:
    project = repo._projects[project_id][1]
    terminal_at = started_at + timedelta(minutes=20)
    cancelled = state is CurrentChangeState.CANCELLED
    completed = state is CurrentChangeState.COMPLETED
    change = V2CurrentChange(
        id=uuid.uuid4(), project_ref=project.ref, plan_item_id=None,
        change_kind=CurrentChangeKind.BUILD, lifecycle_state=state,
        resume_step=(None if completed or cancelled else
                     ResumeStep.RECOVERY_RECHECK if state is CurrentChangeState.RECOVERING
                     else ResumeStep.PROMPT),
        goal_snapshot=goal, done_condition_snapshot=f"{goal} is visible",
        boundary_snapshots=(), version=3, created_at=started_at,
        updated_at=terminal_at,
        completed_at=terminal_at if completed else None,
        cancelled_at=terminal_at if cancelled else None,
        cancellation_command_id=uuid.uuid4() if cancelled else None,
        cancellation_reason_key="student_cancelled" if cancelled else None,
        coding_agent_key=CodingAgentKey.CODEX, effort_category=EffortCategory.STANDARD,
    )
    repo._changes[change.id] = (owner, change)
    return change


def seed_recovery(
    repo: InMemoryV2Repository,
    project_id: uuid.UUID,
    change: V2CurrentChange,
    *,
    status: RecoveryStatus,
    opened_at: datetime,
    observed_symptom: str = "The stored result did not match the intended behavior.",
    investigation_finding: str | None = None,
    correction_summary: str | None = None,
    resolution_summary: str | None = None,
) -> V2RecoveryCase:
    recovery = V2RecoveryCase(
        id=uuid.uuid4(), project_id=project_id, current_change_id=change.id,
        status=status, intended_behavior=change.done_condition_snapshot or change.goal_snapshot,
        observed_symptom=observed_symptom,
        last_known_working_statement=None, last_known_working_certainty="unsure",
        candidate_change_summary=change.goal_snapshot, student_hypothesis=None,
        proposed_first_check=None, investigation_finding=investigation_finding,
        cause_summary=None, correction_summary=correction_summary,
        resolution_summary=(resolution_summary or "The student recheck passed.")
        if status is RecoveryStatus.RESOLVED else resolution_summary,
        opened_at=opened_at,
        resolved_at=(opened_at + timedelta(minutes=10))
        if status in {RecoveryStatus.RESOLVED, RecoveryStatus.ABANDONED} else None,
        version=2,
    )
    repo._recovery_cases[recovery.id] = (USER_A, recovery)
    return recovery


def seed_check(
    repo: InMemoryV2Repository,
    project_id: uuid.UUID,
    change: V2CurrentChange,
    *,
    created_at: datetime,
    status: str,
    result: CheckResult | None = None,
    observation: str | None = None,
    performed_at: datetime | None = None,
    not_run_at: datetime | None = None,
    supersedes: V2Check | None = None,
    plan: str = "Submit an invalid login",
) -> V2Check:
    check = V2Check(
        id=uuid.uuid4(), project_id=project_id, current_change_id=change.id,
        check_plan=plan, plan_source="student", status=status, result=result,
        student_observation=observation, performed_at=performed_at,
        not_run_at=not_run_at,
        supersedes_check_id=supersedes.id if supersedes else None,
        created_at=created_at, version=2 if status != "proposed" else 1,
    )
    repo._checks[check.id] = (USER_A, check)
    return check


def test_learning_empty_is_truthful_read_only_and_cross_owner_is_denied(client):
    project, repo = create_project(client)
    project_id = project["project_id"]
    before = (dict(repo._projects), dict(repo._learner_evidence), dict(repo._changes))

    response = client.get(f"/v2/projects/{project_id}/learning", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["competencies"] == []
    assert "mastery" not in response.text.lower()
    assert before == (dict(repo._projects), dict(repo._learner_evidence), dict(repo._changes))

    denied = client.get(f"/v2/projects/{project_id}/learning", headers=auth_headers(USER_B))
    assert denied.status_code == 404


def test_learning_projects_canonical_statuses_recent_evidence_and_returned_support(client):
    project, repo = create_project(client)
    project_id = project["project_id"]
    now = datetime.now(UTC)
    context_change = seed_change(
        repo, uuid.UUID(project_id), goal="Add player totals",
        state=CurrentChangeState.REVIEWING, started_at=now - timedelta(days=3),
    )
    # One assisted example -> Guided.
    repo.seed_learner_evidence(
        USER_A, "debugging", elicitation="after_hint", support_level=SupportLevel.CLUE,
        current_change_id=context_change.id, observed_at=now - timedelta(days=2),
    )
    # One unsupported example -> Practiced.
    repo.seed_learner_evidence(
        USER_A, "testing", elicitation="asked", support_level=SupportLevel.NONE,
        current_change_id=uuid.uuid4(), observed_at=now - timedelta(days=2),
    )
    # Two independent, distinct recent changes -> Recently independent.
    for days in (12, 1):
        repo.seed_learner_evidence(
            USER_A, "define_done", elicitation="spontaneous",
            support_level=SupportLevel.NONE, current_change_id=uuid.uuid4(),
            observed_at=now - timedelta(days=days),
        )
    # A previously independent competency gets support again -> Guided, without loss language.
    for days in (14, 3):
        repo.seed_learner_evidence(
            USER_A, "effort_selection", elicitation="asked",
            support_level=SupportLevel.NONE, current_change_id=uuid.uuid4(),
            observed_at=now - timedelta(days=days),
        )
    repo.seed_learner_evidence(
        USER_A, "effort_selection", elicitation="taught", support_level=SupportLevel.TEACH,
        current_change_id=uuid.uuid4(), observed_at=now,
    )
    # Bound the response even when more evidence exists.
    for index in range(4):
        repo.seed_learner_evidence(
            USER_A, "protect_working_behavior", elicitation="asked",
            current_change_id=uuid.uuid4(), observed_at=now - timedelta(hours=index),
        )

    response = client.get(f"/v2/projects/{project_id}/learning", headers=auth_headers())
    assert response.status_code == 200, response.text
    by_key = {item["key"]: item for item in response.json()["competencies"]}
    assert by_key["debugging"]["status"] == "guided"
    assert by_key["testing"]["status"] == "practiced"
    assert by_key["define_done"]["status"] == "recently_independent"
    assert by_key["effort_selection"]["status"] == "guided"
    assert by_key["effort_selection"]["support_direction"] == "more"
    assert len(by_key["protect_working_behavior"]["recent_evidence"]) == 3
    context = by_key["debugging"]["recent_evidence"][0]
    assert context["project_name"] == "Volleyball Tracker"
    assert context["current_change_goal"] == "Add player totals"
    assert "id" not in context
    assert "project_id" not in context
    assert "current_change_id" not in context
    assert "lost" not in response.text.lower()
    assert "percent" not in response.text.lower()


def test_history_groups_prompts_checks_and_recovery_without_upgrading_agent_claims(client):
    project, repo = create_project(client)
    project_id = uuid.UUID(project["project_id"])
    started = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    change = seed_change(
        repo, project_id, goal="Add login validation",
        state=CurrentChangeState.COMPLETED, started_at=started,
    )
    prompt = V2PromptVersion(
        id=uuid.uuid4(), project_ref=change.project_ref, current_change_id=change.id,
        ordinal=1, purpose=PromptPurpose.FEATURE,
        content="Add focused login validation.",
        content_sha256=hashlib.sha256(b"Add focused login validation.").hexdigest(),
        input_current_change_version=1, input_goal_snapshot=change.goal_snapshot,
        input_done_condition_snapshot=change.done_condition_snapshot,
        input_boundary_snapshots=(), generation_attempt_id=None,
        coding_agent_key=CodingAgentKey.CODEX, effort_category=EffortCategory.STANDARD,
        provider_mapping_key=None, provider_mapping_version=None,
        accepted_at=started + timedelta(minutes=2),
        handed_off_at=started + timedelta(minutes=3), version=2,
    )
    repo._prompt_versions[prompt.id] = (USER_A, prompt)
    failed = seed_check(
        repo, project_id, change, created_at=started + timedelta(minutes=5),
        status="performed", result=CheckResult.DID_NOT_WORK,
        observation="Unauthorized still appears", performed_at=started + timedelta(minutes=6),
    )
    unsure = seed_check(
        repo, project_id, change, created_at=started + timedelta(minutes=8),
        status="performed", result=CheckResult.UNSURE,
        observation="The error changed but I could not tell",
        performed_at=started + timedelta(minutes=9), supersedes=failed,
    )
    seed_check(
        repo, project_id, change, created_at=started + timedelta(minutes=10),
        status="performed", result=CheckResult.WORKED,
        observation="Invalid login now shows the expected error",
        performed_at=started + timedelta(minutes=18), supersedes=unsure,
    )
    seed_recovery(
        repo, project_id, change, status=RecoveryStatus.ABANDONED,
        opened_at=started + timedelta(minutes=7),
        observed_symptom="The first investigation was stopped.",
    )
    seed_recovery(
        repo, project_id, change, status=RecoveryStatus.RESOLVED,
        opened_at=started + timedelta(minutes=11),
        observed_symptom="Unauthorized still appears",
        investigation_finding="A missing header may be involved",
        correction_summary="Add only the missing header handling",
        resolution_summary="The student recheck passed",
    )

    before = (dict(repo._changes), dict(repo._checks), dict(repo._prompt_versions), dict(repo._recovery_cases))
    response = client.get(f"/v2/projects/{project_id}/history", headers=auth_headers())
    assert response.status_code == 200, response.text
    assert response.json()["project_name"] == "Volleyball Tracker"
    assert response.json()["project_created_at"]
    item = response.json()["changes"][0]
    assert item["status"] == "completed_after_recovery"
    assert [check["result"] for check in item["checks"]] == [
        "did_not_work", "unsure", "worked"
    ]
    assert [check["sequence"] for check in item["checks"]] == [1, 2, 3]
    assert [check["relationship"] for check in item["checks"]] == [
        "initial", "follow_up", "retry_after_unsure"
    ]
    assert [check["supersedes_sequence"] for check in item["checks"]] == [None, 1, 2]
    assert all("created_at" in check for check in item["checks"])
    assert all("id" not in check for check in item["checks"])
    assert "supersedes_check_id" not in response.text
    assert item["prompts"][0]["content"] == "Add focused login validation."
    assert [episode["episode_number"] for episode in item["recoveries"]] == [1, 2]
    assert item["recoveries"][0]["recheck_state"] is None
    assert item["recoveries"][1]["recheck_state"] == "completed"
    assert item["recoveries"][1]["investigation_finding_provenance"] == "agent_claimed"
    assert "root cause" not in response.text.lower()
    assert response.json()["transfer_question"] is not None
    assert before == (dict(repo._changes), dict(repo._checks), dict(repo._prompt_versions), dict(repo._recovery_cases))


def test_history_active_cancelled_pagination_and_security_are_truthful(client):
    project, repo = create_project(client)
    project_id = uuid.UUID(project["project_id"])
    base = datetime(2026, 8, 20, tzinfo=UTC)
    seed_change(repo, project_id, goal="Old completed", state=CurrentChangeState.COMPLETED, started_at=base)
    seed_change(repo, project_id, goal="Cancelled change", state=CurrentChangeState.CANCELLED, started_at=base + timedelta(days=1))
    resumed = seed_change(
        repo, project_id, goal="Current work", state=CurrentChangeState.REVIEWING,
        started_at=base + timedelta(days=2),
    )
    seed_recovery(
        repo, project_id, resumed, status=RecoveryStatus.RESOLVED,
        opened_at=base + timedelta(days=2, minutes=5),
    )
    recovering = seed_change(
        repo, project_id, goal="Fix saved players", state=CurrentChangeState.RECOVERING,
        started_at=base + timedelta(days=3),
    )
    seed_recovery(
        repo, project_id, recovering, status=RecoveryStatus.INVESTIGATING,
        opened_at=base + timedelta(days=3, minutes=5),
    )

    first = client.get(
        f"/v2/projects/{project_id}/history?limit=3&offset=0", headers=auth_headers()
    )
    assert first.status_code == 200
    body = first.json()
    assert [item["status"] for item in body["changes"]] == [
        "recovering", "active", "cancelled"
    ]
    assert body["changes"][0]["recoveries"][0]["recheck_state"] is None
    assert body["changes"][1]["recoveries"][0]["recheck_state"] == "completed"
    assert body["has_more"] is True and body["next_offset"] == 3
    second = client.get(
        f"/v2/projects/{project_id}/history?limit=3&offset=3", headers=auth_headers()
    )
    assert [item["goal"] for item in second.json()["changes"]] == ["Old completed"]
    denied = client.get(f"/v2/projects/{project_id}/history", headers=auth_headers(USER_B))
    assert denied.status_code == 404


def test_history_orders_proposed_not_run_and_performed_checks_by_creation(client):
    project, repo = create_project(client)
    project_id = uuid.UUID(project["project_id"])
    started = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    change = seed_change(
        repo, project_id, goal="Check chronological states",
        state=CurrentChangeState.REVIEWING, started_at=started,
    )
    seed_check(
        repo, project_id, change, created_at=started + timedelta(minutes=1),
        status="proposed", plan="Still waiting to be run",
    )
    seed_check(
        repo, project_id, change, created_at=started + timedelta(minutes=2),
        status="not_run", not_run_at=started + timedelta(minutes=6),
        plan="Explicitly skipped check",
    )
    seed_check(
        repo, project_id, change, created_at=started + timedelta(minutes=3),
        status="performed", result=CheckResult.WORKED,
        observation="The result appeared", performed_at=started + timedelta(minutes=4),
        plan="Performed check",
    )

    response = client.get(f"/v2/projects/{project_id}/history", headers=auth_headers())
    assert response.status_code == 200, response.text
    checks = response.json()["changes"][0]["checks"]
    assert [check["check_plan"] for check in checks] == [
        "Still waiting to be run", "Explicitly skipped check", "Performed check"
    ]
    assert [check["status"] for check in checks] == ["proposed", "not_run", "performed"]
    assert checks[0]["performed_at"] is None and checks[0]["not_run_at"] is None
    assert checks[1]["not_run_at"] is not None
    assert checks[2]["performed_at"] is not None


@pytest.mark.parametrize(
    "visible_result", [CheckResult.DID_NOT_WORK, CheckResult.UNSURE]
)
def test_history_completion_uses_final_performed_check_beyond_display_bound(
    client, visible_result,
):
    project, repo = create_project(client)
    project_id = uuid.UUID(project["project_id"])
    started = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    change = seed_change(
        repo, project_id, goal="Verify the bounded history summary",
        state=CurrentChangeState.COMPLETED, started_at=started,
    )
    for index in range(55):
        result = CheckResult.WORKED if index == 54 else visible_result
        created_at = started + timedelta(minutes=index + 1)
        seed_check(
            repo, project_id, change, created_at=created_at,
            status="performed", result=result,
            observation=f"Check result {index + 1}",
            performed_at=created_at + timedelta(seconds=30),
            plan=f"Check {index + 1}",
        )

    response = client.get(f"/v2/projects/{project_id}/history", headers=auth_headers())
    assert response.status_code == 200, response.text
    item = response.json()["changes"][0]
    assert len(item["checks"]) == 50
    assert item["checks_truncated"] is True
    assert item["checks"][-1]["result"] == visible_result.value
    assert item["checks"][-1]["check_plan"] == "Check 50"
    assert item["completion_summary"] == (
        "Completed. The final student-performed check passed."
    )
    assert all("id" not in check for check in item["checks"])
