"""Authenticated, explicit-ID Codize V2 Project and Build routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.schemas.v2 import (
    BuildResumeStateView,
    CancelCurrentChangeRequest,
    CodingAgentSelectionRequest,
    CodingAgentSelectionResponse,
    CreateProjectRequest,
    CompleteManualChangeRequest,
    CompleteManualChangeResponse,
    ConfirmManualChangeRequest,
    CurrentChangeResponse,
    CurrentChangeView,
    EffortAttemptRequest,
    EffortAttemptResponse,
    EffortSelectionRequest,
    EstablishManualProjectRequest,
    EstablishManualProjectResponse,
    ManualCheckRequest,
    ManualLoopResponse,
    ManualReturnRequest,
    CheckPlanRequest,
    PlanMutationRequest,
    PlanResponse,
    ProjectCommandResponse,
    ProjectRefsResponse,
    PromptAcceptanceRequest,
    PromptAcceptanceResponse,
    PromptDraftUpdateRequest,
    PromptHandoffRequest,
    PromptHandoffResponse,
    PromptVersionsResponse,
    RecentChangesResponse,
    PromoteProjectRequest,
    PurgeProjectResponse,
    PurgeTemporaryProjectRequest,
    StartCurrentChangeRequest,
    UpdateDialogueSoundRequest,
    TeachingCommandResponse,
    TeachingHelpRequest,
    TeachingResponseRequest,
    UserPreferencesView,
    V2ProjectView,
)
from app.services import (
    v2_build_service,
    v2_current_change_service,
    v2_manual_loop_service,
    v2_plan_service,
    v2_project_service,
    v2_teaching_service,
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


@router.post("/projects/{project_id}/manual-setup", response_model=EstablishManualProjectResponse)
async def establish_manual_project(
    project_id: UUID, body: EstablishManualProjectRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> EstablishManualProjectResponse:
    try:
        return await v2_project_service.establish_manual_project(repo, user.user_id, project_id, body)
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


@router.get("/projects/{project_id}/recent-changes", response_model=RecentChangesResponse)
async def list_recent_changes(
    project_id: UUID, user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> RecentChangesResponse:
    try:
        return await v2_project_service.list_recent_changes(repo, user.user_id, project_id)
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


@router.post("/projects/{project_id}/current-change/{current_change_id}/confirm",
             response_model=CurrentChangeResponse)
async def confirm_manual_change(
    project_id: UUID, current_change_id: UUID, body: ConfirmManualChangeRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> CurrentChangeResponse:
    try:
        return await v2_manual_loop_service.confirm_change(
            repo, user.user_id, project_id, current_change_id, body)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change/{current_change_id}/teaching/help",
    response_model=TeachingCommandResponse,
)
async def disclose_teaching_help(
    project_id: UUID, current_change_id: UUID, body: TeachingHelpRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> TeachingCommandResponse:
    try:
        return await v2_teaching_service.disclose_help(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change/{current_change_id}/teaching/respond",
    response_model=TeachingCommandResponse,
)
async def record_teaching_response(
    project_id: UUID, current_change_id: UUID, body: TeachingResponseRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> TeachingCommandResponse:
    try:
        return await v2_teaching_service.record_response(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change/{current_change_id}/effort-attempts",
    response_model=EffortAttemptResponse,
)
async def record_effort_attempt(
    project_id: UUID, current_change_id: UUID, body: EffortAttemptRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> EffortAttemptResponse:
    try:
        return await v2_teaching_service.record_effort(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change/{current_change_id}/checks",
    response_model=ManualLoopResponse,
)
async def create_student_check_plan(
    project_id: UUID, current_change_id: UUID, body: CheckPlanRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> ManualLoopResponse:
    try:
        return await v2_teaching_service.create_check_plan(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/current-change/{current_change_id}/return",
             response_model=ManualLoopResponse)
async def record_manual_return(
    project_id: UUID, current_change_id: UUID, body: ManualReturnRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> ManualLoopResponse:
    try:
        return await v2_manual_loop_service.record_return(
            repo, user.user_id, project_id, current_change_id, body)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/current-change/{current_change_id}/checks/{check_id}",
             response_model=ManualLoopResponse)
async def record_manual_check(
    project_id: UUID, current_change_id: UUID, check_id: UUID, body: ManualCheckRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> ManualLoopResponse:
    try:
        return await v2_manual_loop_service.record_check(
            repo, user.user_id, project_id, current_change_id, check_id, body)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/current-change/{current_change_id}/complete",
             response_model=CompleteManualChangeResponse)
async def complete_manual_change(
    project_id: UUID, current_change_id: UUID, body: CompleteManualChangeRequest,
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> CompleteManualChangeResponse:
    try:
        return await v2_manual_loop_service.complete_change(
            repo, user.user_id, project_id, current_change_id, body)
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.get("/preferences", response_model=UserPreferencesView)
async def get_preferences(
    user: CurrentUser = Depends(require_user), repo: V2Repository = Depends(get_v2_repository),
) -> UserPreferencesView:
    return await v2_manual_loop_service.get_preferences(repo, user.user_id)


@router.put("/preferences/dialogue-sound", response_model=UserPreferencesView)
async def update_dialogue_sound(
    body: UpdateDialogueSoundRequest, user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> UserPreferencesView:
    try:
        return await v2_manual_loop_service.update_dialogue_sound(repo, user.user_id, body)
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


@router.put(
    "/projects/{project_id}/current-change/{current_change_id}/coding-agent",
    response_model=CodingAgentSelectionResponse,
)
async def select_coding_agent(
    project_id: UUID,
    current_change_id: UUID,
    body: CodingAgentSelectionRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> CodingAgentSelectionResponse:
    try:
        return await v2_build_service.select_coding_agent(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.put(
    "/projects/{project_id}/current-change/{current_change_id}/prompt-draft",
    response_model=CurrentChangeView,
)
async def update_prompt_draft(
    project_id: UUID,
    current_change_id: UUID,
    body: PromptDraftUpdateRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> CurrentChangeView:
    try:
        return await v2_build_service.update_prompt_draft(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.put(
    "/projects/{project_id}/current-change/{current_change_id}/effort",
    response_model=CurrentChangeView,
    deprecated=True,
)
async def select_legacy_effort(
    project_id: UUID,
    current_change_id: UUID,
    body: EffortSelectionRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> CurrentChangeView:
    """Compatibility-only: Phase 5 policy rejects this mutation fail closed."""
    try:
        return await v2_build_service.select_effort(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change/{current_change_id}/prompt-versions",
    response_model=PromptAcceptanceResponse,
)
async def accept_prompt_version(
    project_id: UUID,
    current_change_id: UUID,
    body: PromptAcceptanceRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> PromptAcceptanceResponse:
    try:
        return await v2_build_service.accept_prompt(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/projects/{project_id}/current-change/{current_change_id}/prompt-versions",
    response_model=PromptVersionsResponse,
)
async def list_prompt_versions(
    project_id: UUID,
    current_change_id: UUID,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> PromptVersionsResponse:
    try:
        return await v2_build_service.list_prompt_versions(
            repo, user.user_id, project_id, current_change_id
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/projects/{project_id}/current-change/{current_change_id}/handoff",
    response_model=PromptHandoffResponse,
)
async def handoff_prompt(
    project_id: UUID,
    current_change_id: UUID,
    body: PromptHandoffRequest,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> PromptHandoffResponse:
    try:
        return await v2_build_service.handoff_prompt(
            repo, user.user_id, project_id, current_change_id, body
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/projects/{project_id}/current-change/{current_change_id}/build-state",
    response_model=BuildResumeStateView,
)
async def get_build_resume_state(
    project_id: UUID,
    current_change_id: UUID,
    user: CurrentUser = Depends(require_user),
    repo: V2Repository = Depends(get_v2_repository),
) -> BuildResumeStateView:
    try:
        return await v2_build_service.get_build_resume_state(
            repo, user.user_id, project_id, current_change_id
        )
    except V2ApplicationError as exc:
        raise _http_error(exc) from exc
