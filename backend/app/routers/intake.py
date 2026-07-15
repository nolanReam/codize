"""Intake routes — thin, auth-required; all intake logic lives in the service.

The user id comes only from the verified JWT (require_user); the repository
scopes every read/write to it, so a user can never touch another user's
intake state. Controlled intake errors map to the standard error shape.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.schemas.intake import AnswerRequest, EntryProfileUpdateRequest
from app.services import intake_service
from app.services.project_repository import ProjectRepository, get_project_repository

router = APIRouter(prefix="/intake")


def _http_error(exc: intake_service.IntakeError) -> HTTPException:
    status = 422 if isinstance(
        exc,
        (intake_service.InvalidAnswerError, intake_service.InvalidEntryProfileError),
    ) else 409
    return HTTPException(status_code=status, detail=str(exc))


@router.get("/questions")
async def get_questions(user: CurrentUser = Depends(require_user)) -> dict:
    return {"questions": intake_service.get_questions()}


@router.get("/entry-profile")
async def get_entry_profile(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    return await intake_service.get_entry_profile(repo, user.user_id)


@router.put("/entry-profile")
async def update_entry_profile(
    body: EntryProfileUpdateRequest,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await intake_service.update_entry_profile(
            repo, user.user_id, body.model_dump(exclude_unset=True)
        )
    except intake_service.IntakeError as exc:
        raise _http_error(exc)


@router.get("/status")
async def get_status(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    return await intake_service.get_status(repo, user.user_id)


@router.post("/answers")
async def submit_answer(
    body: AnswerRequest,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await intake_service.submit_answer(repo, user.user_id, body.question, body.answer)
    except intake_service.IntakeError as exc:
        raise _http_error(exc)


@router.post("/complete")
async def complete_intake(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await intake_service.complete_intake(repo, user.user_id)
    except intake_service.IntakeError as exc:
        raise _http_error(exc)
