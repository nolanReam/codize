"""Workflow artifact routes (M13B) — thin, auth-required; logic in the service.

The user id comes only from the verified JWT and the repository scopes every
read/write to it, so a user can only ever see or update their own artifacts.
Controlled errors map to the standard shape: workspace not ready → 409,
unknown phase or section → 404, invalid or oversized payload → 422.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.services import phase_service, workflow_service
from app.services.project_repository import ProjectRepository, get_project_repository

router = APIRouter(prefix="/workflow")


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, phase_service.PhaseNotFoundError) or isinstance(
        exc, workflow_service.SectionNotFoundError
    ):
        status = 404
    elif isinstance(exc, workflow_service.InvalidArtifactError):
        status = 422
    else:  # workspace not ready
        status = 409
    return HTTPException(status_code=status, detail=str(exc))


@router.get("/{phase_number}")
async def get_phase_artifacts(
    phase_number: int,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await workflow_service.get_phase_artifacts(repo, user.user_id, phase_number)
    except (phase_service.PhaseWorkspaceError, workflow_service.WorkflowError) as exc:
        raise _http_error(exc)


@router.put("/{phase_number}/{section}")
async def put_section(
    phase_number: int,
    section: str,
    body: dict,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await workflow_service.save_section(
            repo, user.user_id, phase_number, section, body
        )
    except (phase_service.PhaseWorkspaceError, workflow_service.WorkflowError) as exc:
        raise _http_error(exc)
