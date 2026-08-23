"""V2 Current Change start, resume read, and deterministic cancellation."""

from __future__ import annotations

from uuid import UUID

from app.domain.v2 import NONTERMINAL_STATES, V2CurrentChange, validate_cancellation
from app.schemas.v2 import (
    CancelCurrentChangeRequest,
    CurrentChangeResponse,
    CurrentChangeView,
    ResumeStateView,
    StartCurrentChangeRequest,
)
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_repository import (
    V2Repository,
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


def current_change_view(change: V2CurrentChange) -> CurrentChangeView:
    change.project_ref.require_v2()
    available_commands = ["cancel"] if change.lifecycle_state in NONTERMINAL_STATES else []
    return CurrentChangeView(
        id=change.id,
        project_id=change.project_ref.project_id,
        plan_item_id=change.plan_item_id,
        change_kind=change.change_kind,
        lifecycle_state=change.lifecycle_state,
        resume_step=change.resume_step,
        resume=ResumeStateView(
            lifecycle_state=change.lifecycle_state,
            resume_step=change.resume_step,
            available_commands=available_commands,
        ),
        goal_snapshot=change.goal_snapshot,
        done_condition_snapshot=change.done_condition_snapshot,
        boundary_snapshots=list(change.boundary_snapshots),
        prompt_draft=change.prompt_draft,
        prompt_draft_version=change.prompt_draft_version,
        coding_agent_key=change.coding_agent_key,
        effort_category=change.effort_category,
        latest_prompt_version_id=change.latest_prompt_version_id,
        version=change.version,
        created_at=change.created_at,
        updated_at=change.updated_at,
        completed_at=change.completed_at,
        cancelled_at=change.cancelled_at,
    )


async def start_current_change(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    request: StartCurrentChangeRequest,
) -> CurrentChangeResponse:
    try:
        change, replayed = await repo.start_current_change(
            owner_user_id,
            project_id,
            request.expected_project_version,
            request.command_id,
            request.plan_item_id,
            request.change_kind.value,
            request.goal_snapshot,
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("V2 Project or Plan Item not found.") from exc
    except V2RepositoryConflict as exc:
        raise V2ConflictError("This Project already has a Current Change or the Project changed.") from exc
    except V2RepositoryInvalidState as exc:
        raise V2ConflictError("A Current Change cannot start from this Project state.") from exc
    return CurrentChangeResponse(current_change=current_change_view(change), replayed=replayed)


async def get_current_change(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
) -> CurrentChangeResponse:
    try:
        change = await repo.get_current_change(owner_user_id, project_id)
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("V2 Project not found.") from exc
    return CurrentChangeResponse(
        current_change=current_change_view(change) if change is not None else None,
    )


async def cancel_current_change(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
    request: CancelCurrentChangeRequest,
) -> CurrentChangeResponse:
    current = await repo.get_current_change_by_id(
        owner_user_id,
        project_id,
        current_change_id,
    )
    if current is None:
        raise V2NotFoundError("V2 Current Change not found.")
    try:
        validate_cancellation(current, request.command_id)
    except ValueError as exc:
        raise V2ConflictError("This Current Change cannot be cancelled from its current state.") from exc

    try:
        change, replayed = await repo.cancel_current_change(
            owner_user_id,
            project_id,
            current_change_id,
            request.expected_current_change_version,
            request.command_id,
            request.reason,
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("V2 Current Change not found.") from exc
    except V2RepositoryConflict as exc:
        raise V2ConflictError("The Current Change changed. Reload it before cancelling.") from exc
    except V2RepositoryInvalidState as exc:
        raise V2ConflictError("This Current Change cannot be cancelled from its current state.") from exc
    return CurrentChangeResponse(current_change=current_change_view(change), replayed=replayed)
