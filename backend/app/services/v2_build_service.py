"""Deterministic V2 Build preparation, prompt acceptance, and handoff."""

from __future__ import annotations

from uuid import UUID

from app.domain.v2 import BuildStage, CodingAgentKey, CurrentChangeState, V2PromptVersion
from app.schemas.v2 import (
    AgentMetadataView,
    BuildResumeStateView,
    CodingAgentSelectionRequest,
    CodingAgentSelectionResponse,
    EffortSelectionRequest,
    PromptAcceptanceRequest,
    PromptAcceptanceResponse,
    PromptDraftUpdateRequest,
    PromptHandoffRequest,
    PromptHandoffResponse,
    PromptVersionView,
    PromptVersionsResponse,
    StructuredPromptDecisionsView,
)
from app.services.v2_agent_guidance import get_agent_metadata
from app.services.v2_current_change_service import current_change_view
from app.services.v2_manual_loop_service import check_view
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_repository import (
    V2Repository,
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


def _agent_view(key: CodingAgentKey | None) -> AgentMetadataView | None:
    if key is None:
        return None
    metadata = get_agent_metadata(key)
    return AgentMetadataView(
        key=metadata.key,
        display_name=metadata.display_name,
        reasoning_controls_known=metadata.reasoning_controls_known,
        mapping_available=(
            metadata.mapping_key is not None and metadata.mapping_version is not None
        ),
        stale_fallback=metadata.stale_fallback,
    )


def prompt_version_view(prompt: V2PromptVersion) -> PromptVersionView:
    return PromptVersionView(
        id=prompt.id,
        current_change_id=prompt.current_change_id,
        ordinal=prompt.ordinal,
        purpose=prompt.purpose,
        content=prompt.content,
        coding_agent_key=prompt.coding_agent_key,
        effort_category=prompt.effort_category,
        accepted_at=prompt.accepted_at,
        handed_off_at=prompt.handed_off_at,
        version=prompt.version,
    )


def _translate_write_error(exc: Exception, stale_message: str) -> Exception:
    if isinstance(exc, V2RepositoryNotFound):
        return V2NotFoundError("V2 Project or Current Change not found.")
    if isinstance(exc, (V2RepositoryConflict, V2RepositoryInvalidState)):
        return V2ConflictError(stale_message)
    return exc


async def select_coding_agent(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
    request: CodingAgentSelectionRequest,
) -> CodingAgentSelectionResponse:
    if request.choice == "help_me_choose":
        project = await repo.get_project(owner_user_id, project_id)
        change = await repo.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        if project is None or change is None:
            raise V2NotFoundError("V2 Project or Current Change not found.")
        if (
            project.version != request.expected_project_version
            or change.version != request.expected_current_change_version
        ):
            raise V2ConflictError("The Build state changed. Reload it before choosing an agent.")
        return CodingAgentSelectionResponse(
            project_id=project_id,
            current_change_id=current_change_id,
            project_version=project.version,
            current_change_version=change.version,
            selected_agent=_agent_view(change.coding_agent_key),
            guidance_required=True,
        )

    try:
        project, change = await repo.update_coding_agent(
            owner_user_id,
            project_id,
            current_change_id,
            request.expected_project_version,
            request.expected_current_change_version,
            request.choice,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate_write_error(
            exc, "The Build state changed or is not ready for agent selection."
        ) from exc
    return CodingAgentSelectionResponse(
        project_id=project_id,
        current_change_id=current_change_id,
        project_version=project.version,
        current_change_version=change.version,
        selected_agent=_agent_view(change.coding_agent_key),
        guidance_required=False,
    )


async def update_prompt_draft(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
    request: PromptDraftUpdateRequest,
):
    try:
        change = await repo.update_prompt_draft(
            owner_user_id,
            project_id,
            current_change_id,
            request.expected_current_change_version,
            request.expected_prompt_draft_version,
            request.prompt_text,
            request.done_condition,
            request.boundaries,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate_write_error(
            exc, "The prompt draft changed or cannot be edited in this state."
        ) from exc
    return current_change_view(change)


async def select_effort(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
    request: EffortSelectionRequest,
):
    try:
        change = await repo.update_effort(
            owner_user_id,
            project_id,
            current_change_id,
            request.expected_current_change_version,
            request.effort.value,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate_write_error(
            exc, "The Build state changed or cannot accept an effort selection."
        ) from exc
    return current_change_view(change)


async def accept_prompt(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
    request: PromptAcceptanceRequest,
) -> PromptAcceptanceResponse:
    try:
        change, prompt, replayed = await repo.accept_prompt_version(
            owner_user_id,
            project_id,
            current_change_id,
            request.expected_current_change_version,
            request.expected_prompt_draft_version,
            request.command_id,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate_write_error(
            exc, "The prompt changed or is not ready to be accepted."
        ) from exc
    return PromptAcceptanceResponse(
        current_change=current_change_view(change),
        prompt_version=prompt_version_view(prompt),
        replayed=replayed,
    )


async def list_prompt_versions(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
) -> PromptVersionsResponse:
    try:
        prompts = await repo.list_prompt_versions(
            owner_user_id, project_id, current_change_id
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("V2 Current Change not found.") from exc
    return PromptVersionsResponse(
        project_id=project_id,
        current_change_id=current_change_id,
        prompt_versions=[prompt_version_view(prompt) for prompt in prompts],
    )


async def handoff_prompt(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
    request: PromptHandoffRequest,
) -> PromptHandoffResponse:
    try:
        change, prompt, replayed = await repo.handoff_prompt_version(
            owner_user_id,
            project_id,
            current_change_id,
            request.prompt_version_id,
            request.expected_current_change_version,
            request.expected_prompt_version,
            request.command_id,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate_write_error(
            exc, "The accepted prompt changed or cannot be handed off."
        ) from exc
    return PromptHandoffResponse(
        current_change=current_change_view(change),
        prompt_version=prompt_version_view(prompt),
        exact_prompt=prompt.content,
        replayed=replayed,
    )


async def get_build_resume_state(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    current_change_id: UUID,
) -> BuildResumeStateView:
    change = await repo.get_current_change_by_id(
        owner_user_id, project_id, current_change_id
    )
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    try:
        prompts = await repo.list_prompt_versions(owner_user_id, project_id, current_change_id)
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("V2 Current Change not found.") from exc

    accepted = next(
        (prompt for prompt in reversed(prompts) if prompt.id == change.latest_prompt_version_id),
        None,
    )
    accepted_matches = bool(
        accepted
        and accepted.content == change.prompt_draft
        and accepted.coding_agent_key == change.coding_agent_key
        and accepted.effort_category == change.effort_category
        and accepted.input_goal_snapshot == change.goal_snapshot
        and accepted.input_done_condition_snapshot == change.done_condition_snapshot
        and accepted.input_boundary_snapshots == change.boundary_snapshots
    )
    latest_check = await repo.get_latest_check(owner_user_id, project_id, current_change_id)

    if change.lifecycle_state is CurrentChangeState.AWAITING_AGENT:
        stage = BuildStage.WAITING_FOR_RETURN
    elif change.lifecycle_state is CurrentChangeState.REVIEWING:
        if latest_check is not None and latest_check.status == "performed" and latest_check.result.value == "worked":
            stage = BuildStage.READY_TO_COMPLETE
        elif latest_check is not None and latest_check.status == "proposed":
            stage = (BuildStage.CHECK_UNSURE if change.student_return_outcome == "unsure"
                     else BuildStage.PERFORM_CHECK)
        else:
            stage = BuildStage.REPORT_RETURN_OUTCOME
    elif change.lifecycle_state is CurrentChangeState.RECOVERING:
        stage = BuildStage.CHECK_FAILED
    elif change.lifecycle_state is not CurrentChangeState.PREPARING:
        raise V2ConflictError("This Current Change is no longer active.")
    elif change.resume_step.value == "confirm_change":
        stage = BuildStage.CONFIRM_CHANGE
    elif change.coding_agent_key is None:
        stage = BuildStage.CHOOSE_AGENT
    elif change.prompt_draft is None:
        stage = BuildStage.EDIT_PROMPT
    elif change.effort_category is None:
        stage = BuildStage.CHOOSE_EFFORT
    elif accepted_matches:
        stage = BuildStage.READY_TO_HANDOFF
    else:
        stage = BuildStage.REVIEW_PROMPT

    return BuildResumeStateView(
        project_id=project_id,
        current_change_id=current_change_id,
        lifecycle_state=change.lifecycle_state,
        resume_step=change.resume_step,
        build_stage=stage,
        selected_agent=_agent_view(change.coding_agent_key),
        prompt_draft=change.prompt_draft,
        prompt_draft_version=change.prompt_draft_version,
        effort_category=change.effort_category,
        structured_decisions=StructuredPromptDecisionsView(
            intended_result=change.goal_snapshot,
            done_condition=change.done_condition_snapshot,
            boundaries=list(change.boundary_snapshots),
            coding_agent_key=change.coding_agent_key,
        ),
        accepted_prompt_version=prompt_version_view(accepted) if accepted else None,
        ready_to_handoff=(stage is BuildStage.READY_TO_HANDOFF),
        exact_handoff_prompt=(
            accepted.content
            if stage in {BuildStage.READY_TO_HANDOFF, BuildStage.WAITING_FOR_RETURN} and accepted
            else None
        ),
        current_change_version=change.version,
        active_check=check_view(latest_check),
        last_check_result=latest_check.result if latest_check else None,
    )
