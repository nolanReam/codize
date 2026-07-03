"""Evaluation route — thin, auth-required; all logic in evaluation_service.

GET /evaluation is a pure read returning a deterministic, safe progress
evaluation of the caller's own current project. Every outcome is a controlled
200 state (not_started / intake_needed / roadmap_needed / in_progress /
gate_ready / cooldown / complete) — no project yet is a state, not an error.
Responses never contain gate scores, unlock thresholds, evaluator internals,
prompt text, or server-only keys.
"""

from fastapi import APIRouter, Depends

from app.deps.auth import CurrentUser, require_user
from app.services import evaluation_service
from app.services.project_repository import (
    GateSessionRepository,
    ProjectRepository,
    UnlockRepository,
    get_gate_session_repository,
    get_project_repository,
    get_unlock_repository,
)

router = APIRouter(prefix="/evaluation")


@router.get("")
async def get_evaluation(
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
    unlock_repo: UnlockRepository = Depends(get_unlock_repository),
) -> dict:
    return await evaluation_service.get_evaluation(
        project_repo, gate_repo, unlock_repo, user.user_id
    )
