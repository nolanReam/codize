"""V2 Plan reads and typed commands over the atomic V2.2 Plan RPC."""

from __future__ import annotations

from uuid import UUID

from app.domain.v2 import V2Plan
from app.schemas.v2 import PlanItemView, PlanMutationRequest, PlanResponse
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_repository import (
    V2Repository,
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


def plan_view(plan: V2Plan) -> PlanResponse:
    plan.project_ref.require_v2()
    return PlanResponse(
        project_id=plan.project_ref.project_id,
        project_version=plan.project_version,
        plan_version=plan.plan_version,
        replayed=plan.replayed,
        items=[
            PlanItemView(
                id=item.id,
                label=item.label,
                intended_outcome=item.intended_outcome,
                scope_band=item.scope_band,
                status=item.status,
                order_key=item.order_key,
                version=item.version,
                completed_at=item.completed_at,
                terminal_current_change_id=item.terminal_current_change_id,
            )
            for item in plan.items
        ],
    )


async def get_plan(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
) -> PlanResponse:
    try:
        plan = await repo.get_plan(owner_user_id, project_id)
    except V2RepositoryConflict as exc:
        raise V2ConflictError("The Plan changed while it was loading. Try again.") from exc
    if plan is None:
        raise V2NotFoundError("V2 Project not found.")
    return plan_view(plan)


async def mutate_plan(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    request: PlanMutationRequest,
) -> PlanResponse:
    operations = [operation.model_dump(mode="json") for operation in request.operations]
    try:
        plan = await repo.mutate_plan(
            owner_user_id,
            project_id,
            request.expected_project_version,
            request.expected_plan_version,
            request.command_id,
            operations,
            request.expected_current_change_version,
            request.linked_item_action,
            request.cancellation_command_id,
            request.cancellation_reason_key,
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("V2 Project or Plan Item not found.") from exc
    except V2RepositoryConflict as exc:
        raise V2ConflictError("The Plan changed. Reload it before trying again.") from exc
    except V2RepositoryInvalidState as exc:
        raise V2ConflictError("This Plan change is not legal in the current state.") from exc
    return plan_view(plan)
