"""Phase workspace routes — thin, auth-required; all logic lives in the service.

The user id comes only from the verified JWT (require_user) and the repository
scopes every read/write to it, so a user can only ever see or update their own
phase state. Controlled errors map to the standard error shape: workspace not
ready → 409, unknown phase/task → 404.

Note: /current is declared before /{phase_number} so it isn't captured by the
int path parameter.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.schemas.phases import AssignmentSelectionRequest, TaskUpdateRequest
from app.services import phase_service
from app.services.project_repository import ProjectRepository, get_project_repository

router = APIRouter(prefix="/phases")


def _http_error(exc: phase_service.PhaseWorkspaceError) -> HTTPException:
    if isinstance(exc, (phase_service.PhaseNotFoundError, phase_service.TaskNotFoundError)):
        status = 404
    else:  # workspace not ready
        status = 409
    return HTTPException(status_code=status, detail=str(exc))


@router.get("")
async def list_phases(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await phase_service.list_phases(repo, user.user_id)
    except phase_service.PhaseWorkspaceError as exc:
        raise _http_error(exc)


@router.get("/current")
async def get_current_phase(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await phase_service.get_current_phase(repo, user.user_id)
    except phase_service.PhaseWorkspaceError as exc:
        raise _http_error(exc)


@router.get("/current/assignment")
async def get_current_assignment(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await phase_service.get_current_assignment(repo, user.user_id)
    except phase_service.PhaseWorkspaceError as exc:
        raise _http_error(exc)


@router.put("/current/assignment")
async def select_current_assignment(
    body: AssignmentSelectionRequest,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await phase_service.select_current_assignment(
            repo, user.user_id, body.task_id
        )
    except phase_service.PhaseWorkspaceError as exc:
        raise _http_error(exc)


@router.get("/{phase_number}")
async def get_phase(
    phase_number: int,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await phase_service.get_phase(repo, user.user_id, phase_number)
    except phase_service.PhaseWorkspaceError as exc:
        raise _http_error(exc)


@router.patch("/{phase_number}/tasks/{task_id}")
async def update_task(
    phase_number: int,
    task_id: str,
    body: TaskUpdateRequest,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await phase_service.set_task_completion(
            repo, user.user_id, phase_number, task_id, body.completed
        )
    except phase_service.PhaseWorkspaceError as exc:
        raise _http_error(exc)
