"""Authenticated student-safe Defense Report context route (M16C.1)."""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.services import phase_service, report_service
from app.services.project_repository import (
    GateSessionRepository,
    ProjectRepository,
    get_gate_session_repository,
    get_project_repository,
)

router = APIRouter(prefix="/report")


@router.get("/{phase_number}")
async def get_report_context(
    phase_number: int,
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
) -> dict:
    try:
        report = await report_service.build_report_context(
            project_repo, gate_repo, user.user_id, phase_number
        )
    except phase_service.PhaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except phase_service.PhaseWorkspaceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return report.model_dump(mode="json")
