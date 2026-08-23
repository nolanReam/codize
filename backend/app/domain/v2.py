"""Deterministic Codize V2 project and manual Build-loop domain types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID


class WorkflowVersion(StrEnum):
    V1 = "v1"
    V2 = "v2"


class ProjectCreationIntent(StrEnum):
    NEW_IDEA = "new_idea"
    ALREADY_BUILDING = "already_building"
    RECOVERY_FIRST = "recovery_first"


class ProjectLifecycle(StrEnum):
    DRAFT = "draft"
    TEMPORARY_RECOVERY = "temporary_recovery"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETION_PENDING = "deletion_pending"


class SetupResumeStep(StrEnum):
    IDEA_CAPTURE = "idea_capture"
    FIRST_VERSION_SHAPING = "first_version_shaping"
    GUIDED_RESISTANCE = "guided_resistance"
    PLAN_PROPOSAL = "plan_proposal"
    EXISTING_PROJECT_CONTEXT = "existing_project_context"
    RECOVERY_CONTEXT = "recovery_context"
    READY = "ready"


class PlanScopeBand(StrEnum):
    FIRST_VERSION = "first_version"
    LATER = "later"


class PlanItemStatus(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    DEFERRED = "deferred"
    DONE = "done"
    REMOVED = "removed"


class CurrentChangeKind(StrEnum):
    BUILD = "build"
    RECOVERY = "recovery"


class CurrentChangeState(StrEnum):
    PREPARING = "preparing"
    AWAITING_AGENT = "awaiting_agent"
    REVIEWING = "reviewing"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResumeStep(StrEnum):
    CONFIRM_CHANGE = "confirm_change"
    CHOOSE_AGENT = "choose_agent"
    INTERVENTION = "intervention"
    PROMPT = "prompt"
    EFFORT = "effort"
    RETURN_OUTCOME = "return_outcome"
    CHECK = "check"
    INSPECT = "inspect"
    UNDERSTAND = "understand"
    RECOVERY_SYMPTOM = "recovery_symptom"
    RECOVERY_INVESTIGATE = "recovery_investigate"
    RECOVERY_CORRECT = "recovery_correct"
    RECOVERY_RECHECK = "recovery_recheck"


class CodingAgentKey(StrEnum):
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    CURSOR = "cursor"
    CHATGPT = "chatgpt"
    REPLIT = "replit"
    OTHER = "other"


class EffortCategory(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class PromptPurpose(StrEnum):
    FEATURE = "feature"
    DIAGNOSTIC = "diagnostic"
    CORRECTION = "correction"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class GenerationPurpose(StrEnum):
    SETUP_SUMMARY = "setup_summary"
    FIRST_VERSION_PROPOSAL = "first_version_proposal"
    PLAN_PROPOSAL = "plan_proposal"
    INTERVENTION_COPY = "intervention_copy"
    PROMPT_DRAFT = "prompt_draft"
    RECOVERY_SUMMARY = "recovery_summary"
    DIAGNOSTIC_PROMPT = "diagnostic_prompt"
    CORRECTION_PROMPT = "correction_prompt"
    CONCEPT_EXPLANATION = "concept_explanation"
    PROJECT_ANSWER = "project_answer"


class BuildStage(StrEnum):
    CHOOSE_AGENT = "choose_agent"
    EDIT_PROMPT = "edit_prompt"
    CHOOSE_EFFORT = "choose_effort"
    REVIEW_PROMPT = "review_prompt"
    READY_TO_HANDOFF = "ready_to_handoff"
    WAITING_FOR_RETURN = "waiting_for_return"


NONTERMINAL_STATES = frozenset(
    {
        CurrentChangeState.PREPARING,
        CurrentChangeState.AWAITING_AGENT,
        CurrentChangeState.REVIEWING,
        CurrentChangeState.RECOVERING,
    }
)

_LEGAL_TRANSITIONS = MappingProxyType(
    {
        CurrentChangeState.PREPARING: frozenset(
            {
                CurrentChangeState.PREPARING,
                CurrentChangeState.AWAITING_AGENT,
                CurrentChangeState.CANCELLED,
            }
        ),
        CurrentChangeState.AWAITING_AGENT: frozenset(
            {
                CurrentChangeState.REVIEWING,
                CurrentChangeState.RECOVERING,
                CurrentChangeState.CANCELLED,
            }
        ),
        CurrentChangeState.REVIEWING: frozenset(
            {
                CurrentChangeState.REVIEWING,
                CurrentChangeState.RECOVERING,
                CurrentChangeState.COMPLETED,
                CurrentChangeState.CANCELLED,
            }
        ),
        CurrentChangeState.RECOVERING: frozenset(
            {
                CurrentChangeState.RECOVERING,
                CurrentChangeState.AWAITING_AGENT,
                CurrentChangeState.REVIEWING,
                CurrentChangeState.COMPLETED,
                CurrentChangeState.CANCELLED,
            }
        ),
        CurrentChangeState.COMPLETED: frozenset(),
        CurrentChangeState.CANCELLED: frozenset(),
    }
)

_RESUME_STEPS = MappingProxyType(
    {
        CurrentChangeState.PREPARING: frozenset(
            {
                ResumeStep.CONFIRM_CHANGE,
                ResumeStep.CHOOSE_AGENT,
                ResumeStep.INTERVENTION,
                ResumeStep.PROMPT,
                ResumeStep.EFFORT,
            }
        ),
        CurrentChangeState.AWAITING_AGENT: frozenset({ResumeStep.RETURN_OUTCOME}),
        CurrentChangeState.REVIEWING: frozenset(
            {
                ResumeStep.RETURN_OUTCOME,
                ResumeStep.CHECK,
                ResumeStep.INSPECT,
                ResumeStep.UNDERSTAND,
            }
        ),
        CurrentChangeState.RECOVERING: frozenset(
            {
                ResumeStep.RECOVERY_SYMPTOM,
                ResumeStep.RECOVERY_INVESTIGATE,
                ResumeStep.RECOVERY_CORRECT,
                ResumeStep.RECOVERY_RECHECK,
            }
        ),
        CurrentChangeState.COMPLETED: frozenset(),
        CurrentChangeState.CANCELLED: frozenset(),
    }
)


class WrongWorkflowVersionError(ValueError):
    """A V1 reference was offered to a V2-only application service."""


class IllegalCurrentChangeTransitionError(ValueError):
    """A command attempted a noncanonical lifecycle or resume transition."""


@dataclass(frozen=True, slots=True)
class ProjectRef:
    workflow_version: WorkflowVersion
    project_id: UUID

    def require_v2(self) -> None:
        if self.workflow_version is not WorkflowVersion.V2:
            raise WrongWorkflowVersionError("A V2 operation requires a V2 Project reference.")


@dataclass(frozen=True, slots=True)
class V2Project:
    ref: ProjectRef
    display_name: str
    lifecycle_state: ProjectLifecycle
    setup_resume_step: SetupResumeStep
    plan_version: int
    version: int
    coding_agent_key: str | None
    first_version_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class V2PlanItem:
    id: UUID
    project_id: UUID
    label: str
    intended_outcome: str
    scope_band: PlanScopeBand
    status: PlanItemStatus
    order_key: int
    version: int
    completed_at: datetime | None
    terminal_current_change_id: UUID | None


@dataclass(frozen=True, slots=True)
class V2Plan:
    project_ref: ProjectRef
    project_version: int
    plan_version: int
    items: tuple[V2PlanItem, ...]
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class V2CurrentChange:
    id: UUID
    project_ref: ProjectRef
    plan_item_id: UUID | None
    change_kind: CurrentChangeKind
    lifecycle_state: CurrentChangeState
    resume_step: ResumeStep | None
    goal_snapshot: str
    done_condition_snapshot: str | None
    boundary_snapshots: tuple[str, ...]
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_command_id: UUID | None
    cancellation_reason_key: str | None
    prompt_draft: str | None = None
    prompt_draft_version: int = 1
    coding_agent_key: CodingAgentKey | None = None
    effort_category: EffortCategory | None = None
    latest_prompt_version_id: UUID | None = None
    teaching_policy_version: str = "unresolved-v0"
    risk_policy_version: str = "unresolved-v0"
    handoff_command_id: UUID | None = None

    @property
    def policy_is_resolved(self) -> bool:
        return (
            self.teaching_policy_version != "unresolved-v0"
            and self.risk_policy_version != "unresolved-v0"
        )


@dataclass(frozen=True, slots=True)
class V2PromptVersion:
    id: UUID
    project_ref: ProjectRef
    current_change_id: UUID
    ordinal: int
    purpose: PromptPurpose
    content: str
    content_sha256: str
    input_current_change_version: int
    input_goal_snapshot: str | None
    input_done_condition_snapshot: str | None
    input_boundary_snapshots: tuple[str, ...] | None
    generation_attempt_id: UUID | None
    coding_agent_key: CodingAgentKey
    effort_category: EffortCategory | None
    provider_mapping_key: str | None
    provider_mapping_version: str | None
    accepted_at: datetime
    handed_off_at: datetime | None
    version: int


@dataclass(frozen=True, slots=True)
class V2GenerationAttempt:
    id: UUID
    project_ref: ProjectRef
    target_current_change_id: UUID | None
    target_recovery_case_id: UUID | None
    purpose: GenerationPurpose
    target_aggregate_version: int
    policy_version: str | None
    config_version: str
    status: GenerationStatus
    provider_key: str
    model_key: str
    input_sha256: str
    safe_error_category: str | None
    retryable: bool | None
    result_record_type: str | None
    result_record_id: UUID | None
    started_at: datetime
    completed_at: datetime | None
    version: int


def allowed_transitions(state: CurrentChangeState) -> frozenset[CurrentChangeState]:
    return _LEGAL_TRANSITIONS[state]


def validate_resume_state(
    state: CurrentChangeState,
    resume_step: ResumeStep | None,
) -> None:
    allowed = _RESUME_STEPS[state]
    if state in NONTERMINAL_STATES:
        if resume_step is None or resume_step not in allowed:
            raise IllegalCurrentChangeTransitionError(
                f"Resume step {resume_step!s} is not legal for {state.value}."
            )
    elif resume_step is not None:
        raise IllegalCurrentChangeTransitionError(
            f"Terminal state {state.value} cannot have a resume step."
        )


def validate_transition(
    current_state: CurrentChangeState,
    target_state: CurrentChangeState,
    target_resume_step: ResumeStep | None,
) -> None:
    if target_state not in _LEGAL_TRANSITIONS[current_state]:
        raise IllegalCurrentChangeTransitionError(
            f"Transition {current_state.value} -> {target_state.value} is not legal."
        )
    validate_resume_state(target_state, target_resume_step)


def validate_cancellation(change: V2CurrentChange, command_id: UUID) -> None:
    if (
        change.lifecycle_state is CurrentChangeState.CANCELLED
        and change.cancellation_command_id == command_id
    ):
        return
    validate_transition(
        change.lifecycle_state,
        CurrentChangeState.CANCELLED,
        None,
    )
