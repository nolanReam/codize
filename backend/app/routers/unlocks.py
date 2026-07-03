"""Functional unlock routes — thin, auth-required; all logic in unlock_service.

One route: GET /unlocks lists what the current user has earned on their
current project. The catalog of possible rewards is already visible per phase
through the workspace (`functional_unlock` in every phase view), so there is
no separate "available" route — and the trigger rule, threshold, and raw gate
scores are server-only and appear in no response.
"""

from fastapi import APIRouter, Depends

from app.deps.auth import CurrentUser, require_user
from app.services import unlock_service
from app.services.project_repository import (
    ProjectRepository,
    UnlockRepository,
    get_project_repository,
    get_unlock_repository,
)

router = APIRouter(prefix="/unlocks")


@router.get("")
async def list_unlocks(
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    unlock_repo: UnlockRepository = Depends(get_unlock_repository),
) -> dict:
    return await unlock_service.list_unlocks(project_repo, unlock_repo, user.user_id)
