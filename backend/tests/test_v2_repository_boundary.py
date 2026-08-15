"""Fail-closed tests for V2 database-row to domain conversion."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.services.v2_repository import (
    V2RepositoryError,
    _current_change_from_row,
    _project_from_row,
)


OWNER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
PROJECT_ID = UUID("10000000-0000-4000-8000-000000000001")
CHANGE_ID = UUID("20000000-0000-4000-8000-000000000001")
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
