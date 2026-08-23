"""Typed, client-safe request and response contracts for Codize V2."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.v2 import (
    BuildStage,
    CodingAgentKey,
    CurrentChangeKind,
    CurrentChangeState,
    EffortCategory,
    GenerationPurpose,
    GenerationStatus,
    PlanItemStatus,
    PlanScopeBand,
    PromptPurpose,
    ProjectLifecycle,
    ResumeStep,
    SetupResumeStep,
)

WorkflowV2 = Literal["v2"]
CancellationReason = Literal[
    "student_cancelled",
    "student_chose_another_change",
    "plan_item_removed",
]


def _bounded_utf8(value: str, maximum: int, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    if len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{field_name} is too long")
    return value


def _bounded_utf8_preserving(value: str, maximum: int, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    if len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{field_name} is too long")
    return value


class ProjectRefView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: Literal["v1", "v2"]
    project_id: UUID
    display_name: str
    open_mode: Literal["legacy_active_only", "explicit"]


class ProjectRefIdentityView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: Literal["v1", "v2"]
    project_id: UUID


class ProjectRefsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projects: list[ProjectRefView]


class V2ProjectView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: Literal["v2"] = "v2"
    project_id: UUID
    display_name: str
    lifecycle_state: ProjectLifecycle
    setup_resume_step: SetupResumeStep
    coding_agent_key: str | None
    plan_version: int
    version: int
    first_version_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectCommandResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: V2ProjectView
    replayed: bool


class _CreateProjectBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    command_id: UUID
    display_name: str

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        return _bounded_utf8(value, 120, "display_name")


class NewIdeaProjectRequest(_CreateProjectBase):
    creation_intent: Literal["new_idea"]


class AlreadyBuildingProjectRequest(_CreateProjectBase):
    creation_intent: Literal["already_building"]


class RecoveryContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_context: str
    intended_behavior: str
    observed_symptom: str
    last_known_working_statement: str | None = None
    last_known_working_certainty: Literal["yes", "no", "unsure"]
    candidate_change_summary: str

    @field_validator("project_context", "intended_behavior", "observed_symptom")
    @classmethod
    def validate_recovery_text(cls, value: str) -> str:
        return _bounded_utf8(value, 16384, "recovery context")

    @field_validator("last_known_working_statement")
    @classmethod
    def validate_last_known(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _bounded_utf8(value, 16384, "last_known_working_statement")

    @field_validator("candidate_change_summary")
    @classmethod
    def validate_candidate_change(cls, value: str) -> str:
        return _bounded_utf8(value, 8192, "candidate_change_summary")


class RecoveryFirstProjectRequest(_CreateProjectBase):
    creation_intent: Literal["recovery_first"]
    current_change_command_id: UUID
    recovery_context: RecoveryContextRequest


CreateProjectRequest = Annotated[
    Union[
        NewIdeaProjectRequest,
        AlreadyBuildingProjectRequest,
        RecoveryFirstProjectRequest,
    ],
    Field(discriminator="creation_intent"),
]


class PromoteProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    command_id: UUID
    expected_project_version: int = Field(gt=0)


class PurgeTemporaryProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    expected_project_version: int = Field(gt=0)


class PurgeProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_ref: ProjectRefIdentityView
    purged: Literal[True] = True


class PlanItemView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    label: str
    intended_outcome: str
    scope_band: PlanScopeBand
    status: PlanItemStatus
    order_key: int
    version: int
    completed_at: datetime | None
    terminal_current_change_id: UUID | None


class PlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: Literal["v2"] = "v2"
    project_id: UUID
    project_version: int
    plan_version: int
    items: list[PlanItemView]
    replayed: bool = False


class PlanAddOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["add"]
    plan_item_id: UUID
    label: str
    intended_outcome: str
    scope_band: PlanScopeBand
    status: Literal["proposed", "ready", "deferred"]
    order_key: int = Field(gt=0)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _bounded_utf8(value, 200, "label")

    @field_validator("intended_outcome")
    @classmethod
    def validate_outcome(cls, value: str) -> str:
        return _bounded_utf8(value, 4096, "intended_outcome")


class PlanEditOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["edit"]
    plan_item_id: UUID
    expected_version: int = Field(gt=0)
    label: str
    intended_outcome: str
    status: Literal["proposed", "ready", "deferred"]

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _bounded_utf8(value, 200, "label")

    @field_validator("intended_outcome")
    @classmethod
    def validate_outcome(cls, value: str) -> str:
        return _bounded_utf8(value, 4096, "intended_outcome")


class PlanReorderOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["reorder"]
    plan_item_id: UUID
    expected_version: int = Field(gt=0)
    order_key: int = Field(gt=0)


class PlanMoveOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["move"]
    plan_item_id: UUID
    expected_version: int = Field(gt=0)
    scope_band: PlanScopeBand
    order_key: int = Field(gt=0)


class PlanRemoveOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["remove"]
    plan_item_id: UUID
    expected_version: int = Field(gt=0)


PlanOperation = Annotated[
    Union[
        PlanAddOperation,
        PlanEditOperation,
        PlanReorderOperation,
        PlanMoveOperation,
        PlanRemoveOperation,
    ],
    Field(discriminator="action"),
]


class PlanMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    command_id: UUID
    expected_project_version: int = Field(gt=0)
    expected_plan_version: int = Field(gt=0)
    operations: list[PlanOperation] = Field(min_length=1, max_length=128)
    expected_current_change_version: int | None = Field(default=None, gt=0)
    linked_item_action: Literal["detach", "cancel"] | None = None
    cancellation_command_id: UUID | None = None
    cancellation_reason_key: CancellationReason | None = None

    @model_validator(mode="after")
    def validate_linked_item_action(self) -> "PlanMutationRequest":
        has_remove = any(operation.action == "remove" for operation in self.operations)
        if self.linked_item_action is None:
            if any(
                value is not None
                for value in (
                    self.expected_current_change_version,
                    self.cancellation_command_id,
                    self.cancellation_reason_key,
                )
            ):
                raise ValueError("linked-item fields require linked_item_action")
            return self
        if not has_remove or self.expected_current_change_version is None:
            raise ValueError("linked_item_action requires a remove operation and current version")
        if self.linked_item_action == "detach":
            if self.cancellation_command_id is not None or self.cancellation_reason_key is not None:
                raise ValueError("detach cannot include cancellation fields")
        elif self.cancellation_command_id is None or self.cancellation_reason_key is None:
            raise ValueError("cancel requires cancellation identity and reason")
        return self


class StartCurrentChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    command_id: UUID
    expected_project_version: int = Field(gt=0)
    plan_item_id: UUID | None = None
    change_kind: CurrentChangeKind = CurrentChangeKind.BUILD
    goal_snapshot: str

    @field_validator("goal_snapshot")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        return _bounded_utf8(value, 4096, "goal_snapshot")


class CancelCurrentChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    command_id: UUID
    expected_current_change_version: int = Field(gt=0)
    reason: CancellationReason = "student_cancelled"


class ResumeStateView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lifecycle_state: CurrentChangeState
    resume_step: ResumeStep | None
    available_commands: list[Literal["cancel"]]


class CurrentChangeView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    workflow_version: Literal["v2"] = "v2"
    project_id: UUID
    plan_item_id: UUID | None
    change_kind: CurrentChangeKind
    lifecycle_state: CurrentChangeState
    resume_step: ResumeStep | None
    resume: ResumeStateView
    goal_snapshot: str
    done_condition_snapshot: str | None
    boundary_snapshots: list[str]
    prompt_draft: str | None
    prompt_draft_version: int
    coding_agent_key: CodingAgentKey | None
    effort_category: EffortCategory | None
    latest_prompt_version_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None


class CurrentChangeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_change: CurrentChangeView | None
    replayed: bool = False


class AgentMetadataView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: CodingAgentKey
    display_name: str
    reasoning_controls_known: bool
    mapping_available: bool
    stale_fallback: str


class CodingAgentSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    expected_project_version: int = Field(gt=0)
    expected_current_change_version: int = Field(gt=0)
    choice: Literal[
        "codex",
        "claude_code",
        "cursor",
        "chatgpt",
        "replit",
        "other",
        "help_me_choose",
    ]


class CodingAgentSelectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: Literal["v2"] = "v2"
    project_id: UUID
    current_change_id: UUID
    project_version: int
    current_change_version: int
    selected_agent: AgentMetadataView | None
    guidance_required: bool


class PromptDraftUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    expected_current_change_version: int = Field(gt=0)
    expected_prompt_draft_version: int = Field(gt=0)
    prompt_text: str
    done_condition: str | None = None
    boundaries: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("prompt_text")
    @classmethod
    def validate_prompt_text(cls, value: str) -> str:
        return _bounded_utf8_preserving(value, 65536, "prompt_text")

    @field_validator("done_condition")
    @classmethod
    def validate_done_condition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _bounded_utf8_preserving(value, 8192, "done_condition")

    @field_validator("boundaries")
    @classmethod
    def validate_boundaries(cls, values: list[str]) -> list[str]:
        cleaned = [
            _bounded_utf8_preserving(value, 256, "boundary") for value in values
        ]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("boundaries cannot contain duplicates")
        if len("".join(cleaned).encode("utf-8")) > 8192:
            raise ValueError("boundaries are too long")
        return cleaned


class EffortSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    expected_current_change_version: int = Field(gt=0)
    effort: EffortCategory


class PromptAcceptanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    command_id: UUID
    expected_current_change_version: int = Field(gt=0)
    expected_prompt_draft_version: int = Field(gt=0)


class PromptVersionView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    current_change_id: UUID
    ordinal: int
    purpose: PromptPurpose
    content: str
    coding_agent_key: CodingAgentKey
    effort_category: EffortCategory | None
    accepted_at: datetime
    handed_off_at: datetime | None
    version: int


class PromptAcceptanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_change: CurrentChangeView
    prompt_version: PromptVersionView
    replayed: bool


class PromptVersionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: Literal["v2"] = "v2"
    project_id: UUID
    current_change_id: UUID
    prompt_versions: list[PromptVersionView]


class PromptHandoffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: WorkflowV2
    command_id: UUID
    prompt_version_id: UUID
    expected_current_change_version: int = Field(gt=0)
    expected_prompt_version: int = Field(gt=0)


class PromptHandoffResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_change: CurrentChangeView
    prompt_version: PromptVersionView
    exact_prompt: str
    replayed: bool


class StructuredPromptDecisionsView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intended_result: str
    done_condition: str | None
    boundaries: list[str]
    coding_agent_key: CodingAgentKey | None


class BuildResumeStateView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_version: Literal["v2"] = "v2"
    project_id: UUID
    current_change_id: UUID
    lifecycle_state: CurrentChangeState
    resume_step: ResumeStep | None
    build_stage: BuildStage
    selected_agent: AgentMetadataView | None
    prompt_draft: str | None
    prompt_draft_version: int
    effort_category: EffortCategory | None
    structured_decisions: StructuredPromptDecisionsView
    accepted_prompt_version: PromptVersionView | None
    ready_to_handoff: bool
    exact_handoff_prompt: str | None
    current_change_version: int


class StartGenerationAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: UUID
    target_current_change_id: UUID | None = None
    target_recovery_case_id: UUID | None = None
    purpose: GenerationPurpose
    target_aggregate_version: int = Field(gt=0)
    policy_version: str | None = Field(default=None, max_length=64)
    config_version: str = Field(min_length=1, max_length=64)
    provider_key: str = Field(min_length=1, max_length=64)
    model_key: str = Field(min_length=1, max_length=128)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_target(self) -> "StartGenerationAttemptRequest":
        if self.target_current_change_id is not None and self.target_recovery_case_id is not None:
            raise ValueError("a Generation Attempt has one target")
        project_purposes = {
            GenerationPurpose.SETUP_SUMMARY,
            GenerationPurpose.FIRST_VERSION_PROPOSAL,
            GenerationPurpose.PLAN_PROPOSAL,
            GenerationPurpose.PROJECT_ANSWER,
        }
        current_change_purposes = {
            GenerationPurpose.INTERVENTION_COPY,
            GenerationPurpose.PROMPT_DRAFT,
            GenerationPurpose.CONCEPT_EXPLANATION,
        }
        recovery_purposes = {
            GenerationPurpose.RECOVERY_SUMMARY,
            GenerationPurpose.DIAGNOSTIC_PROMPT,
            GenerationPurpose.CORRECTION_PROMPT,
        }
        if self.purpose in project_purposes and (
            self.target_current_change_id is not None
            or self.target_recovery_case_id is not None
        ):
            raise ValueError("this generation purpose targets the Project")
        if (
            self.purpose in current_change_purposes
            and self.target_current_change_id is None
        ):
            raise ValueError("this generation purpose requires a Current Change target")
        if self.purpose in recovery_purposes and self.target_recovery_case_id is None:
            raise ValueError("this generation purpose requires a Recovery Case target")
        return self


class FinishGenerationAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_attempt_version: int = Field(gt=0)
    status: Literal["succeeded", "failed"]
    safe_error_category: str | None = Field(default=None, min_length=1, max_length=64)
    retryable: bool | None = None
    result_record_type: Literal["prompt_version", "build_turn"] | None = None
    result_record_id: UUID | None = None

    @model_validator(mode="after")
    def validate_completion(self) -> "FinishGenerationAttemptRequest":
        if self.status == "failed":
            if self.safe_error_category is None or self.retryable is None:
                raise ValueError("failed generation requires a safe category and retryability")
            if self.result_record_type is not None or self.result_record_id is not None:
                raise ValueError("failed generation cannot have a result record")
        else:
            if self.safe_error_category is not None or self.retryable is not None:
                raise ValueError("successful generation cannot have failure metadata")
            if self.result_record_type is None or self.result_record_id is None:
                raise ValueError("successful generation requires an accepted result record")
        return self


class ApplyGeneratedPromptDraftRequest(BaseModel):
    """Validated provider output for one atomic Generation Attempt application."""

    model_config = ConfigDict(extra="forbid")

    expected_attempt_version: int = Field(gt=0)
    expected_current_change_version: int = Field(gt=0)
    expected_prompt_draft_version: int = Field(gt=0)
    prompt_text: str
    done_condition: str | None = None
    boundaries: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("prompt_text")
    @classmethod
    def validate_prompt_text(cls, value: str) -> str:
        return _bounded_utf8_preserving(value, 65536, "prompt_text")

    @field_validator("done_condition")
    @classmethod
    def validate_done_condition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _bounded_utf8_preserving(value, 8192, "done_condition")

    @field_validator("boundaries")
    @classmethod
    def validate_boundaries(cls, values: list[str]) -> list[str]:
        cleaned = [
            _bounded_utf8_preserving(value, 256, "boundary") for value in values
        ]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("boundaries cannot contain duplicates")
        if len("".join(cleaned).encode("utf-8")) > 8192:
            raise ValueError("boundaries are too long")
        return cleaned


class GenerationAttemptView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    purpose: GenerationPurpose
    target_aggregate_version: int
    status: GenerationStatus
    safe_error_category: str | None
    retryable: bool | None
    result_record_type: str | None
    result_record_id: UUID | None
    started_at: datetime
    completed_at: datetime | None
    version: int


class ApplyGeneratedPromptDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation_attempt: GenerationAttemptView
    current_change: CurrentChangeView
    applied: bool
    replayed: bool
