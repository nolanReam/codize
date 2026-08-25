"""Fail-closed tests for V2 database-row to domain conversion."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.services.v2_repository import (
    SupabaseV2Repository,
    V2RepositoryConflict,
    V2RepositoryError,
    _current_change_from_row,
    _project_from_row,
)


OWNER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
PROJECT_ID = UUID("10000000-0000-4000-8000-000000000001")
CHANGE_ID = UUID("20000000-0000-4000-8000-000000000001")
COMMAND_ID = UUID("30000000-0000-4000-8000-000000000001")
CHECK_ID = UUID("40000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 13, tzinfo=UTC).isoformat()


def project_row() -> dict:
    return {
        "id": str(PROJECT_ID),
        "owner_user_id": OWNER,
        "workflow_version": "v2",
        "display_name": "Owned project",
        "lifecycle_state": "active",
        "setup_resume_step": "ready",
        "coding_agent_key": None,
        "plan_version": 1,
        "first_version_completed_at": None,
        "version": 1,
        "created_at": NOW,
        "updated_at": NOW,
    }


def current_change_row() -> dict:
    return {
        "id": str(CHANGE_ID),
        "project_id": str(PROJECT_ID),
        "owner_user_id": OWNER,
        "plan_item_id": None,
        "change_kind": "build",
        "lifecycle_state": "preparing",
        "resume_step": "confirm_change",
        "goal_snapshot": "Add player totals",
        "done_condition_snapshot": None,
        "boundary_snapshots": [],
        "version": 1,
        "created_at": NOW,
        "updated_at": NOW,
        "completed_at": None,
        "cancelled_at": None,
        "cancellation_command_id": None,
        "cancellation_reason_key": None,
    }


def test_project_conversion_rejects_missing_or_non_v2_database_identity():
    missing_id = project_row()
    missing_id.pop("id")
    with pytest.raises(V2RepositoryError, match="malformed"):
        _project_from_row(missing_id, expected_owner=OWNER)

    wrong_version = project_row()
    wrong_version["workflow_version"] = "v1"
    with pytest.raises(V2RepositoryError, match="non-V2"):
        _project_from_row(wrong_version, expected_owner=OWNER)


def test_project_conversion_rejects_a_database_row_outside_the_expected_owner():
    with pytest.raises(V2RepositoryError, match="wrong owner"):
        _project_from_row(
            project_row(),
            expected_owner="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        )


def test_current_change_conversion_rejects_illegal_persisted_resume_state():
    row = current_change_row()
    row["lifecycle_state"] = "awaiting_agent"
    row["resume_step"] = "confirm_change"
    with pytest.raises(V2RepositoryError, match="illegal"):
        _current_change_from_row(
            row,
            expected_owner=OWNER,
            expected_project_id=PROJECT_ID,
        )


def test_production_repository_returns_canonical_check_plan_replay_before_requalification():
    row = current_change_row()
    row.update({"lifecycle_state": "reviewing", "resume_step": "check", "version": 9})
    canonical_change = _current_change_from_row(
        row, expected_owner=OWNER, expected_project_id=PROJECT_ID,
    )
    plan = "Add one point and observe the visible score increase"
    turn = {
        "id": str(COMMAND_ID), "project_id": str(PROJECT_ID),
        "current_change_id": str(CHANGE_ID), "turn_kind": "student_answer",
        "speaker": "student", "content": plan,
        "structured_payload": {"context": "verification", "competency_key": "testing"},
        "related_record_type": "check", "related_record_id": str(CHECK_ID),
        "support_level": "clue",
    }
    check = {
        "id": str(CHECK_ID), "project_id": str(PROJECT_ID), "owner_user_id": OWNER,
        "current_change_id": str(CHANGE_ID), "check_plan": plan,
        "plan_source": "student", "status": "proposed", "result": None,
        "student_observation": None, "performed_at": None, "not_run_at": None,
        "supersedes_check_id": None, "created_at": "2026-08-23T12:00:00Z",
        "version": 1,
    }
    repo = object.__new__(SupabaseV2Repository)
    repo._request = AsyncMock(side_effect=[[turn], [check]])
    repo.get_current_change_by_id = AsyncMock(return_value=canonical_change)

    replay = asyncio.run(repo.get_student_check_plan_replay(
        OWNER, PROJECT_ID, CHANGE_ID, COMMAND_ID, CHECK_ID, plan,
    ))

    assert replay is not None
    assert replay[0] == canonical_change
    assert replay[1].id == CHECK_ID
    assert replay[1].check_plan == plan
    assert repo._request.await_count == 2


def test_production_repository_replay_rejects_material_payload_mismatch():
    turn = {
        "id": str(COMMAND_ID), "project_id": str(PROJECT_ID),
        "current_change_id": str(CHANGE_ID), "turn_kind": "student_answer",
        "speaker": "student", "content": "Original plan",
        "structured_payload": {"context": "verification", "competency_key": "testing"},
        "related_record_type": "check", "related_record_id": str(CHECK_ID),
        "support_level": "clue",
    }
    repo = object.__new__(SupabaseV2Repository)
    repo._request = AsyncMock(return_value=[turn])

    with pytest.raises(V2RepositoryConflict, match="already used"):
        asyncio.run(repo.get_student_check_plan_replay(
            OWNER, PROJECT_ID, CHANGE_ID, COMMAND_ID, CHECK_ID, "Different plan",
        ))

    assert repo._request.await_count == 1


def test_history_repository_reads_checks_and_recoveries_in_canonical_bounded_order():
    repo = object.__new__(SupabaseV2Repository)
    repo._request = AsyncMock(side_effect=[[], [], []])

    assert asyncio.run(repo.list_history_checks(
        OWNER, PROJECT_ID, CHANGE_ID, limit=50,
    )) == ([], False)
    assert asyncio.run(repo.list_history_recovery_cases(
        OWNER, PROJECT_ID, CHANGE_ID, limit=10,
    )) == ([], False)
    assert asyncio.run(repo.get_latest_history_performed_check(
        OWNER, PROJECT_ID, CHANGE_ID,
    )) is None

    check_params = repo._request.await_args_list[0].kwargs["params"]
    recovery_params = repo._request.await_args_list[1].kwargs["params"]
    final_check_params = repo._request.await_args_list[2].kwargs["params"]
    assert check_params["order"] == "created_at.asc,id.asc"
    assert check_params["limit"] == "51"
    assert recovery_params["order"] == "opened_at.asc,id.asc"
    assert recovery_params["limit"] == "11"
    assert final_check_params["status"] == "eq.performed"
    assert final_check_params["order"] == "performed_at.desc,id.desc"
    assert final_check_params["limit"] == "1"
