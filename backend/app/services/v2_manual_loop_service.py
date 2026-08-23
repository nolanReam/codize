"""Phase 4 deterministic manual Build-loop commands and projections."""

from uuid import UUID

from app.domain.v2 import CheckResult, V2Check, V2UserPreferences
from app.schemas.v2 import (
    CheckView, CompleteManualChangeRequest, CompleteManualChangeResponse,
    ConfirmManualChangeRequest, CurrentChangeResponse, ManualCheckRequest,
    ManualLoopResponse, ManualReturnRequest, UserPreferencesView,
    UpdateDialogueSoundRequest,
)
from app.services.v2_current_change_service import current_change_view
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_plan_service import plan_view
from app.services.v2_project_service import project_view
from app.services.v2_repository import (
    V2Repository, V2RepositoryConflict, V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


def check_view(check: V2Check | None) -> CheckView | None:
    if check is None:
        return None
    return CheckView(
        id=check.id, current_change_id=check.current_change_id,
        check_plan=check.check_plan, status=check.status, result=check.result,
        student_observation=check.student_observation,
        performed_at=check.performed_at, version=check.version,
    )


def preferences_view(preferences: V2UserPreferences) -> UserPreferencesView:
    return UserPreferencesView(
        dialogue_sound_enabled=preferences.dialogue_sound_enabled,
        motion_preference=preferences.motion_preference,
        version=preferences.version,
    )


def _translate(exc: Exception, message: str) -> Exception:
    if isinstance(exc, V2RepositoryNotFound):
        return V2NotFoundError("V2 Project, Current Change, or Check not found.")
    if isinstance(exc, (V2RepositoryConflict, V2RepositoryInvalidState)):
        return V2ConflictError(message)
    return exc


async def confirm_change(repo: V2Repository, owner: str, project_id: UUID,
                         change_id: UUID, request: ConfirmManualChangeRequest) -> CurrentChangeResponse:
    try:
        change, replayed = await repo.confirm_manual_current_change(
            owner, project_id, change_id, request.expected_current_change_version,
            request.command_id,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The change was updated or cannot be confirmed.") from exc
    return CurrentChangeResponse(current_change=current_change_view(change), replayed=replayed)


async def record_return(repo: V2Repository, owner: str, project_id: UUID,
                        change_id: UUID, request: ManualReturnRequest) -> ManualLoopResponse:
    try:
        change, check, replayed = await repo.record_manual_return(
            owner, project_id, change_id, request.expected_current_change_version,
            request.command_id, request.outcome, request.check_id,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The return state changed or cannot accept this report.") from exc
    return ManualLoopResponse(current_change=current_change_view(change),
                              check=check_view(check), replayed=replayed)


async def record_check(repo: V2Repository, owner: str, project_id: UUID,
                       change_id: UUID, check_id: UUID,
                       request: ManualCheckRequest) -> ManualLoopResponse:
    try:
        change, check, next_check, replayed = await repo.record_manual_check(
            owner, project_id, change_id, check_id,
            request.expected_current_change_version, request.expected_check_version,
            request.command_id, request.result.value, request.observation,
            request.performed_by_student, request.next_check_id,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The check changed or could not be recorded.") from exc
    return ManualLoopResponse(current_change=current_change_view(change),
        check=check_view(check), next_check=check_view(next_check), replayed=replayed)


async def complete_change(repo: V2Repository, owner: str, project_id: UUID,
                          change_id: UUID,
                          request: CompleteManualChangeRequest) -> CompleteManualChangeResponse:
    check = await repo.get_latest_check(owner, project_id, change_id)
    if (check is None or check.status != "performed" or check.result is not CheckResult.WORKED
            or not check.student_observation or check.performed_at is None):
        raise V2ConflictError("A student-performed successful check is required before completion.")
    try:
        replayed = await repo.complete_manual_change(
            owner, project_id, change_id, request.expected_current_change_version,
            request.expected_plan_version, request.expected_plan_item_version,
            request.command_id, check,
        )
        change = await repo.get_current_change_by_id(owner, project_id, change_id)
        project = await repo.get_project(owner, project_id)
        plan = await repo.get_plan(owner, project_id)
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The Build state changed or is not eligible for completion.") from exc
    if change is None or project is None or plan is None:
        raise V2NotFoundError("Completed V2 state could not be reloaded.")
    return CompleteManualChangeResponse(
        current_change=current_change_view(change), project=project_view(project),
        plan=plan_view(plan), check=check_view(check), replayed=replayed,
    )


async def get_preferences(repo: V2Repository, owner: str) -> UserPreferencesView:
    return preferences_view(await repo.get_preferences(owner))


async def update_dialogue_sound(repo: V2Repository, owner: str,
                                request: UpdateDialogueSoundRequest) -> UserPreferencesView:
    try:
        preferences = await repo.update_dialogue_sound(
            owner, request.expected_version, request.dialogue_sound_enabled
        )
    except (V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise V2ConflictError("The preference changed. Reload before trying again.") from exc
    return preferences_view(preferences)
