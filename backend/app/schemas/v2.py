"""Typed, client-safe request and response contracts for Codize V2.3A."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.v2 import (
    CurrentChangeKind,
    CurrentChangeState,
    PlanItemStatus,
    PlanScopeBand,
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
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None


class CurrentChangeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_change: CurrentChangeView | None
    replayed: bool = False
