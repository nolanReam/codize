"""Contextual Observe -> Investigate -> Correct -> Recheck recovery flow."""

from __future__ import annotations

from uuid import UUID

from app.domain.v2 import CheckResult, PromptPurpose, RecoveryStatus, V2RecoveryCase
from app.schemas.v2 import (
    RecoveryCaseView,
    RecoveryCheckRequest,
    RecoveryCommandResponse,
    RecoveryCorrectionReturnRequest,
    RecoveryInvestigationReturnRequest,
    RecoveryPromptAcceptanceRequest,
    RecoveryPromptHandoffRequest,
    RecoverySymptomRequest,
)
from app.services import v2_teaching_service
from app.services.v2_build_service import prompt_version_view
from app.services.v2_current_change_service import current_change_view
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_manual_loop_service import check_view
from app.services.v2_repository import (
    V2Repository,
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


def recovery_view(recovery: V2RecoveryCase) -> RecoveryCaseView:
    return RecoveryCaseView(
        id=recovery.id,
        current_change_id=recovery.current_change_id,
        status=recovery.status,
        intended_behavior=recovery.intended_behavior,
        observed_symptom=recovery.observed_symptom,
        last_known_working_statement=recovery.last_known_working_statement,
        last_known_working_certainty=recovery.last_known_working_certainty,
        candidate_change_summary=recovery.candidate_change_summary,
        student_hypothesis=recovery.student_hypothesis,
        proposed_first_check=recovery.proposed_first_check,
        investigation_finding=recovery.investigation_finding,
        investigation_finding_provenance=(
            "agent_claimed" if recovery.investigation_finding else None
        ),
        cause_summary=recovery.cause_summary,
        correction_summary=recovery.correction_summary,
        resolution_summary=recovery.resolution_summary,
        opened_at=recovery.opened_at,
        resolved_at=recovery.resolved_at,
        version=recovery.version,
    )


def _boundaries(values: tuple[str, ...]) -> str:
    if not values:
        return "Preserve unrelated working behavior."
    return "\n".join(f"- {value}" for value in values)


def investigation_prompt(change, symptom: str, *, prior_observation: str | None = None) -> str:
    history = (
        f"\nNewest student-observed failed recheck:\n{prior_observation}\n"
        if prior_observation else ""
    )
    return f"""INVESTIGATION ONLY — DO NOT MODIFY FILES YET.

Intended change:
{change.goal_snapshot}

Done condition:
{change.done_condition_snapshot or "The intended behavior can be personally observed."}

Student-observed symptom:
{symptom}
{history}
Boundaries:
{_boundaries(change.boundary_snapshots)}

Inspect the current implementation before editing. Identify the most likely cause or a small set of likely causes. Point to the relevant files, code, runtime behavior, or other evidence. Explain how that evidence supports each hypothesis and identify the smallest likely correction.

Do not make changes yet. Do not broadly refactor. Report what you inspected, what you found, and what remains uncertain."""


def correction_prompt(change, recovery: V2RecoveryCase, finding: str) -> str:
    return f"""MAKE ONE TARGETED CORRECTION.

Original change:
{change.goal_snapshot}

Done condition:
{change.done_condition_snapshot or recovery.intended_behavior}

Student-observed symptom:
{recovery.observed_symptom}

Coding-agent investigation finding (a hypothesis, not verified truth):
{finding}

Boundaries:
{_boundaries(change.boundary_snapshots)}

Make the smallest targeted change justified by the investigation. Do not refactor unrelated code. Preserve existing working behavior and the boundaries above. If the evidence does not justify a safe correction, stop and explain what still needs investigation instead of guessing.

Report exactly what changed and tell the student what behavior they should personally recheck. Do not claim the bug is fixed; the student will recheck it."""


def _risk(change, prompt: str):
    relevant = v2_teaching_service.risk_relevant_text(
        change.goal_snapshot,
        change.done_condition_snapshot,
        change.boundary_snapshots,
        prompt,
    )
    decision = v2_teaching_service.classify_risk(relevant)
    fingerprint = v2_teaching_service.risk_input_fingerprint(
        change.goal_snapshot,
        change.done_condition_snapshot,
        change.boundary_snapshots,
        prompt,
    )
    return decision, fingerprint


def _translate(exc: Exception, message: str) -> Exception:
    if isinstance(exc, V2RepositoryNotFound):
        return V2NotFoundError("V2 Project, Current Change, or Recovery Case not found.")
    if isinstance(exc, (V2RepositoryConflict, V2RepositoryInvalidState)):
        return V2ConflictError(message)
    return exc


async def record_symptom(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: RecoverySymptomRequest,
) -> RecoveryCommandResponse:
    change = await repo.get_current_change_by_id(owner, project_id, change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    prompt = investigation_prompt(change, request.observed_symptom)
    risk, fingerprint = _risk(change, prompt)
    try:
        current, recovery, replayed = await repo.record_recovery_symptom(
            owner, project_id, change_id, request.recovery_case_id,
            request.expected_current_change_version, request.command_id,
            request.observed_symptom, request.last_known_working_statement,
            request.last_known_working_certainty, prompt, risk.mode.value,
            risk.reason_key, v2_teaching_service.RISK_POLICY_VERSION, fingerprint,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The Recovery symptom changed or was already recorded.") from exc
    return RecoveryCommandResponse(
        current_change=current_change_view(current), recovery_case=recovery_view(recovery),
        replayed=replayed,
    )


async def accept_recovery_prompt(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: RecoveryPromptAcceptanceRequest,
) -> RecoveryCommandResponse:
    change = await repo.get_current_change_by_id(owner, project_id, change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    recovery = await repo.get_active_recovery_case(owner, project_id, change_id)
    if recovery is None or recovery.id != request.recovery_case_id:
        raise V2NotFoundError("Active Recovery Case not found.")
    purpose = PromptPurpose(request.purpose)
    status_matches_purpose = (
        (recovery.status is RecoveryStatus.INVESTIGATING and purpose is PromptPurpose.DIAGNOSTIC)
        or (recovery.status is RecoveryStatus.CORRECTING and purpose is PromptPurpose.CORRECTION)
    )
    if not status_matches_purpose or not v2_teaching_service.risk_is_fresh(change):
        raise V2ConflictError("The Recovery prompt is not ready or its risk state is stale.")
    try:
        current, prompt, replayed = await repo.accept_recovery_prompt(
            owner, project_id, change_id, recovery.id, purpose.value,
            request.expected_current_change_version,
            request.expected_prompt_draft_version, request.command_id,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The Recovery prompt changed or cannot be accepted.") from exc
    return RecoveryCommandResponse(
        current_change=current_change_view(current), recovery_case=recovery_view(recovery),
        prompt_version=prompt_version_view(prompt), exact_prompt=prompt.content,
        replayed=replayed,
    )


async def handoff_recovery_prompt(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: RecoveryPromptHandoffRequest,
) -> RecoveryCommandResponse:
    change = await repo.get_current_change_by_id(owner, project_id, change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    recovery = await repo.get_active_recovery_case(owner, project_id, change_id)
    if recovery is None or recovery.id != request.recovery_case_id:
        raise V2NotFoundError("Active Recovery Case not found.")
    try:
        current, prompt, replayed = await repo.handoff_recovery_prompt(
            owner, project_id, change_id, recovery.id, request.prompt_version_id,
            request.expected_current_change_version, request.expected_prompt_version,
            request.command_id,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The Recovery prompt changed or cannot be handed off.") from exc
    return RecoveryCommandResponse(
        current_change=current_change_view(current), recovery_case=recovery_view(recovery),
        prompt_version=prompt_version_view(prompt), exact_prompt=prompt.content,
        replayed=replayed,
    )


async def record_investigation_return(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: RecoveryInvestigationReturnRequest,
) -> RecoveryCommandResponse:
    normalized = " ".join(request.finding.lower().split()).strip(".! ")
    if (
        normalized in {"fixed it", "the ai fixed it", "it fixed it", "it works", "done"}
        or (len(normalized) < 80 and "fixed it" in normalized)
    ):
        raise V2ConflictError(
            "Record what the investigation found in the code or behavior, not a claim that it was fixed."
        )
    change = await repo.get_current_change_by_id(owner, project_id, change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    recovery = await repo.get_active_recovery_case(owner, project_id, change_id)
    if recovery is None or recovery.id != request.recovery_case_id:
        raise V2NotFoundError("Active Recovery Case not found.")
    prompt = correction_prompt(change, recovery, request.finding)
    summary = f"Target the smallest correction supported by this finding: {request.finding}"
    risk, fingerprint = _risk(change, prompt)
    try:
        current, updated, replayed = await repo.record_recovery_investigation_return(
            owner, project_id, change_id, recovery.id,
            request.expected_current_change_version, request.command_id,
            request.finding, summary[:16384], prompt, risk.mode.value,
            risk.reason_key, v2_teaching_service.RISK_POLICY_VERSION, fingerprint,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The investigation return changed or cannot be recorded.") from exc
    return RecoveryCommandResponse(
        current_change=current_change_view(current), recovery_case=recovery_view(updated),
        replayed=replayed,
    )


async def record_correction_return(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: RecoveryCorrectionReturnRequest,
) -> RecoveryCommandResponse:
    change = await repo.get_current_change_by_id(owner, project_id, change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    recovery = await repo.get_active_recovery_case(owner, project_id, change_id)
    if recovery is None or recovery.id != request.recovery_case_id:
        raise V2NotFoundError("Active Recovery Case not found.")
    plan = change.done_condition_snapshot or (
        f"Try the original behavior again and observe whether this still happens: "
        f"{recovery.observed_symptom}"
    )
    try:
        current, updated, check, replayed = await repo.record_recovery_correction_return(
            owner, project_id, change_id, recovery.id,
            request.expected_current_change_version, request.command_id,
            request.check_id, plan,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The correction return changed or cannot begin a recheck.") from exc
    return RecoveryCommandResponse(
        current_change=current_change_view(current), recovery_case=recovery_view(updated),
        check=check_view(check), replayed=replayed,
    )


async def record_recheck(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    check_id: UUID, request: RecoveryCheckRequest,
) -> RecoveryCommandResponse:
    change = await repo.get_current_change_by_id(owner, project_id, change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    recovery = await repo.get_active_recovery_case(owner, project_id, change_id)
    if recovery is None or recovery.id != request.recovery_case_id:
        raise V2NotFoundError("Active Recovery Case not found.")
    prompt = None
    risk = None
    fingerprint = None
    if request.result in {CheckResult.DID_NOT_WORK, CheckResult.PARTLY_WORKED}:
        prompt = investigation_prompt(
            change, recovery.observed_symptom, prior_observation=request.observation
        )
        risk, fingerprint = _risk(change, prompt)
    try:
        current, updated, check, next_check, replayed = await repo.record_recovery_check(
            owner, project_id, change_id, recovery.id, check_id,
            request.expected_current_change_version, request.expected_check_version,
            request.command_id, request.result.value, request.observation,
            request.performed_by_student, request.next_check_id, prompt,
            risk.mode.value if risk else None, risk.reason_key if risk else None,
            v2_teaching_service.RISK_POLICY_VERSION if risk else None, fingerprint,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The Recovery recheck changed or could not be recorded.") from exc
    return RecoveryCommandResponse(
        current_change=current_change_view(current), recovery_case=recovery_view(updated),
        check=check_view(check), next_check=check_view(next_check), replayed=replayed,
    )
