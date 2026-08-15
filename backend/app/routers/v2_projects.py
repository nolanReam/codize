"""Authenticated, explicit-ID Codize V2 Project/Plan/Current Change routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.schemas.v2 import (
    CancelCurrentChangeRequest,
    CreateProjectRequest,
    CurrentChangeResponse,
    PlanMutationRequest,
    PlanResponse,
    ProjectCommandResponse,
    ProjectRefsResponse,
    PromoteProjectRequest,
    PurgeProjectResponse,
    PurgeTemporaryProjectRequest,
    StartCurrentChangeRequest,
    V2ProjectView,
)
from app.services import (
    v2_current_change_service,
    v2_plan_service,
    v2_project_service,
)
from app.services.project_repository import ProjectRepository, get_project_repository
from app.services.v2_errors import (
    V2ApplicationError,
    V2ConflictError,
    V2InvalidRequestError,
    V2NotFoundError,
)
from app.services.v2_repository import V2Repository, get_v2_repository

router = APIRouter(prefix="/v2", tags=["v2"])


def _http_error(exc: V2ApplicationError) -> HTTPException:
    if isinstance(exc, V2NotFoundError):
        status = 404
    elif isinstance(exc, V2ConflictError):
        status = 409
    elif isinstance(exc, V2InvalidRequestError):
        status = 422
    else:
        status = 500
    return HTTPException(status_code=status, detail=str(exc))


@router.post("/projects", response_model=ProjectCommandResponse)
async def create_project(
    body: CreateProjectRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> ProjectCommandResponse:
    try:
        return await v2_project_service.create_project(repo, user.user_id, body)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.get("/project-refs", response_model=ProjectRefsResponse)
async def list_project_refs(
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
    legacy_repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectRefsResponse:
    return await v2_project_service.list_project_refs(
        repo,
        legacy_repo,
        user.user_id,
    )


@router.get("/projects/{project_id}", response_model=V2ProjectView)
async def get_project(
    project_id: UUID,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> V2ProjectView:
    try:
        return await v2_project_service.get_project(repo, user.user_id, project_id)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/promote", response_model=ProjectCommandResponse)
async def promote_temporary_project(
    project_id: UUID,
    body: PromoteProjectRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> ProjectCommandResponse:
    try:
        return await v2_project_service.promote_temporary_project(
            repo,
            user.user_id,
            project_id,
            body.expected_project_version,
            body.command_id,
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/discard-temporary",
    response_model=PurgeProjectResponse,
)
async def discard_temporary_project(
    project_id: UUID,
    body: PurgeTemporaryProjectRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> PurgeProjectResponse:
    try:
        return await v2_project_service.purge_temporary_project(
            repo,
            user.user_id,
            project_id,
            body.expected_project_version,
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.get("/projects/{project_id}/plan", response_model=PlanResponse)
async def get_plan(
    project_id: UUID,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> PlanResponse:
    try:
        return await v2_plan_service.get_plan(repo, user.user_id, project_id)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/plan/mutations", response_model=PlanResponse)
async def mutate_plan(
    project_id: UUID,
    body: PlanMutationRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> PlanResponse:
    try:
        return await v2_plan_service.mutate_plan(repo, user.user_id, project_id, body)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change",
    response_model=CurrentChangeResponse,
)
async def start_current_change(
    project_id: UUID,
    body: StartCurrentChangeRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> CurrentChangeResponse:
    try:
        return await v2_current_change_service.start_current_change(
            repo,
            user.user_id,
            project_id,
            body,
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/projects/{project_id}/current-change",
    response_model=CurrentChangeResponse,
)
async def get_current_change(
    project_id: UUID,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> CurrentChangeResponse:
    try:
        return await v2_current_change_service.get_current_change(
            repo,
            user.user_id,
            project_id,
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change/{current_change_id}/cancel",
    response_model=CurrentChangeResponse,
)
async def cancel_current_change(
    project_id: UUID,
    current_change_id: UUID,
    body: CancelCurrentChangeRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> CurrentChangeResponse:
    try:
        return await v2_current_change_service.cancel_current_change(
            repo,
            user.user_id,
            project_id,
            current_change_id,
            body,
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc
