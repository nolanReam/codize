"""Owner-scoped persistence boundary for the separate Codize V2 domain.

V2 table reads use the backend credential and always constrain both owner and
explicit Project ID. Mutations use only reviewed PostgreSQL RPCs; the backend
credential has no direct V2 table-write grants.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings, get_settings
from app.domain.v2 import (
    CodingAgentKey,
    CheckResult,
    CurrentChangeKind,
    CurrentChangeState,
    EffortCategory,
    GenerationPurpose,
    GenerationStatus,
    PlanItemStatus,
    PlanScopeBand,
    ProjectLifecycle,
    ProjectRef,
    PromptPurpose,
    RecoveryStatus,
    RiskMode,
    ResumeStep,
    SetupResumeStep,
    SupportLevel,
    TeachingMode,
    V2CurrentChange,
    V2Check,
    V2GenerationAttempt,
    V2LearnerEvidence,
    V2Plan,
    V2PlanItem,
    V2Project,
    V2SetupDraft,
    V2RecentChange,
    V2PromptVersion,
    V2RecoveryCase,
    V2TeachingProgress,
    V2UserPreferences,
    WorkflowVersion,
    validate_resume_state,
)

_TIMEOUT = 10.0
_PROJECT_SELECT = (
    "id,owner_user_id,workflow_version,display_name,lifecycle_state,"
    "setup_resume_step,setup_draft,coding_agent_key,plan_version,first_version_completed_at,"
    "version,created_at,updated_at"
)
_PLAN_ITEM_SELECT = (
    "id,project_id,owner_user_id,label,intended_outcome,scope_band,status,"
    "order_key,completed_at,terminal_current_change_id,version"
)
_CURRENT_CHANGE_SELECT = (
    "id,project_id,owner_user_id,plan_item_id,change_kind,lifecycle_state,"
    "resume_step,goal_snapshot,done_condition_snapshot,boundary_snapshots,"
    "prompt_draft,prompt_draft_version,coding_agent_key,effort_category,"
    "latest_prompt_version_id,teaching_mode,teaching_target,teaching_policy_version,"
    "risk,risk_reason_key,risk_policy_version,risk_input_fingerprint,check_requirement,"
    "help_context_key,support_level_disclosed,"
    "handoff_command_id,student_return_outcome,accepted_outcome_summary,"
    "unresolved_uncertainty_summary,"
    "version,created_at,updated_at,completed_at,cancelled_at,"
    "cancellation_command_id,cancellation_reason_key"
)
_LEARNER_EVIDENCE_SELECT = (
    "id,competency_key,observed_behavior,elicitation,support_level,context_key,"
    "source_project_id,source_current_change_id,observed_at,status"
)
_CHECK_SELECT = (
    "id,project_id,owner_user_id,current_change_id,check_plan,plan_source,status,result,"
    "student_observation,performed_at,not_run_at,supersedes_check_id,created_at,version"
)
_RECOVERY_SELECT = (
    "id,project_id,owner_user_id,current_change_id,status,intended_behavior,"
    "observed_symptom,last_known_working_statement,last_known_working_certainty,"
    "candidate_change_summary,student_hypothesis,proposed_first_check,"
    "investigation_finding,cause_summary,correction_summary,resolution_summary,"
    "opened_at,resolved_at,version"
)
_PREFERENCE_SELECT = (
    "owner_user_id,dialogue_sound_enabled,motion_preference,version"
)
_PROMPT_VERSION_SELECT = (
    "id,project_id,owner_user_id,current_change_id,ordinal,purpose,content,"
    "content_sha256,input_current_change_version,generation_attempt_id,"
    "input_goal_snapshot,input_done_condition_snapshot,input_boundary_snapshots,"
    "coding_agent_key,effort_category,provider_mapping_key,"
    "provider_mapping_version,accepted_at,handed_off_at,version"
)
_GENERATION_ATTEMPT_SELECT = (
    "id,project_id,owner_user_id,target_current_change_id,"
    "target_recovery_case_id,purpose,target_aggregate_version,policy_version,"
    "config_version,status,provider_key,model_key,input_sha256,"
    "safe_error_category,retryable,result_record_type,result_record_id,"
    "started_at,completed_at,version"
)
_TURN_PROGRESS_SELECT = "turn_kind,structured_payload,help_context_key,support_level"
_CHECK_PLAN_COMMAND_SELECT = (
    "id,project_id,current_change_id,turn_kind,speaker,content,structured_payload,"
    "related_record_type,related_record_id,support_level"
)


class V2RepositoryError(RuntimeError):
    """Unexpected or unavailable persistence behavior; safe details stay server-side."""


class V2RepositoryNotFound(V2RepositoryError):
    """Absent, deleted, and other-owner identifiers share this outcome."""


class V2RepositoryConflict(V2RepositoryError):
    """Optimistic version, uniqueness, or retry identity conflict."""


class V2RepositoryInvalidState(V2RepositoryError):
    """The database rejected a malformed or illegal domain command."""


class _ProjectRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    owner_user_id: UUID
    workflow_version: WorkflowVersion
    display_name: str
    lifecycle_state: ProjectLifecycle
    setup_resume_step: SetupResumeStep
    setup_draft: dict[str, Any] | None = None
    coding_agent_key: str | None
    plan_version: int = Field(gt=0)
    first_version_completed_at: datetime | None
    version: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime


class _PlanItemRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    project_id: UUID
    owner_user_id: UUID
    label: str
    intended_outcome: str
    scope_band: PlanScopeBand
    status: PlanItemStatus
    order_key: int
    completed_at: datetime | None = None
    terminal_current_change_id: UUID | None = None
    version: int = Field(gt=0)


class _CurrentChangeRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    project_id: UUID
    owner_user_id: UUID
    plan_item_id: UUID | None
    change_kind: CurrentChangeKind
    lifecycle_state: CurrentChangeState
    resume_step: ResumeStep | None
    goal_snapshot: str
    done_condition_snapshot: str | None
    boundary_snapshots: list[str]
    prompt_draft: str | None = None
    prompt_draft_version: int = Field(default=1, gt=0)
    coding_agent_key: CodingAgentKey | None = None
    effort_category: EffortCategory | None = None
    latest_prompt_version_id: UUID | None = None
    teaching_mode: TeachingMode = TeachingMode.SKIP
    teaching_target: str | None = None
    teaching_policy_version: str = "unresolved-v0"
    risk: RiskMode = RiskMode.NORMAL
    risk_reason_key: str | None = None
    risk_policy_version: str = "unresolved-v0"
    risk_input_fingerprint: str | None = None
    check_requirement: str = "required"
    help_context_key: str | None = None
    support_level_disclosed: SupportLevel = SupportLevel.NONE
    handoff_command_id: UUID | None = None
    student_return_outcome: str | None = None
    accepted_outcome_summary: str | None = None
    unresolved_uncertainty_summary: str | None = None
    version: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_command_id: UUID | None
    cancellation_reason_key: str | None


class _PromptVersionRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    project_id: UUID
    owner_user_id: UUID
    current_change_id: UUID
    ordinal: int = Field(gt=0)
    purpose: PromptPurpose
    content: str
    content_sha256: str
    input_current_change_version: int = Field(gt=0)
    input_goal_snapshot: str | None
    input_done_condition_snapshot: str | None
    input_boundary_snapshots: list[str] | None
    generation_attempt_id: UUID | None
    coding_agent_key: CodingAgentKey
    effort_category: EffortCategory | None
    provider_mapping_key: str | None
    provider_mapping_version: str | None
    accepted_at: datetime
    handed_off_at: datetime | None
    version: int = Field(gt=0)


class _GenerationAttemptRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    project_id: UUID
    owner_user_id: UUID
    target_current_change_id: UUID | None
    target_recovery_case_id: UUID | None
    purpose: GenerationPurpose
    target_aggregate_version: int = Field(gt=0)
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
    version: int = Field(gt=0)


class _CheckRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    project_id: UUID
    owner_user_id: UUID
    current_change_id: UUID
    check_plan: str
    plan_source: str
    status: str
    result: CheckResult | None = None
    student_observation: str | None = None
    performed_at: datetime | None = None
    not_run_at: datetime | None = None
    supersedes_check_id: UUID | None = None
    created_at: datetime
    version: int = Field(gt=0)


class _RecoveryRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    project_id: UUID
    owner_user_id: UUID
    current_change_id: UUID
    status: RecoveryStatus
    intended_behavior: str
    observed_symptom: str
    last_known_working_statement: str | None = None
    last_known_working_certainty: str
    candidate_change_summary: str | None = None
    student_hypothesis: str | None = None
    proposed_first_check: str | None = None
    investigation_finding: str | None = None
    cause_summary: str | None = None
    correction_summary: str | None = None
    resolution_summary: str | None = None
    opened_at: datetime
    resolved_at: datetime | None = None
    version: int = Field(gt=0)


class _PreferenceRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    owner_user_id: UUID
    dialogue_sound_enabled: bool
    motion_preference: str
    version: int = Field(gt=0)


class _LearnerEvidenceRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    competency_key: str
    observed_behavior: str
    elicitation: str
    support_level: SupportLevel
    context_key: str
    source_project_id: UUID | None
    source_current_change_id: UUID | None
    observed_at: datetime
    status: str


class V2Repository(Protocol):
    async def save_setup_draft(
        self, owner_user_id: str, project_id: UUID, expected_project_version: int,
        command_id: UUID, project_context: str, initial_change_label: str,
        done_condition: str,
    ) -> tuple[V2Project, bool]: ...

    async def establish_manual_project(
        self, owner_user_id: str, project_id: UUID, expected_project_version: int,
        command_id: UUID, project_context: str, plan_item_id: UUID,
        change_label: str, done_condition: str,
    ) -> tuple[V2Project, V2PlanItem, bool]: ...

    async def create_project(
        self,
        owner_user_id: str,
        command_id: UUID,
        display_name: str,
        creation_intent: str,
        recovery_context: dict[str, Any] | None,
        current_change_command_id: UUID | None,
    ) -> tuple[V2Project, bool]: ...

    async def get_project(self, owner_user_id: str, project_id: UUID) -> V2Project | None: ...

    async def list_projects(self, owner_user_id: str) -> list[V2Project]: ...
    async def list_recent_changes(
        self, owner_user_id: str, project_id: UUID,
    ) -> list[V2RecentChange]: ...

    async def promote_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
    ) -> tuple[V2Project, bool]: ...

    async def purge_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
    ) -> bool: ...

    async def get_plan(self, owner_user_id: str, project_id: UUID) -> V2Plan | None: ...

    async def mutate_plan(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        expected_plan_version: int,
        command_id: UUID,
        operations: list[dict[str, Any]],
        expected_current_change_version: int | None,
        linked_item_action: str | None,
        cancellation_command_id: UUID | None,
        cancellation_reason_key: str | None,
    ) -> V2Plan: ...

    async def start_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
        plan_item_id: UUID | None,
        change_kind: str,
        goal_snapshot: str,
    ) -> tuple[V2CurrentChange, bool]: ...

    async def confirm_manual_current_change(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID,
    ) -> tuple[V2CurrentChange, bool]: ...

    async def list_learner_evidence(
        self, owner_user_id: str, competency_keys: list[str] | None = None,
    ) -> list[V2LearnerEvidence]: ...

    async def resolve_teaching_policy(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID,
        decision: dict[str, Any],
    ) -> tuple[V2CurrentChange, bool]: ...

    async def get_teaching_progress(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2TeachingProgress: ...

    async def disclose_teaching_help(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, context: str,
    ) -> tuple[V2CurrentChange, bool]: ...

    async def record_teaching_response(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, context: str,
        response: str, elicitation: str, support_level: str,
    ) -> tuple[V2CurrentChange, bool]: ...

    async def record_effort_attempt(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, selected: str,
        recommended: str, appropriate: bool,
    ) -> tuple[V2CurrentChange, dict[str, Any], bool]: ...

    async def get_student_check_plan_replay(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        command_id: UUID, check_id: UUID, check_plan: str,
    ) -> tuple[V2CurrentChange, V2Check] | None: ...

    async def create_student_check_plan(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, check_id: UUID,
        check_plan: str, elicitation: str, support_level: str,
    ) -> tuple[V2CurrentChange, V2Check, bool]: ...

    async def record_manual_return(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID,
        outcome: str, check_id: UUID | None,
    ) -> tuple[V2CurrentChange, V2Check | None, bool]: ...

    async def record_manual_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        check_id: UUID, expected_current_change_version: int,
        expected_check_version: int, command_id: UUID, result: str,
        observation: str, performed_by_student: bool, next_check_id: UUID | None,
    ) -> tuple[V2CurrentChange, V2Check, V2Check | None, bool]: ...

    async def get_latest_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2Check | None: ...

    async def get_active_recovery_case(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2RecoveryCase | None: ...

    async def record_recovery_symptom(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, expected_current_change_version: int,
        command_id: UUID, observed_symptom: str,
        last_known_working_statement: str | None,
        last_known_working_certainty: str, investigation_prompt: str,
        risk: str, risk_reason_key: str | None, risk_policy_version: str,
        risk_input_fingerprint: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, bool]: ...

    async def accept_recovery_prompt(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, purpose: str,
        expected_current_change_version: int, expected_prompt_draft_version: int,
        acceptance_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]: ...

    async def handoff_recovery_prompt(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, prompt_version_id: UUID,
        expected_current_change_version: int, expected_prompt_version: int,
        handoff_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]: ...

    async def record_recovery_investigation_return(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, expected_current_change_version: int,
        command_id: UUID, finding: str, correction_summary: str,
        correction_prompt: str, risk: str, risk_reason_key: str | None,
        risk_policy_version: str, risk_input_fingerprint: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, bool]: ...

    async def record_recovery_correction_return(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, expected_current_change_version: int,
        command_id: UUID, check_id: UUID, check_plan: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, V2Check, bool]: ...

    async def record_recovery_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, check_id: UUID,
        expected_current_change_version: int, expected_check_version: int,
        command_id: UUID, result: str, observation: str,
        performed_by_student: bool, next_check_id: UUID | None,
        investigation_prompt: str | None, risk: str | None,
        risk_reason_key: str | None, risk_policy_version: str | None,
        risk_input_fingerprint: str | None,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, V2Check, V2Check | None, bool]: ...

    async def complete_manual_change(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, expected_plan_version: int,
        expected_plan_item_version: int, command_id: UUID,
        check: V2Check,
    ) -> bool: ...

    async def get_preferences(self, owner_user_id: str) -> V2UserPreferences: ...
    async def update_dialogue_sound(
        self, owner_user_id: str, expected_version: int, enabled: bool,
    ) -> V2UserPreferences: ...

    async def get_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
    ) -> V2CurrentChange | None: ...

    async def get_current_change_by_id(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
    ) -> V2CurrentChange | None: ...

    async def list_history_changes(
        self, owner_user_id: str, project_id: UUID, *, limit: int, offset: int,
    ) -> tuple[list[V2CurrentChange], bool]: ...

    async def list_history_checks(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        *, limit: int,
    ) -> tuple[list[V2Check], bool]: ...

    async def get_latest_history_performed_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2Check | None: ...

    async def list_history_prompt_versions(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        *, limit: int,
    ) -> tuple[list[V2PromptVersion], bool]: ...

    async def list_history_recovery_cases(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        *, limit: int,
    ) -> tuple[list[V2RecoveryCase], bool]: ...

    async def cancel_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        cancellation_command_id: UUID,
        cancellation_reason_key: str,
    ) -> tuple[V2CurrentChange, bool]: ...

    async def update_coding_agent(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_project_version: int,
        expected_current_change_version: int,
        coding_agent_key: str,
    ) -> tuple[V2Project, V2CurrentChange]: ...

    async def update_prompt_draft(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        prompt_text: str,
        done_condition: str | None,
        boundaries: list[str],
        risk: str,
        risk_reason_key: str | None,
        risk_policy_version: str,
        risk_input_fingerprint: str,
    ) -> V2CurrentChange: ...

    async def update_effort(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        effort_category: str,
    ) -> V2CurrentChange: ...

    async def accept_prompt_version(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        acceptance_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]: ...

    async def handoff_prompt_version(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        prompt_version_id: UUID,
        expected_current_change_version: int,
        expected_prompt_version: int,
        handoff_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]: ...

    async def list_prompt_versions(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
    ) -> list[V2PromptVersion]: ...

    async def start_generation_attempt(
        self,
        owner_user_id: str,
        project_id: UUID,
        payload: dict[str, Any],
    ) -> tuple[V2GenerationAttempt, bool]: ...

    async def finish_generation_attempt(
        self,
        owner_user_id: str,
        project_id: UUID,
        generation_attempt_id: UUID,
        payload: dict[str, Any],
    ) -> V2GenerationAttempt: ...

    async def apply_generated_prompt_draft(
        self,
        owner_user_id: str,
        project_id: UUID,
        generation_attempt_id: UUID,
        expected_attempt_version: int,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        prompt_text: str,
        done_condition: str | None,
        boundaries: list[str],
    ) -> tuple[V2GenerationAttempt, V2CurrentChange, bool, bool]: ...


def _project_from_row(raw: Any, *, expected_owner: str | None = None) -> V2Project:
    try:
        row = _ProjectRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Project row") from exc
    if row.workflow_version is not WorkflowVersion.V2:
        raise V2RepositoryError("database returned a non-V2 Project from v2_projects")
    if expected_owner is not None and str(row.owner_user_id) != expected_owner:
        raise V2RepositoryError("database returned a V2 Project for the wrong owner")
    if not row.display_name.strip():
        raise V2RepositoryError("database returned a blank V2 Project name")
    setup_draft = None
    if row.setup_draft is not None:
        draft_values: list[str] = []
        for key, maximum in (
            ("project_context", 8192),
            ("initial_change_label", 200),
            ("done_condition", 4096),
        ):
            value = row.setup_draft.get(key, "")
            if not isinstance(value, str) or len(value.encode("utf-8")) > maximum:
                raise V2RepositoryError("database returned a malformed V2 setup draft")
            draft_values.append(value)
        if any(draft_values):
            setup_draft = V2SetupDraft(*draft_values)
    return V2Project(
        ref=ProjectRef(WorkflowVersion.V2, row.id),
        display_name=row.display_name,
        lifecycle_state=row.lifecycle_state,
        setup_resume_step=row.setup_resume_step,
        plan_version=row.plan_version,
        version=row.version,
        coding_agent_key=row.coding_agent_key,
        first_version_completed_at=row.first_version_completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        setup_draft=setup_draft,
    )


def _plan_item_from_row(
    raw: Any,
    *,
    expected_owner: str,
    expected_project_id: UUID,
) -> V2PlanItem:
    try:
        row = _PlanItemRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Plan Item row") from exc
    if str(row.owner_user_id) != expected_owner or row.project_id != expected_project_id:
        raise V2RepositoryError("database returned a V2 Plan Item outside the owned Project")
    if row.status is PlanItemStatus.REMOVED:
        raise V2RepositoryError("ordinary V2 Plan projection included a removed item")
    if row.order_key <= 0:
        raise V2RepositoryError("ordinary V2 Plan projection included an invalid order")
    if (
        row.status is PlanItemStatus.DONE
        and row.completed_at is None
        or row.status is not PlanItemStatus.DONE
        and (row.completed_at is not None or row.terminal_current_change_id is not None)
    ):
        raise V2RepositoryError("database returned inconsistent V2 Plan Item terminal state")
    return V2PlanItem(
        id=row.id,
        project_id=row.project_id,
        label=row.label,
        intended_outcome=row.intended_outcome,
        scope_band=row.scope_band,
        status=row.status,
        order_key=row.order_key,
        version=row.version,
        completed_at=row.completed_at,
        terminal_current_change_id=row.terminal_current_change_id,
    )


def _current_change_from_row(
    raw: Any,
    *,
    expected_owner: str,
    expected_project_id: UUID,
) -> V2CurrentChange:
    try:
        row = _CurrentChangeRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Current Change row") from exc
    if str(row.owner_user_id) != expected_owner or row.project_id != expected_project_id:
        raise V2RepositoryError("database returned a V2 Current Change outside the owned Project")
    if not row.goal_snapshot.strip() or any(not value.strip() for value in row.boundary_snapshots):
        raise V2RepositoryError("database returned malformed V2 Current Change snapshots")
    try:
        validate_resume_state(row.lifecycle_state, row.resume_step)
    except ValueError as exc:
        raise V2RepositoryError("database returned an illegal V2 Current Change resume state") from exc
    if row.lifecycle_state is CurrentChangeState.COMPLETED:
        timestamps_are_valid = row.completed_at is not None and row.cancelled_at is None
        cancellation_is_valid = (
            row.cancellation_command_id is None and row.cancellation_reason_key is None
        )
    elif row.lifecycle_state is CurrentChangeState.CANCELLED:
        timestamps_are_valid = row.completed_at is None and row.cancelled_at is not None
        cancellation_is_valid = (
            row.cancellation_command_id is not None
            and row.cancellation_reason_key is not None
            and bool(row.cancellation_reason_key.strip())
        )
    else:
        timestamps_are_valid = row.completed_at is None and row.cancelled_at is None
        cancellation_is_valid = (
            row.cancellation_command_id is None and row.cancellation_reason_key is None
        )
    if not timestamps_are_valid or not cancellation_is_valid:
        raise V2RepositoryError("database returned inconsistent V2 Current Change terminal state")
    return V2CurrentChange(
        id=row.id,
        project_ref=ProjectRef(WorkflowVersion.V2, row.project_id),
        plan_item_id=row.plan_item_id,
        change_kind=row.change_kind,
        lifecycle_state=row.lifecycle_state,
        resume_step=row.resume_step,
        goal_snapshot=row.goal_snapshot,
        done_condition_snapshot=row.done_condition_snapshot,
        boundary_snapshots=tuple(row.boundary_snapshots),
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
        cancelled_at=row.cancelled_at,
        cancellation_command_id=row.cancellation_command_id,
        cancellation_reason_key=row.cancellation_reason_key,
        prompt_draft=row.prompt_draft,
        prompt_draft_version=row.prompt_draft_version,
        coding_agent_key=row.coding_agent_key,
        effort_category=row.effort_category,
        latest_prompt_version_id=row.latest_prompt_version_id,
        teaching_mode=row.teaching_mode,
        teaching_target=row.teaching_target,
        teaching_policy_version=row.teaching_policy_version,
        risk=row.risk,
        risk_reason_key=row.risk_reason_key,
        risk_policy_version=row.risk_policy_version,
        risk_input_fingerprint=row.risk_input_fingerprint,
        check_requirement=row.check_requirement,
        help_context_key=row.help_context_key,
        support_level_disclosed=row.support_level_disclosed,
        handoff_command_id=row.handoff_command_id,
        student_return_outcome=row.student_return_outcome,
        accepted_outcome_summary=row.accepted_outcome_summary,
        unresolved_uncertainty_summary=row.unresolved_uncertainty_summary,
    )


def _check_from_row(raw: Any, *, expected_owner: str, expected_project_id: UUID) -> V2Check:
    try:
        row = _CheckRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Check row") from exc
    if str(row.owner_user_id) != expected_owner or row.project_id != expected_project_id:
        raise V2RepositoryError("database returned a Check outside the owned Project")
    return V2Check(
        id=row.id, project_id=row.project_id, current_change_id=row.current_change_id,
        check_plan=row.check_plan, plan_source=row.plan_source, status=row.status, result=row.result,
        student_observation=row.student_observation, performed_at=row.performed_at,
        not_run_at=row.not_run_at, supersedes_check_id=row.supersedes_check_id,
        created_at=row.created_at,
        version=row.version,
    )


def _recovery_from_row(
    raw: Any, *, expected_owner: str, expected_project_id: UUID,
    expected_current_change_id: UUID | None = None,
) -> V2RecoveryCase:
    try:
        row = _RecoveryRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Recovery Case row") from exc
    if str(row.owner_user_id) != expected_owner or row.project_id != expected_project_id:
        raise V2RepositoryError("database returned a Recovery Case outside the owned Project")
    if (expected_current_change_id is not None
            and row.current_change_id != expected_current_change_id):
        raise V2RepositoryError("database returned a Recovery Case for the wrong Current Change")
    return V2RecoveryCase(
        id=row.id, project_id=row.project_id, current_change_id=row.current_change_id,
        status=row.status, intended_behavior=row.intended_behavior,
        observed_symptom=row.observed_symptom,
        last_known_working_statement=row.last_known_working_statement,
        last_known_working_certainty=row.last_known_working_certainty,
        candidate_change_summary=row.candidate_change_summary,
        student_hypothesis=row.student_hypothesis,
        proposed_first_check=row.proposed_first_check,
        investigation_finding=row.investigation_finding,
        cause_summary=row.cause_summary,
        correction_summary=row.correction_summary,
        resolution_summary=row.resolution_summary,
        opened_at=row.opened_at, resolved_at=row.resolved_at, version=row.version,
    )


def _preference_from_row(raw: Any, *, expected_owner: str) -> V2UserPreferences:
    try:
        row = _PreferenceRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 preferences row") from exc
    if str(row.owner_user_id) != expected_owner:
        raise V2RepositoryError("database returned preferences for the wrong owner")
    return V2UserPreferences(
        dialogue_sound_enabled=row.dialogue_sound_enabled,
        motion_preference=row.motion_preference,
        version=row.version,
    )


def _learner_evidence_from_row(raw: Any) -> V2LearnerEvidence:
    try:
        row = _LearnerEvidenceRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Learner Evidence row") from exc
    return V2LearnerEvidence(
        id=row.id,
        competency_key=row.competency_key,
        observed_behavior=row.observed_behavior,
        elicitation=row.elicitation,
        support_level=row.support_level,
        context_key=row.context_key,
        source_project_id=row.source_project_id,
        source_current_change_id=row.source_current_change_id,
        observed_at=row.observed_at,
        status=row.status,
    )


def _prompt_version_from_row(
    raw: Any,
    *,
    expected_owner: str,
    expected_project_id: UUID,
    expected_current_change_id: UUID,
) -> V2PromptVersion:
    try:
        row = _PromptVersionRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Prompt Version row") from exc
    if (
        str(row.owner_user_id) != expected_owner
        or row.project_id != expected_project_id
        or row.current_change_id != expected_current_change_id
    ):
        raise V2RepositoryError("database returned a V2 Prompt Version outside the owned change")
    if not row.content.strip():
        raise V2RepositoryError("database returned a blank V2 Prompt Version")
    return V2PromptVersion(
        id=row.id,
        project_ref=ProjectRef(WorkflowVersion.V2, row.project_id),
        current_change_id=row.current_change_id,
        ordinal=row.ordinal,
        purpose=row.purpose,
        content=row.content,
        content_sha256=row.content_sha256,
        input_current_change_version=row.input_current_change_version,
        input_goal_snapshot=row.input_goal_snapshot,
        input_done_condition_snapshot=row.input_done_condition_snapshot,
        input_boundary_snapshots=(
            tuple(row.input_boundary_snapshots)
            if row.input_boundary_snapshots is not None
            else None
        ),
        generation_attempt_id=row.generation_attempt_id,
        coding_agent_key=row.coding_agent_key,
        effort_category=row.effort_category,
        provider_mapping_key=row.provider_mapping_key,
        provider_mapping_version=row.provider_mapping_version,
        accepted_at=row.accepted_at,
        handed_off_at=row.handed_off_at,
        version=row.version,
    )


def _generation_attempt_from_row(
    raw: Any,
    *,
    expected_owner: str,
    expected_project_id: UUID,
) -> V2GenerationAttempt:
    try:
        row = _GenerationAttemptRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Generation Attempt row") from exc
    if str(row.owner_user_id) != expected_owner or row.project_id != expected_project_id:
        raise V2RepositoryError("database returned a Generation Attempt outside the owned Project")
    return V2GenerationAttempt(
        id=row.id,
        project_ref=ProjectRef(WorkflowVersion.V2, row.project_id),
        target_current_change_id=row.target_current_change_id,
        target_recovery_case_id=row.target_recovery_case_id,
        purpose=row.purpose,
        target_aggregate_version=row.target_aggregate_version,
        policy_version=row.policy_version,
        config_version=row.config_version,
        status=row.status,
        provider_key=row.provider_key,
        model_key=row.model_key,
        input_sha256=row.input_sha256,
        safe_error_category=row.safe_error_category,
        retryable=row.retryable,
        result_record_type=row.result_record_type,
        result_record_id=row.result_record_id,
        started_at=row.started_at,
        completed_at=row.completed_at,
        version=row.version,
    )


class SupabaseV2Repository:
    def __init__(self, settings: Settings) -> None:
        self._base = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        key = settings.supabase_service_role_key.get_secret_value()
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.request(
                    method,
                    f"{self._base}{path}",
                    params=params or {},
                    json=body,
                    headers=self._headers,
                )
        except httpx.RequestError as exc:
            raise V2RepositoryError("V2 persistence request failed") from exc

        if response.is_error:
            code = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    code = payload.get("code")
            except ValueError:
                pass
            if code == "P0002":
                raise V2RepositoryNotFound("owned V2 resource not found")
            if code in {"40001", "23505"}:
                raise V2RepositoryConflict("V2 command conflicted")
            if code in {"22023", "22P02", "23514"}:
                raise V2RepositoryInvalidState("V2 command was invalid for current state")
            raise V2RepositoryError("V2 persistence returned an unexpected error")

        try:
            return response.json()
        except ValueError as exc:
            raise V2RepositoryError("V2 persistence returned malformed JSON") from exc

    async def _rpc(self, name: str, body: dict[str, Any]) -> Any:
        return await self._request("POST", f"/rpc/{name}", body=body)

    @staticmethod
    def _object(value: Any, context: str) -> dict[str, Any]:
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
            value = value[0]
        if not isinstance(value, dict):
            raise V2RepositoryError(f"{context} returned a malformed object")
        return value

    async def save_setup_draft(
        self, owner_user_id: str, project_id: UUID, expected_project_version: int,
        command_id: UUID, project_context: str, initial_change_label: str,
        done_condition: str,
    ) -> tuple[V2Project, bool]:
        payload = self._object(await self._rpc("save_v2_setup_draft", {
            "p_owner_user_id": owner_user_id,
            "p_project_id": str(project_id),
            "p_expected_project_version": expected_project_version,
            "p_command_id": str(command_id),
            "p_project_context": project_context,
            "p_initial_change_label": initial_change_label,
            "p_done_condition": done_condition,
        }), "save_v2_setup_draft")
        replayed = payload.get("replayed")
        if not isinstance(replayed, bool):
            raise V2RepositoryError("setup draft save omitted replay state")
        return _project_from_row(
            payload.get("project"), expected_owner=owner_user_id
        ), replayed

    async def establish_manual_project(
        self, owner_user_id: str, project_id: UUID, expected_project_version: int,
        command_id: UUID, project_context: str, plan_item_id: UUID,
        change_label: str, done_condition: str,
    ) -> tuple[V2Project, V2PlanItem, bool]:
        payload = self._object(await self._rpc("establish_v2_manual_project", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_expected_project_version": expected_project_version,
            "p_command_id": str(command_id), "p_project_context": project_context,
            "p_plan_item_id": str(plan_item_id), "p_change_label": change_label,
            "p_done_condition": done_condition,
        }), "establish_v2_manual_project")
        replayed = payload.get("replayed")
        if not isinstance(replayed, bool):
            raise V2RepositoryError("manual setup omitted replay state")
        return (
            _project_from_row(payload.get("project"), expected_owner=owner_user_id),
            _plan_item_from_row(payload.get("plan_item"), expected_owner=owner_user_id,
                                expected_project_id=project_id), replayed,
        )

    async def create_project(
        self,
        owner_user_id: str,
        command_id: UUID,
        display_name: str,
        creation_intent: str,
        recovery_context: dict[str, Any] | None,
        current_change_command_id: UUID | None,
    ) -> tuple[V2Project, bool]:
        payload = self._object(
            await self._rpc(
                "create_v2_project",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_create_command_id": str(command_id),
                    "p_display_name": display_name,
                    "p_creation_intent": creation_intent,
                    "p_recovery_context": recovery_context,
                    "p_current_change_command_id": (
                        str(current_change_command_id)
                        if current_change_command_id is not None
                        else None
                    ),
                },
            ),
            "create_v2_project",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("create_v2_project omitted replay state")
        return (
            _project_from_row(payload.get("project"), expected_owner=owner_user_id),
            payload["replayed"],
        )

    async def get_project(self, owner_user_id: str, project_id: UUID) -> V2Project | None:
        rows = await self._request(
            "GET",
            "/v2_projects",
            params={
                "select": _PROJECT_SELECT,
                "id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "workflow_version": "eq.v2",
                "lifecycle_state": "neq.deletion_pending",
                "limit": "1",
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 Project read returned malformed rows")
        if not rows:
            return None
        if len(rows) != 1:
            raise V2RepositoryError("explicit V2 Project read returned multiple rows")
        return _project_from_row(rows[0], expected_owner=owner_user_id)

    async def list_projects(self, owner_user_id: str) -> list[V2Project]:
        rows = await self._request(
            "GET",
            "/v2_projects",
            params={
                "select": _PROJECT_SELECT,
                "owner_user_id": f"eq.{owner_user_id}",
                "workflow_version": "eq.v2",
                "lifecycle_state": "neq.deletion_pending",
                "order": "updated_at.desc,id.asc",
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 Project list returned malformed rows")
        return [_project_from_row(row, expected_owner=owner_user_id) for row in rows]

    async def list_recent_changes(
        self, owner_user_id: str, project_id: UUID,
    ) -> list[V2RecentChange]:
        rows = await self._request("GET", "/v2_current_changes", params={
            "select": _CURRENT_CHANGE_SELECT, "owner_user_id": f"eq.{owner_user_id}",
            "project_id": f"eq.{project_id}", "lifecycle_state": "eq.completed",
            "order": "completed_at.desc,id.desc", "limit": "3",
        })
        if not isinstance(rows, list):
            raise V2RepositoryError("recent V2 Current Change read returned malformed rows")
        result: list[V2RecentChange] = []
        for raw in rows:
            change = _current_change_from_row(raw, expected_owner=owner_user_id,
                                              expected_project_id=project_id)
            check_rows = await self._request("GET", "/v2_checks", params={
                "select": _CHECK_SELECT, "owner_user_id": f"eq.{owner_user_id}",
                "project_id": f"eq.{project_id}", "current_change_id": f"eq.{change.id}",
                "status": "eq.performed", "result": "in.(worked,partly_worked)",
                "order": "performed_at.desc,id.desc", "limit": "1",
            })
            if not isinstance(check_rows, list) or len(check_rows) > 1:
                raise V2RepositoryError("recent V2 Check read returned malformed rows")
            if not check_rows or change.completed_at is None:
                continue
            check = _check_from_row(check_rows[0], expected_owner=owner_user_id,
                                    expected_project_id=project_id)
            if not check.student_observation:
                continue
            result.append(V2RecentChange(change.id, change.goal_snapshot,
                change.completed_at, check.check_plan, check.student_observation))
        return result

    async def promote_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
    ) -> tuple[V2Project, bool]:
        payload = self._object(
            await self._rpc(
                "promote_v2_temporary_project",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_expected_project_version": expected_project_version,
                    "p_command_id": str(command_id),
                },
            ),
            "promote_v2_temporary_project",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("Project promotion omitted replay state")
        return (
            _project_from_row(payload.get("project"), expected_owner=owner_user_id),
            payload["replayed"],
        )

    async def purge_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
    ) -> bool:
        result = await self._rpc(
            "purge_v2_project",
            {
                "p_owner_user_id": owner_user_id,
                "p_project_id": str(project_id),
                "p_expected_project_version": expected_project_version,
                "p_purge_kind": "temporary_recovery",
                "p_evidence_actions": [],
            },
        )
        if isinstance(result, list) and len(result) == 1:
            result = result[0]
        if result is not True:
            raise V2RepositoryError("temporary V2 Project purge returned malformed success")
        return True

    async def get_plan(self, owner_user_id: str, project_id: UUID) -> V2Plan | None:
        # PostgREST does not give two separate HTTP reads one shared snapshot.
        # Re-read the root version and retry once so a mixed Plan is never
        # returned as current.
        for _ in range(2):
            project = await self.get_project(owner_user_id, project_id)
            if project is None:
                return None
            rows = await self._request(
                "GET",
                "/v2_plan_items",
                params={
                    "select": _PLAN_ITEM_SELECT,
                    "project_id": f"eq.{project_id}",
                    "owner_user_id": f"eq.{owner_user_id}",
                    "status": "neq.removed",
                    "order": "scope_band.asc,order_key.asc,id.asc",
                },
            )
            if not isinstance(rows, list):
                raise V2RepositoryError("V2 Plan read returned malformed rows")
            current = await self.get_project(owner_user_id, project_id)
            if current is None:
                return None
            if (
                current.version == project.version
                and current.plan_version == project.plan_version
            ):
                return V2Plan(
                    project_ref=project.ref,
                    project_version=project.version,
                    plan_version=project.plan_version,
                    items=tuple(
                        _plan_item_from_row(
                            row,
                            expected_owner=owner_user_id,
                            expected_project_id=project_id,
                        )
                        for row in rows
                    ),
                )
        raise V2RepositoryConflict("V2 Plan changed while it was being read")

    async def mutate_plan(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        expected_plan_version: int,
        command_id: UUID,
        operations: list[dict[str, Any]],
        expected_current_change_version: int | None,
        linked_item_action: str | None,
        cancellation_command_id: UUID | None,
        cancellation_reason_key: str | None,
    ) -> V2Plan:
        payload = self._object(
            await self._rpc(
                "mutate_v2_plan",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_expected_project_version": expected_project_version,
                    "p_expected_plan_version": expected_plan_version,
                    "p_command_id": str(command_id),
                    "p_operations": operations,
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_linked_item_action": linked_item_action,
                    "p_cancellation_command_id": (
                        str(cancellation_command_id) if cancellation_command_id else None
                    ),
                    "p_cancellation_reason_key": cancellation_reason_key,
                },
            ),
            "mutate_v2_plan",
        )
        try:
            returned_project_id = UUID(str(payload["project_id"]))
            project_version = int(payload["project_version"])
            plan_version = int(payload["plan_version"])
            replayed = payload["replayed"]
            item_rows = payload["items"]
        except (KeyError, TypeError, ValueError) as exc:
            raise V2RepositoryError("mutate_v2_plan returned a malformed result") from exc
        if (
            returned_project_id != project_id
            or project_version <= 0
            or plan_version <= 0
            or not isinstance(replayed, bool)
            or not isinstance(item_rows, list)
        ):
            raise V2RepositoryError("mutate_v2_plan returned inconsistent identity or shape")
        return V2Plan(
            project_ref=ProjectRef(WorkflowVersion.V2, project_id),
            project_version=project_version,
            plan_version=plan_version,
            items=tuple(
                _plan_item_from_row(
                    row,
                    expected_owner=owner_user_id,
                    expected_project_id=project_id,
                )
                for row in item_rows
            ),
            replayed=replayed,
        )

    async def start_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
        plan_item_id: UUID | None,
        change_kind: str,
        goal_snapshot: str,
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(
            await self._rpc(
                "start_v2_current_change",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_expected_project_version": expected_project_version,
                    "p_create_command_id": str(command_id),
                    "p_plan_item_id": str(plan_item_id) if plan_item_id else None,
                    "p_change_kind": change_kind,
                    "p_goal_snapshot": goal_snapshot,
                },
            ),
            "start_v2_current_change",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("Current Change start omitted replay state")
        return (
            _current_change_from_row(
                payload.get("current_change"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            payload["replayed"],
        )

    async def confirm_manual_current_change(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID,
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(await self._rpc("confirm_v2_manual_current_change", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id),
        }), "confirm_v2_manual_current_change")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                bool(payload.get("replayed")))

    async def list_learner_evidence(
        self, owner_user_id: str, competency_keys: list[str] | None = None,
    ) -> list[V2LearnerEvidence]:
        params: dict[str, str] = {
            "select": _LEARNER_EVIDENCE_SELECT,
            "owner_user_id": f"eq.{owner_user_id}",
            "status": "eq.active",
            "order": "observed_at.asc,id.asc",
        }
        if competency_keys:
            params["competency_key"] = f"in.({','.join(competency_keys)})"
        rows = await self._request("GET", "/v2_learner_evidence", params=params)
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 Learner Evidence read returned malformed rows")
        return [_learner_evidence_from_row(row) for row in rows]

    async def resolve_teaching_policy(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID,
        decision: dict[str, Any],
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(await self._rpc("resolve_v2_current_change_policy", {
            "p_owner_user_id": owner_user_id,
            "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id),
            "p_teaching_mode": decision["mode"],
            "p_teaching_target": decision.get("target"),
            "p_teaching_reason_key": decision["reason_key"],
            "p_teaching_policy_version": decision["teaching_policy_version"],
            "p_risk": decision["risk"],
            "p_risk_reason_key": decision.get("risk_reason_key"),
            "p_risk_policy_version": decision["risk_policy_version"],
            "p_check_requirement": decision["check_requirement"],
            "p_check_waiver_reason_key": None,
        }), "resolve_v2_current_change_policy")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                bool(payload.get("replayed")))

    async def get_teaching_progress(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2TeachingProgress:
        rows = await self._request("GET", "/v2_build_turns", params={
            "select": _TURN_PROGRESS_SELECT,
            "owner_user_id": f"eq.{owner_user_id}", "project_id": f"eq.{project_id}",
            "current_change_id": f"eq.{current_change_id}",
            "turn_kind": "in.(student_answer,student_decision,help_nudge,help_clue,help_teach)",
            "order": "sequence_no.asc",
        })
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 teaching progress returned malformed rows")
        attempts: list[str] = []
        feedback = None
        intervention_answered = check_answered = understanding_answered = False
        hint = SupportLevel.NONE
        for row in rows:
            payload = row.get("structured_payload") or {}
            context = payload.get("context")
            if row.get("support_level"):
                hint = SupportLevel(row["support_level"])
            if row.get("turn_kind") == "student_answer":
                intervention_answered |= context == "prebuild"
                check_answered |= context == "verification"
                understanding_answered |= context == "understanding"
            if row.get("turn_kind") == "student_decision" and context == "effort":
                attempts.append(str(payload.get("selected")))
                feedback = payload.get("message")
        return V2TeachingProgress(
            hint_level=hint, intervention_answered=intervention_answered,
            effort_attempts=tuple(attempts), effort_feedback=feedback,
            check_plan_answered=check_answered,
            understanding_answered=understanding_answered,
        )

    async def disclose_teaching_help(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, context: str,
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(await self._rpc("disclose_v2_teaching_help", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id), "p_context": context,
        }), "disclose_v2_teaching_help")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                bool(payload.get("replayed")))

    async def record_teaching_response(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, context: str,
        response: str, elicitation: str, support_level: str,
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(await self._rpc("record_v2_teaching_response", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id), "p_context": context,
            "p_response": response, "p_elicitation": elicitation,
            "p_support_level": support_level,
        }), "record_v2_teaching_response")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                bool(payload.get("replayed")))

    async def record_effort_attempt(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, selected: str,
        recommended: str, appropriate: bool,
    ) -> tuple[V2CurrentChange, dict[str, Any], bool]:
        payload = self._object(await self._rpc("record_v2_effort_attempt", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id), "p_selected": selected,
            "p_recommended": recommended, "p_appropriate": appropriate,
        }), "record_v2_effort_attempt")
        feedback = payload.get("feedback")
        if not isinstance(feedback, dict):
            raise V2RepositoryError("effort attempt omitted feedback")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                feedback, bool(payload.get("replayed")))

    async def create_student_check_plan(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID, check_id: UUID,
        check_plan: str, elicitation: str, support_level: str,
    ) -> tuple[V2CurrentChange, V2Check, bool]:
        payload = self._object(await self._rpc("create_v2_student_check_plan", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id), "p_check_id": str(check_id),
            "p_check_plan": check_plan, "p_elicitation": elicitation,
            "p_support_level": support_level,
        }), "create_v2_student_check_plan")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                _check_from_row(payload.get("check"), expected_owner=owner_user_id,
                                expected_project_id=project_id),
                bool(payload.get("replayed")))

    async def get_student_check_plan_replay(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        command_id: UUID, check_id: UUID, check_plan: str,
    ) -> tuple[V2CurrentChange, V2Check] | None:
        rows = await self._request("GET", "/v2_build_turns", params={
            "select": _CHECK_PLAN_COMMAND_SELECT,
            "owner_user_id": f"eq.{owner_user_id}", "id": f"eq.{command_id}",
            "limit": "1",
        })
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("student Check replay lookup returned malformed rows")
        if not rows:
            return None
        turn = rows[0]
        payload = turn.get("structured_payload")
        if (
            str(turn.get("project_id")) != str(project_id)
            or str(turn.get("current_change_id")) != str(current_change_id)
            or turn.get("turn_kind") != "student_answer"
            or turn.get("speaker") != "student"
            or turn.get("content") != check_plan.strip()
            or not isinstance(payload, dict)
            or payload.get("context") != "verification"
            or turn.get("related_record_type") != "check"
            or str(turn.get("related_record_id")) != str(check_id)
        ):
            raise V2RepositoryConflict("student Check command id already used")
        check_rows = await self._request("GET", "/v2_checks", params={
            "select": _CHECK_SELECT,
            "owner_user_id": f"eq.{owner_user_id}", "project_id": f"eq.{project_id}",
            "current_change_id": f"eq.{current_change_id}", "id": f"eq.{check_id}",
            "limit": "1",
        })
        if not isinstance(check_rows, list) or len(check_rows) != 1:
            raise V2RepositoryInvalidState("student Check replay source is missing")
        change = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        if change is None:
            raise V2RepositoryNotFound("owned V2 Current Change not found")
        return change, _check_from_row(
            check_rows[0], expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def record_manual_return(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, command_id: UUID,
        outcome: str, check_id: UUID | None,
    ) -> tuple[V2CurrentChange, V2Check | None, bool]:
        payload = self._object(await self._rpc("record_v2_manual_return", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id), "p_outcome": outcome,
            "p_check_id": str(check_id) if check_id else None,
        }), "record_v2_manual_return")
        raw_check = payload.get("check")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                _check_from_row(raw_check, expected_owner=owner_user_id,
                                expected_project_id=project_id) if raw_check else None,
                bool(payload.get("replayed")))

    async def record_manual_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        check_id: UUID, expected_current_change_version: int,
        expected_check_version: int, command_id: UUID, result: str,
        observation: str, performed_by_student: bool, next_check_id: UUID | None,
    ) -> tuple[V2CurrentChange, V2Check, V2Check | None, bool]:
        payload = self._object(await self._rpc("record_v2_manual_check", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id), "p_check_id": str(check_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_expected_check_version": expected_check_version,
            "p_command_id": str(command_id), "p_result": result,
            "p_observation": observation, "p_performed_by_student": performed_by_student,
            "p_next_check_id": str(next_check_id) if next_check_id else None,
        }), "record_v2_manual_check")
        raw_next = payload.get("next_check")
        return (_current_change_from_row(payload.get("current_change"),
                expected_owner=owner_user_id, expected_project_id=project_id),
                _check_from_row(payload.get("check"), expected_owner=owner_user_id,
                                expected_project_id=project_id),
                _check_from_row(raw_next, expected_owner=owner_user_id,
                                expected_project_id=project_id) if raw_next else None,
                bool(payload.get("replayed")))

    async def get_latest_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2Check | None:
        rows = await self._request("GET", "/v2_checks", params={
            "select": _CHECK_SELECT, "owner_user_id": f"eq.{owner_user_id}",
            "project_id": f"eq.{project_id}",
            "current_change_id": f"eq.{current_change_id}",
            "order": "created_at.desc,id.desc", "limit": "1",
        })
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("latest V2 Check read returned malformed rows")
        return (_check_from_row(rows[0], expected_owner=owner_user_id,
                expected_project_id=project_id) if rows else None)

    async def get_active_recovery_case(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2RecoveryCase | None:
        rows = await self._request("GET", "/v2_recovery_cases", params={
            "select": _RECOVERY_SELECT,
            "owner_user_id": f"eq.{owner_user_id}",
            "project_id": f"eq.{project_id}",
            "current_change_id": f"eq.{current_change_id}",
            "status": "in.(open,investigating,correcting,rechecking)",
            "limit": "1",
        })
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("active V2 Recovery read returned malformed rows")
        return (_recovery_from_row(
            rows[0], expected_owner=owner_user_id,
            expected_project_id=project_id,
            expected_current_change_id=current_change_id,
        ) if rows else None)

    def _recovery_payload(
        self, payload: dict[str, Any], *, owner_user_id: str,
        project_id: UUID, current_change_id: UUID,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, bool]:
        replayed = payload.get("replayed")
        if not isinstance(replayed, bool):
            raise V2RepositoryError("Recovery command omitted replay state")
        return (
            _current_change_from_row(
                payload.get("current_change"), expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            _recovery_from_row(
                payload.get("recovery_case"), expected_owner=owner_user_id,
                expected_project_id=project_id,
                expected_current_change_id=current_change_id,
            ),
            replayed,
        )

    async def record_recovery_symptom(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, expected_current_change_version: int,
        command_id: UUID, observed_symptom: str,
        last_known_working_statement: str | None,
        last_known_working_certainty: str, investigation_prompt: str,
        risk: str, risk_reason_key: str | None, risk_policy_version: str,
        risk_input_fingerprint: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, bool]:
        payload = self._object(await self._rpc("record_v2_recovery_symptom", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_recovery_case_id": str(recovery_case_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id), "p_observed_symptom": observed_symptom,
            "p_last_known_working_statement": last_known_working_statement,
            "p_last_known_working_certainty": last_known_working_certainty,
            "p_investigation_prompt": investigation_prompt, "p_risk": risk,
            "p_risk_reason_key": risk_reason_key,
            "p_risk_policy_version": risk_policy_version,
            "p_risk_input_fingerprint": risk_input_fingerprint,
        }), "record_v2_recovery_symptom")
        return self._recovery_payload(
            payload, owner_user_id=owner_user_id, project_id=project_id,
            current_change_id=current_change_id,
        )

    async def accept_recovery_prompt(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, purpose: str,
        expected_current_change_version: int, expected_prompt_draft_version: int,
        acceptance_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        change = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        recovery = await self.get_active_recovery_case(
            owner_user_id, project_id, current_change_id
        )
        if change is None or recovery is None or recovery.id != recovery_case_id:
            raise V2RepositoryNotFound("owned active Recovery Case not found")
        if change.prompt_draft is None or change.coding_agent_key is None:
            raise V2RepositoryInvalidState("Recovery prompt prerequisites are missing")
        content_hash = hashlib.sha256(change.prompt_draft.encode("utf-8")).hexdigest()
        payload = self._object(await self._rpc("accept_v2_prompt_version", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_expected_prompt_draft_version": expected_prompt_draft_version,
            "p_acceptance_command_id": str(acceptance_command_id),
            "p_purpose": purpose, "p_recovery_case_id": str(recovery_case_id),
            "p_content": change.prompt_draft, "p_content_sha256": content_hash,
            "p_generation_attempt_id": None,
            "p_coding_agent_key": change.coding_agent_key.value,
            "p_effort_category": (change.effort_category.value
                                   if change.effort_category else None),
            "p_provider_mapping_key": None, "p_provider_mapping_version": None,
        }), "accept_v2_prompt_version")
        try:
            prompt_version_id = UUID(str(payload["prompt_version_id"]))
            replayed = payload["replayed"]
        except (KeyError, TypeError, ValueError) as exc:
            raise V2RepositoryError("Recovery prompt acceptance returned malformed identity") from exc
        current = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        prompt = await self._get_prompt_version(
            owner_user_id, project_id, current_change_id, prompt_version_id
        )
        if current is None or prompt is None or not isinstance(replayed, bool):
            raise V2RepositoryError("accepted Recovery prompt could not be reloaded")
        return current, prompt, replayed

    async def handoff_recovery_prompt(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, prompt_version_id: UUID,
        expected_current_change_version: int, expected_prompt_version: int,
        handoff_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        payload = self._object(await self._rpc("handoff_v2_prompt_version", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_prompt_version_id": str(prompt_version_id),
            "p_recovery_case_id": str(recovery_case_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_expected_prompt_version": expected_prompt_version,
            "p_handoff_command_id": str(handoff_command_id),
        }), "handoff_v2_prompt_version")
        replayed = payload.get("replayed")
        current = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        prompt = await self._get_prompt_version(
            owner_user_id, project_id, current_change_id, prompt_version_id
        )
        if current is None or prompt is None or not isinstance(replayed, bool):
            raise V2RepositoryError("handed-off Recovery prompt could not be reloaded")
        return current, prompt, replayed

    async def record_recovery_investigation_return(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, expected_current_change_version: int,
        command_id: UUID, finding: str, correction_summary: str,
        correction_prompt: str, risk: str, risk_reason_key: str | None,
        risk_policy_version: str, risk_input_fingerprint: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, bool]:
        payload = self._object(await self._rpc(
            "record_v2_recovery_investigation_return", {
                "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
                "p_current_change_id": str(current_change_id),
                "p_recovery_case_id": str(recovery_case_id),
                "p_expected_current_change_version": expected_current_change_version,
                "p_command_id": str(command_id), "p_finding": finding,
                "p_correction_summary": correction_summary,
                "p_correction_prompt": correction_prompt, "p_risk": risk,
                "p_risk_reason_key": risk_reason_key,
                "p_risk_policy_version": risk_policy_version,
                "p_risk_input_fingerprint": risk_input_fingerprint,
            }), "record_v2_recovery_investigation_return")
        return self._recovery_payload(payload, owner_user_id=owner_user_id,
            project_id=project_id, current_change_id=current_change_id)

    async def record_recovery_correction_return(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, expected_current_change_version: int,
        command_id: UUID, check_id: UUID, check_plan: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, V2Check, bool]:
        payload = self._object(await self._rpc("record_v2_recovery_correction_return", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_recovery_case_id": str(recovery_case_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_command_id": str(command_id), "p_check_id": str(check_id),
            "p_check_plan": check_plan,
        }), "record_v2_recovery_correction_return")
        current, recovery, replayed = self._recovery_payload(
            payload, owner_user_id=owner_user_id, project_id=project_id,
            current_change_id=current_change_id)
        return current, recovery, _check_from_row(
            payload.get("check"), expected_owner=owner_user_id,
            expected_project_id=project_id), replayed

    async def record_recovery_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        recovery_case_id: UUID, check_id: UUID,
        expected_current_change_version: int, expected_check_version: int,
        command_id: UUID, result: str, observation: str,
        performed_by_student: bool, next_check_id: UUID | None,
        investigation_prompt: str | None, risk: str | None,
        risk_reason_key: str | None, risk_policy_version: str | None,
        risk_input_fingerprint: str | None,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, V2Check, V2Check | None, bool]:
        payload = self._object(await self._rpc("record_v2_recovery_check", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_recovery_case_id": str(recovery_case_id), "p_check_id": str(check_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_expected_check_version": expected_check_version,
            "p_command_id": str(command_id), "p_result": result,
            "p_observation": observation,
            "p_performed_by_student": performed_by_student,
            "p_next_check_id": str(next_check_id) if next_check_id else None,
            "p_investigation_prompt": investigation_prompt, "p_risk": risk,
            "p_risk_reason_key": risk_reason_key,
            "p_risk_policy_version": risk_policy_version,
            "p_risk_input_fingerprint": risk_input_fingerprint,
        }), "record_v2_recovery_check")
        current, recovery, replayed = self._recovery_payload(
            payload, owner_user_id=owner_user_id, project_id=project_id,
            current_change_id=current_change_id)
        raw_next = payload.get("next_check")
        return current, recovery, _check_from_row(
            payload.get("check"), expected_owner=owner_user_id,
            expected_project_id=project_id), (_check_from_row(
                raw_next, expected_owner=owner_user_id,
                expected_project_id=project_id) if raw_next else None), replayed

    async def complete_manual_change(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        expected_current_change_version: int, expected_plan_version: int,
        expected_plan_item_version: int, command_id: UUID, check: V2Check,
    ) -> bool:
        change = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        if change is None:
            raise V2RepositoryNotFound("owned V2 Current Change not found")
        observed_at = check.performed_at.isoformat() if check.performed_at else None
        check_plan_evidence = next(
            (
                item for item in reversed(
                    await self.list_learner_evidence(owner_user_id, ["testing"])
                )
                if item.source_current_change_id == current_change_id
            ),
            None,
        )
        if check.plan_source == "codize":
            evidence_elicitation = "taught"
            evidence_support = "teach"
        else:
            evidence_elicitation = (
                check_plan_evidence.elicitation if check_plan_evidence else "spontaneous"
            )
            evidence_support = (
                check_plan_evidence.support_level.value if check_plan_evidence else "none"
            )
        result = await self._rpc("complete_v2_current_change", {
            "p_owner_user_id": owner_user_id, "p_project_id": str(project_id),
            "p_current_change_id": str(current_change_id),
            "p_expected_current_change_version": expected_current_change_version,
            "p_expected_plan_version": expected_plan_version,
            "p_expected_plan_item_version": expected_plan_item_version,
            "p_completion_command_id": str(command_id),
            "p_complete_linked_plan_item": True,
            "p_accepted_outcome_summary": check.student_observation,
            "p_unresolved_uncertainty_summary": change.unresolved_uncertainty_summary,
            "p_fact_inputs": [{"fact_type": "known_working_behavior",
                "subject_key": f"change/{current_change_id}", "value_kind": "text",
                "value": check.student_observation, "source_kind": "student_observed",
                "source_record_type": "check", "source_record_id": str(check.id),
                "observed_at": observed_at}],
            "p_learner_evidence_inputs": [{
                "competency_key": "testing",
                "observed_behavior": (
                    "Proposed and performed a contextual Check for the current change."
                    if check.plan_source == "student"
                    else "Performed a contextual Check and recorded a personal observation."
                ),
                "elicitation": evidence_elicitation,
                "support_level": evidence_support,
                "context_key": "build",
                "source_record_type": "check", "source_record_id": str(check.id),
                "observed_at": observed_at,
                "evidence_policy_version": "phase5-beta-evidence-v1",
            }],
        })
        if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0].get("replayed"), bool):
            raise V2RepositoryError("manual completion returned malformed state")
        return result[0]["replayed"]

    async def get_preferences(self, owner_user_id: str) -> V2UserPreferences:
        rows = await self._request("GET", "/v2_user_preferences", params={
            "select": _PREFERENCE_SELECT, "owner_user_id": f"eq.{owner_user_id}", "limit": "1"
        })
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("V2 preferences read returned malformed rows")
        if not rows:
            return V2UserPreferences(dialogue_sound_enabled=True, motion_preference="system", version=0)
        return _preference_from_row(rows[0], expected_owner=owner_user_id)

    async def update_dialogue_sound(
        self, owner_user_id: str, expected_version: int, enabled: bool,
    ) -> V2UserPreferences:
        payload = self._object(await self._rpc("update_v2_dialogue_sound", {
            "p_owner_user_id": owner_user_id, "p_expected_version": expected_version,
            "p_dialogue_sound_enabled": enabled,
        }), "update_v2_dialogue_sound")
        return _preference_from_row(payload, expected_owner=owner_user_id)

    async def update_coding_agent(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_project_version: int,
        expected_current_change_version: int,
        coding_agent_key: str,
    ) -> tuple[V2Project, V2CurrentChange]:
        payload = self._object(
            await self._rpc(
                "update_v2_coding_agent",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_current_change_id": str(current_change_id),
                    "p_expected_project_version": expected_project_version,
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_coding_agent_key": coding_agent_key,
                },
            ),
            "update_v2_coding_agent",
        )
        return (
            _project_from_row(payload.get("project"), expected_owner=owner_user_id),
            _current_change_from_row(
                payload.get("current_change"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
        )

    async def update_prompt_draft(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        prompt_text: str,
        done_condition: str | None,
        boundaries: list[str],
        risk: str,
        risk_reason_key: str | None,
        risk_policy_version: str,
        risk_input_fingerprint: str,
    ) -> V2CurrentChange:
        payload = self._object(
            await self._rpc(
                "update_v2_prompt_draft_with_risk",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_current_change_id": str(current_change_id),
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_expected_prompt_draft_version": expected_prompt_draft_version,
                    "p_prompt_draft": prompt_text,
                    "p_done_condition_snapshot": done_condition,
                    "p_boundary_snapshots": boundaries,
                    "p_risk": risk,
                    "p_risk_reason_key": risk_reason_key,
                    "p_risk_policy_version": risk_policy_version,
                    "p_risk_input_fingerprint": risk_input_fingerprint,
                },
            ),
            "update_v2_prompt_draft_with_risk",
        )
        return _current_change_from_row(
            payload.get("current_change"),
            expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def update_effort(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        effort_category: str,
    ) -> V2CurrentChange:
        payload = self._object(
            await self._rpc(
                "update_v2_effort",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_current_change_id": str(current_change_id),
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_effort_category": effort_category,
                },
            ),
            "update_v2_effort",
        )
        return _current_change_from_row(
            payload.get("current_change"),
            expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def _get_prompt_version(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        prompt_version_id: UUID,
    ) -> V2PromptVersion | None:
        rows = await self._request(
            "GET",
            "/v2_prompt_versions",
            params={
                "select": _PROMPT_VERSION_SELECT,
                "id": f"eq.{prompt_version_id}",
                "current_change_id": f"eq.{current_change_id}",
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": "1",
            },
        )
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("V2 Prompt Version read returned malformed rows")
        if not rows:
            return None
        return _prompt_version_from_row(
            rows[0],
            expected_owner=owner_user_id,
            expected_project_id=project_id,
            expected_current_change_id=current_change_id,
        )

    async def list_prompt_versions(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
    ) -> list[V2PromptVersion]:
        change = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        if change is None:
            raise V2RepositoryNotFound("owned V2 Current Change not found")
        rows = await self._request(
            "GET",
            "/v2_prompt_versions",
            params={
                "select": _PROMPT_VERSION_SELECT,
                "current_change_id": f"eq.{current_change_id}",
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "order": "ordinal.asc,id.asc",
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 Prompt Version list returned malformed rows")
        return [
            _prompt_version_from_row(
                row,
                expected_owner=owner_user_id,
                expected_project_id=project_id,
                expected_current_change_id=current_change_id,
            )
            for row in rows
        ]

    async def accept_prompt_version(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        acceptance_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        change = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        if change is None:
            raise V2RepositoryNotFound("owned V2 Current Change not found")
        if (
            change.prompt_draft is None
            or change.coding_agent_key is None
            or change.effort_category is None
        ):
            raise V2RepositoryInvalidState("prompt acceptance prerequisites are missing")
        content_hash = hashlib.sha256(change.prompt_draft.encode("utf-8")).hexdigest()
        payload = self._object(
            await self._rpc(
                "accept_v2_prompt_version",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_current_change_id": str(current_change_id),
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_expected_prompt_draft_version": expected_prompt_draft_version,
                    "p_acceptance_command_id": str(acceptance_command_id),
                    "p_purpose": "feature",
                    "p_recovery_case_id": None,
                    "p_content": change.prompt_draft,
                    "p_content_sha256": content_hash,
                    "p_generation_attempt_id": None,
                    "p_coding_agent_key": change.coding_agent_key.value,
                    "p_effort_category": change.effort_category.value,
                    "p_provider_mapping_key": None,
                    "p_provider_mapping_version": None,
                },
            ),
            "accept_v2_prompt_version",
        )
        try:
            prompt_version_id = UUID(str(payload["prompt_version_id"]))
            replayed = payload["replayed"]
        except (KeyError, TypeError, ValueError) as exc:
            raise V2RepositoryError("prompt acceptance returned malformed identity") from exc
        if not isinstance(replayed, bool):
            raise V2RepositoryError("prompt acceptance omitted replay state")
        current = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        prompt = await self._get_prompt_version(
            owner_user_id, project_id, current_change_id, prompt_version_id
        )
        if current is None or prompt is None:
            raise V2RepositoryError("accepted prompt could not be reloaded")
        return current, prompt, replayed

    async def handoff_prompt_version(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        prompt_version_id: UUID,
        expected_current_change_version: int,
        expected_prompt_version: int,
        handoff_command_id: UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        payload = self._object(
            await self._rpc(
                "handoff_v2_prompt_version",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_current_change_id": str(current_change_id),
                    "p_prompt_version_id": str(prompt_version_id),
                    "p_recovery_case_id": None,
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_expected_prompt_version": expected_prompt_version,
                    "p_handoff_command_id": str(handoff_command_id),
                },
            ),
            "handoff_v2_prompt_version",
        )
        replayed = payload.get("replayed")
        if not isinstance(replayed, bool):
            raise V2RepositoryError("prompt handoff omitted replay state")
        current = await self.get_current_change_by_id(
            owner_user_id, project_id, current_change_id
        )
        prompt = await self._get_prompt_version(
            owner_user_id, project_id, current_change_id, prompt_version_id
        )
        if current is None or prompt is None:
            raise V2RepositoryError("handed-off prompt could not be reloaded")
        return current, prompt, replayed

    async def start_generation_attempt(
        self,
        owner_user_id: str,
        project_id: UUID,
        payload: dict[str, Any],
    ) -> tuple[V2GenerationAttempt, bool]:
        result = self._object(
            await self._rpc(
                "start_v2_generation_attempt",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    **{f"p_{key}": value for key, value in payload.items()},
                },
            ),
            "start_v2_generation_attempt",
        )
        replayed = result.get("replayed")
        if not isinstance(replayed, bool):
            raise V2RepositoryError("Generation Attempt start omitted replay state")
        return (
            _generation_attempt_from_row(
                result.get("generation_attempt"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            replayed,
        )

    async def finish_generation_attempt(
        self,
        owner_user_id: str,
        project_id: UUID,
        generation_attempt_id: UUID,
        payload: dict[str, Any],
    ) -> V2GenerationAttempt:
        result = self._object(
            await self._rpc(
                "finish_v2_generation_attempt",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_generation_attempt_id": str(generation_attempt_id),
                    **{f"p_{key}": value for key, value in payload.items()},
                },
            ),
            "finish_v2_generation_attempt",
        )
        return _generation_attempt_from_row(
            result.get("generation_attempt"),
            expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def apply_generated_prompt_draft(
        self,
        owner_user_id: str,
        project_id: UUID,
        generation_attempt_id: UUID,
        expected_attempt_version: int,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        prompt_text: str,
        done_condition: str | None,
        boundaries: list[str],
    ) -> tuple[V2GenerationAttempt, V2CurrentChange, bool, bool]:
        result = self._object(
            await self._rpc(
                "apply_v2_generated_prompt_draft",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_generation_attempt_id": str(generation_attempt_id),
                    "p_expected_attempt_version": expected_attempt_version,
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_expected_prompt_draft_version": expected_prompt_draft_version,
                    "p_prompt_draft": prompt_text,
                    "p_done_condition_snapshot": done_condition,
                    "p_boundary_snapshots": boundaries,
                },
            ),
            "apply_v2_generated_prompt_draft",
        )
        replayed = result.get("replayed")
        applied = result.get("applied")
        if not isinstance(replayed, bool) or not isinstance(applied, bool):
            raise V2RepositoryError("generated prompt application omitted replay state")
        return (
            _generation_attempt_from_row(
                result.get("generation_attempt"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            _current_change_from_row(
                result.get("current_change"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            applied,
            replayed,
        )

    async def get_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
    ) -> V2CurrentChange | None:
        project = await self.get_project(owner_user_id, project_id)
        if project is None:
            raise V2RepositoryNotFound("owned V2 Project not found")
        rows = await self._request(
            "GET",
            "/v2_current_changes",
            params={
                "select": _CURRENT_CHANGE_SELECT,
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "lifecycle_state": "in.(preparing,awaiting_agent,reviewing,recovering)",
                "limit": "1",
            },
        )
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("current V2 Current Change read returned malformed rows")
        if not rows:
            return None
        return _current_change_from_row(
            rows[0],
            expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def get_current_change_by_id(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
    ) -> V2CurrentChange | None:
        rows = await self._request(
            "GET",
            "/v2_current_changes",
            params={
                "select": _CURRENT_CHANGE_SELECT,
                "id": f"eq.{current_change_id}",
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": "1",
            },
        )
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("explicit V2 Current Change read returned malformed rows")
        if not rows:
            return None
        return _current_change_from_row(
            rows[0],
            expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def list_history_changes(
        self, owner_user_id: str, project_id: UUID, *, limit: int, offset: int,
    ) -> tuple[list[V2CurrentChange], bool]:
        rows = await self._request(
            "GET",
            "/v2_current_changes",
            params={
                "select": _CURRENT_CHANGE_SELECT,
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "order": "created_at.desc,id.desc",
                "limit": str(limit + 1),
                "offset": str(offset),
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 History Current Change read returned malformed rows")
        changes = [
            _current_change_from_row(
                row, expected_owner=owner_user_id, expected_project_id=project_id
            )
            for row in rows[:limit]
        ]
        return changes, len(rows) > limit

    async def list_history_checks(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        *, limit: int,
    ) -> tuple[list[V2Check], bool]:
        rows = await self._request(
            "GET",
            "/v2_checks",
            params={
                "select": _CHECK_SELECT,
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "current_change_id": f"eq.{current_change_id}",
                "order": "created_at.asc,id.asc",
                "limit": str(limit + 1),
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 History Check read returned malformed rows")
        checks = [
            _check_from_row(row, expected_owner=owner_user_id, expected_project_id=project_id)
            for row in rows[:limit]
        ]
        return checks, len(rows) > limit

    async def get_latest_history_performed_check(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
    ) -> V2Check | None:
        rows = await self._request(
            "GET",
            "/v2_checks",
            params={
                "select": _CHECK_SELECT,
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "current_change_id": f"eq.{current_change_id}",
                "status": "eq.performed",
                "order": "performed_at.desc,id.desc",
                "limit": "1",
            },
        )
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError(
                "V2 History authoritative performed Check read returned malformed rows"
            )
        if not rows:
            return None
        return _check_from_row(
            rows[0], expected_owner=owner_user_id, expected_project_id=project_id
        )

    async def list_history_prompt_versions(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        *, limit: int,
    ) -> tuple[list[V2PromptVersion], bool]:
        rows = await self._request(
            "GET",
            "/v2_prompt_versions",
            params={
                "select": _PROMPT_VERSION_SELECT,
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "current_change_id": f"eq.{current_change_id}",
                "order": "ordinal.asc,id.asc",
                "limit": str(limit + 1),
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 History Prompt Version read returned malformed rows")
        prompts = [
            _prompt_version_from_row(
                row, expected_owner=owner_user_id, expected_project_id=project_id,
                expected_current_change_id=current_change_id,
            )
            for row in rows[:limit]
        ]
        return prompts, len(rows) > limit

    async def list_history_recovery_cases(
        self, owner_user_id: str, project_id: UUID, current_change_id: UUID,
        *, limit: int,
    ) -> tuple[list[V2RecoveryCase], bool]:
        rows = await self._request(
            "GET",
            "/v2_recovery_cases",
            params={
                "select": _RECOVERY_SELECT,
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "current_change_id": f"eq.{current_change_id}",
                "order": "opened_at.asc,id.asc",
                "limit": str(limit + 1),
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 History Recovery Case read returned malformed rows")
        recoveries = [
            _recovery_from_row(
                row, expected_owner=owner_user_id,
                expected_project_id=project_id,
                expected_current_change_id=current_change_id,
            )
            for row in rows[:limit]
        ]
        return recoveries, len(rows) > limit

    async def cancel_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        cancellation_command_id: UUID,
        cancellation_reason_key: str,
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(
            await self._rpc(
                "cancel_v2_current_change",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_current_change_id": str(current_change_id),
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_cancellation_command_id": str(cancellation_command_id),
                    "p_cancellation_reason_key": cancellation_reason_key,
                },
            ),
            "cancel_v2_current_change",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("Current Change cancellation omitted replay state")
        return (
            _current_change_from_row(
                payload.get("current_change"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            payload["replayed"],
        )


def get_v2_repository() -> V2Repository:
    return SupabaseV2Repository(get_settings())
