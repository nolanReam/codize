"""Internal-only Generation Attempt lifecycle for V2 model calls."""

from __future__ import annotations

from uuid import UUID

from app.domain.v2 import V2GenerationAttempt
from app.schemas.v2 import (
    ApplyGeneratedPromptDraftRequest,
    ApplyGeneratedPromptDraftResponse,
    FinishGenerationAttemptRequest,
    GenerationAttemptView,
    StartGenerationAttemptRequest,
)
from app.services.v2_current_change_service import current_change_view
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_repository import (
    V2Repository,
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


def generation_attempt_view(attempt: V2GenerationAttempt) -> GenerationAttemptView:
    return GenerationAttemptView(
        id=attempt.id,
        project_id=attempt.project_ref.project_id,
        purpose=attempt.purpose,
        target_aggregate_version=attempt.target_aggregate_version,
        status=attempt.status,
        safe_error_category=attempt.safe_error_category,
        retryable=attempt.retryable,
        result_record_type=attempt.result_record_type,
        result_record_id=attempt.result_record_id,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        version=attempt.version,
    )


async def start_attempt(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    request: StartGenerationAttemptRequest,
) -> tuple[GenerationAttemptView, bool]:
    try:
        attempt, replayed = await repo.start_generation_attempt(
            owner_user_id,
            project_id,
            request.model_dump(mode="json"),
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("Generation target not found.") from exc
    except (V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise V2ConflictError("The generation target changed or is not eligible.") from exc
    return generation_attempt_view(attempt), replayed


async def finish_attempt(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    generation_attempt_id: UUID,
    request: FinishGenerationAttemptRequest,
) -> GenerationAttemptView:
    try:
        attempt = await repo.finish_generation_attempt(
            owner_user_id,
            project_id,
            generation_attempt_id,
            request.model_dump(mode="json"),
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("Generation Attempt not found.") from exc
    except (V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise V2ConflictError("The Generation Attempt changed or cannot be completed.") from exc
    return generation_attempt_view(attempt)


async def apply_prompt_draft(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    generation_attempt_id: UUID,
    request: ApplyGeneratedPromptDraftRequest,
) -> ApplyGeneratedPromptDraftResponse:
    """Atomically apply a current generated draft or supersede its stale attempt."""

    try:
        attempt, change, applied, replayed = await repo.apply_generated_prompt_draft(
            owner_user_id,
            project_id,
            generation_attempt_id,
            request.expected_attempt_version,
            request.expected_current_change_version,
            request.expected_prompt_draft_version,
            request.prompt_text,
            request.done_condition,
            request.boundaries,
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("Generation Attempt or Current Change not found.") from exc
    except (V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise V2ConflictError(
            "The generated prompt result is stale or cannot be applied."
        ) from exc
    return ApplyGeneratedPromptDraftResponse(
        generation_attempt=generation_attempt_view(attempt),
        current_change=current_change_view(change),
        applied=applied,
        replayed=replayed,
    )
