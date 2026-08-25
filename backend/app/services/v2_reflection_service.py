"""Read-only Learning and History projections from durable V2 truth."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from app.domain.v2 import CheckResult, CurrentChangeState, RecoveryStatus, V2LearnerEvidence
from app.schemas.v2 import (
    HistoryChangeView,
    HistoryCheckView,
    HistoryPromptView,
    HistoryRecoveryView,
    HistoryResponse,
    LearningCompetencyView,
    LearningEvidenceView,
    LearningResponse,
)
from app.services.v2_errors import V2NotFoundError
from app.services.v2_repository import V2Repository
from app.services.v2_teaching_policy import (
    Elicitation,
    EvidenceObservation,
    LearnerStatus,
    SupportLevel,
    derive_learner_status,
)


RECENT_EVIDENCE_LIMIT = 3
HISTORY_CHECK_LIMIT = 50
HISTORY_PROMPT_LIMIT = 20
HISTORY_RECOVERY_LIMIT = 10
TRANSFER_QUESTION = (
    "If you were doing your next change without Codize, what would you do differently "
    "before or after asking the AI to code it?"
)


@dataclass(frozen=True, slots=True)
class CompetencyDefinition:
    name: str
    description: str


# This is the Phase 5 teaching-target allowlist, presented in student language.
COMPETENCIES: dict[str, CompetencyDefinition] = {
    "define_done": CompetencyDefinition(
        "Defining what done looks like",
        "Turn a change into an observable result you can try afterward.",
    ),
    "protect_working_behavior": CompetencyDefinition(
        "Protecting what already works",
        "Name the behavior a focused AI change should leave alone.",
    ),
    "data_ownership": CompetencyDefinition(
        "Thinking about access boundaries",
        "Describe what an intended user may do and what another user must not do.",
    ),
    "effort_selection": CompetencyDefinition(
        "Choosing appropriate AI effort",
        "Match the coding agent's effort to the change's size, uncertainty, and risk.",
    ),
    "testing": CompetencyDefinition(
        "Checking whether AI code works",
        "Try an observable check yourself instead of treating an agent claim as proof.",
    ),
    "causal_explanation": CompetencyDefinition(
        "Understanding cause and effect",
        "Explain the important relationship that makes a behavior happen.",
    ),
    "debugging": CompetencyDefinition(
        "Investigating before patching",
        "Separate what you observed from a possible cause, then narrow the problem.",
    ),
}


def _observation(item: V2LearnerEvidence) -> EvidenceObservation:
    return EvidenceObservation(
        competency_key=item.competency_key,
        elicitation=Elicitation(item.elicitation),
        support_level=SupportLevel(item.support_level.value),
        observed_at=item.observed_at,
        source_current_change_id=(
            str(item.source_current_change_id) if item.source_current_change_id else None
        ),
        status=item.status,
    )


def _support_explanation(item: V2LearnerEvidence) -> str:
    if item.support_level.value == SupportLevel.TEACH.value or item.elicitation == Elicitation.TAUGHT.value:
        return "Codize gave you direct teaching for this example."
    if item.support_level.value in {SupportLevel.NUDGE.value, SupportLevel.CLUE.value} or item.elicitation == Elicitation.AFTER_HINT.value:
        return "You completed this after using a hint."
    if item.elicitation == Elicitation.SPONTANEOUS.value:
        return "You handled this without Codize giving you the answer first."
    return "You worked this out after Codize asked you to think it through."


def _status_explanation(status: LearnerStatus) -> tuple[str, str]:
    if status is LearnerStatus.GUIDED:
        return (
            "Your latest example used Codize support, so Codize will keep offering more help here.",
            "more",
        )
    if status is LearnerStatus.PRACTICED:
        return (
            "You have handled this with less support. Codize will still ask you to make the judgment.",
            "less",
        )
    return (
        "You handled recent examples without Codize giving you the answer first, so Codize can stay quieter here.",
        "less",
    )


async def get_learning(
    repo: V2Repository, owner_user_id: str, project_id: UUID,
) -> LearningResponse:
    project = await repo.get_project(owner_user_id, project_id)
    if project is None:
        raise V2NotFoundError("V2 Project not found.")

    evidence = await repo.list_learner_evidence(owner_user_id, list(COMPETENCIES))
    relevant = [item for item in evidence if item.competency_key in COMPETENCIES]
    by_key: dict[str, list[V2LearnerEvidence]] = defaultdict(list)
    for item in relevant:
        by_key[item.competency_key].append(item)

    projects = {item.ref.project_id: item for item in await repo.list_projects(owner_user_id)}
    context_pairs = list({
        (item.source_project_id, item.source_current_change_id)
        for items in by_key.values()
        for item in sorted(items, key=lambda value: (value.observed_at, value.id), reverse=True)[
            :RECENT_EVIDENCE_LIMIT
        ]
        if item.source_project_id is not None and item.source_current_change_id is not None
    })
    context_results = await asyncio.gather(
        *(
            repo.get_current_change_by_id(owner_user_id, source_project_id, change_id)
            for source_project_id, change_id in context_pairs
        )
    )
    changes = {
        pair: change for pair, change in zip(context_pairs, context_results, strict=True)
        if change is not None
    }

    competencies: list[LearningCompetencyView] = []
    for key, definition in COMPETENCIES.items():
        items = by_key.get(key, [])
        if not items:
            continue
        status = derive_learner_status((_observation(item) for item in items), key)
        explanation, direction = _status_explanation(status)
        recent = sorted(
            items, key=lambda value: (value.observed_at, value.id), reverse=True
        )[:RECENT_EVIDENCE_LIMIT]
        competencies.append(
            LearningCompetencyView(
                key=key,
                name=definition.name,
                description=definition.description,
                status=status.value,
                status_explanation=explanation,
                support_direction=direction,
                recent_evidence=[
                    LearningEvidenceView(
                        observed_behavior=item.observed_behavior,
                        support_explanation=_support_explanation(item),
                        observed_at=item.observed_at,
                        project_name=(
                            projects[item.source_project_id].display_name
                            if item.source_project_id in projects else None
                        ),
                        current_change_goal=(
                            changes[(item.source_project_id, item.source_current_change_id)].goal_snapshot
                            if (item.source_project_id, item.source_current_change_id) in changes
                            else None
                        ),
                    )
                    for item in recent
                ],
            )
        )
    return LearningResponse(
        project_id=project_id,
        competencies=competencies,
        recent_evidence_limit=RECENT_EVIDENCE_LIMIT,
    )


def _history_status(change, recoveries) -> str:
    if change.lifecycle_state is CurrentChangeState.COMPLETED:
        return "completed_after_recovery" if recoveries else "completed"
    if change.lifecycle_state is CurrentChangeState.CANCELLED:
        return "cancelled"
    if change.lifecycle_state is CurrentChangeState.RECOVERING:
        return "recovering"
    return "active"


def _completion_summary(change, final_check, recoveries) -> str:
    if change.lifecycle_state is CurrentChangeState.COMPLETED:
        if final_check and final_check.result:
            outcome = {
                "worked": "The final student-performed check passed.",
                "partly_worked": "The final student-performed check partly worked.",
                "did_not_work": "The final student-performed check failed.",
                "unsure": "The final student-performed check was unsure.",
            }[final_check.result.value]
            prefix = "Completed after recovery." if recoveries else "Completed."
            return f"{prefix} {outcome}"
        return "Completed without enough stored Check detail to claim exactly what code changed."
    if change.lifecycle_state is CurrentChangeState.CANCELLED:
        return "Cancelled before completion."
    if change.lifecycle_state is CurrentChangeState.RECOVERING:
        return "Recovery is in progress; this change is not complete."
    return "This change is still in progress."


async def _history_change(repo: V2Repository, owner: str, project_id: UUID, change):
    (
        (checks, checks_truncated),
        (prompts, prompts_truncated),
        (recoveries, recoveries_truncated),
        final_check,
    ) = await asyncio.gather(
        repo.list_history_checks(
            owner, project_id, change.id, limit=HISTORY_CHECK_LIMIT
        ),
        repo.list_history_prompt_versions(
            owner, project_id, change.id, limit=HISTORY_PROMPT_LIMIT
        ),
        repo.list_history_recovery_cases(
            owner, project_id, change.id, limit=HISTORY_RECOVERY_LIMIT
        ),
        (
            repo.get_latest_history_performed_check(owner, project_id, change.id)
            if change.lifecycle_state is CurrentChangeState.COMPLETED
            else asyncio.sleep(0, result=None)
        ),
    )
    check_sequence = {check.id: index for index, check in enumerate(checks, start=1)}
    checks_by_id = {check.id: check for check in checks}
    return HistoryChangeView(
        id=change.id,
        goal=change.goal_snapshot,
        done_condition=change.done_condition_snapshot,
        status=_history_status(change, recoveries),
        lifecycle_state=change.lifecycle_state,
        started_at=change.created_at,
        completed_at=change.completed_at,
        cancelled_at=change.cancelled_at,
        completion_summary=_completion_summary(change, final_check, recoveries),
        prompts=[
            HistoryPromptView(
                id=prompt.id,
                ordinal=prompt.ordinal,
                purpose=prompt.purpose,
                content=prompt.content,
                coding_agent_key=prompt.coding_agent_key,
                effort_category=prompt.effort_category,
                accepted_at=prompt.accepted_at,
                handed_off_at=prompt.handed_off_at,
            )
            for prompt in prompts
        ],
        prompts_truncated=prompts_truncated,
        checks=[
            HistoryCheckView(
                sequence=index,
                relationship=(
                    "retry_after_unsure"
                    if check.supersedes_check_id in checks_by_id
                    and checks_by_id[check.supersedes_check_id].result is CheckResult.UNSURE
                    else "follow_up" if check.supersedes_check_id is not None
                    else "initial"
                ),
                supersedes_sequence=check_sequence.get(check.supersedes_check_id),
                check_plan=check.check_plan,
                plan_source=check.plan_source,
                status=check.status,
                result=check.result,
                student_observation=check.student_observation,
                created_at=check.created_at,
                performed_at=check.performed_at,
                not_run_at=check.not_run_at,
            )
            for index, check in enumerate(checks, start=1)
        ],
        checks_truncated=checks_truncated,
        recoveries=[
            HistoryRecoveryView(
                episode_number=index,
                status=recovery.status,
                observed_symptom=recovery.observed_symptom,
                opened_at=recovery.opened_at,
                investigation_finding=recovery.investigation_finding,
                investigation_finding_provenance=(
                    "agent_claimed" if recovery.investigation_finding else None
                ),
                correction_summary=recovery.correction_summary,
                resolution_summary=recovery.resolution_summary,
                resolved_at=recovery.resolved_at,
                recheck_state=(
                    "pending" if recovery.status is RecoveryStatus.RECHECKING
                    else "completed" if recovery.status is RecoveryStatus.RESOLVED
                    else None
                ),
            )
            for index, recovery in enumerate(recoveries, start=1)
        ],
        recoveries_truncated=recoveries_truncated,
    )


async def get_history(
    repo: V2Repository, owner_user_id: str, project_id: UUID, *, limit: int, offset: int,
) -> HistoryResponse:
    project = await repo.get_project(owner_user_id, project_id)
    if project is None:
        raise V2NotFoundError("V2 Project not found.")
    changes, has_more = await repo.list_history_changes(
        owner_user_id, project_id, limit=limit, offset=offset
    )
    views = await asyncio.gather(
        *(_history_change(repo, owner_user_id, project_id, change) for change in changes)
    )
    return HistoryResponse(
        project_id=project_id,
        project_name=project.display_name,
        project_created_at=project.created_at,
        changes=list(views),
        limit=limit,
        offset=offset,
        has_more=has_more,
        next_offset=offset + len(changes) if has_more else None,
        transfer_question=(
            TRANSFER_QUESTION
            if any(change.lifecycle_state is CurrentChangeState.COMPLETED for change in changes)
            else None
        ),
    )
