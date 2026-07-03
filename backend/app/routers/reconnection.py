"""Reconnection routes — thin, auth-required; all logic in reconnection_service.

GET /reconnection is a pure read (never writes, so it can never suppress the
modal by touching the timestamp); POST /reconnection/acknowledge is the only
writer of profiles.last_login_at. Frontend contract: GET first on every login,
then acknowledge (immediately when not needed, on the "Let's keep building"
click when needed). Every state is a controlled 200 — no project or roadmap
yet is a "workspace_not_ready" state, not an error. Responses never contain
gate scores, thresholds, prompts, or server-only keys.
"""

from fastapi import APIRouter, Depends

from app.deps.auth import CurrentUser, require_user
from app.services import reconnection_service
from app.services.project_repository import (
    ProfileRepository,
    ProjectRepository,
    UnlockRepository,
    get_profile_repository,
    get_project_repository,
    get_unlock_repository,
)

router = APIRouter(prefix="/reconnection")


@router.get("")
async def get_reconnection_state(
    user: CurrentUser = Depends(require_user),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
    unlock_repo: UnlockRepository = Depends(get_unlock_repository),
) -> dict:
    return await reconnection_service.get_reconnection_state(
        profile_repo, project_repo, unlock_repo, user.user_id
    )


@router.post("/acknowledge")
async def acknowledge(
    user: CurrentUser = Depends(require_user),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> dict:
    return await reconnection_service.acknowledge(profile_repo, user.user_id)
