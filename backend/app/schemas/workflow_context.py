"""Typed downstream workflow context for Defense and Defense Report.

This is the one server-derived representation of Change Map, Review,
Verification, and Evidence.  It contains no raw Implementation Import,
database identity, provenance binding, fingerprint, timestamp, provider data,
or hidden evaluator information.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WORKFLOW_CONTEXT_SCHEMA_VERSION = "1.0"

ArtifactState = Literal[
    "missing",
    "manual",
    "current",
    "stale",
    "incomplete",
    "malformed",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowContextEvidenceEntry(_Model):
    kind: str
    content: str


class WorkflowContextChangeItem(_Model):
    category: str
    origin: Literal["ai_inferred", "student_added"]
    student_decision: str
    text: str
    provenance: str
    ai_uncertainty: str | None = None
    uncertainty_reason: str | None = None
    student_note: str | None = None


class WorkflowContextChangeMap(_Model):
    state: ArtifactState
    items: list[WorkflowContextChangeItem] = Field(default_factory=list)
    truncated: bool = False


class WorkflowContextManualReview(_Model):
    files_changed: list[str] = Field(default_factory=list)
    ai_generated: str | None = None
    accepted: str | None = None
    rejected: str | None = None
    edited_manually: str | None = None
    ai_assumptions: str | None = None
    least_confident: str | None = None
    out_of_scope_changes: str | None = None


class WorkflowContextReviewItem(_Model):
    category: str
    source_origin: Literal["ai_inferred", "student_added"]
    source_student_decision: str
    source_resolution: Literal["confirmed", "unresolved"]
    reviewed_text: str
    review_decision: str
    student_rationale: str | None = None
    student_revision: str | None = None


class WorkflowContextReview(_Model):
    state: ArtifactState
    items: list[WorkflowContextReviewItem] = Field(default_factory=list)
    manual: WorkflowContextManualReview | None = None
    truncated: bool = False


class WorkflowContextVerificationCheck(_Model):
    check: str
    result: Literal["pass", "fail", "skipped", "not_applicable", "unrecorded"]
    result_notes: str | None = None
    category: str | None = None
    provenance: Literal["student_recorded", "student_unrecorded"]


class WorkflowContextVerification(_Model):
    state: ArtifactState
    checks: list[WorkflowContextVerificationCheck] = Field(default_factory=list)
    student_explanation: str | None = None
    truncated: bool = False


class WorkflowContextEvidenceRecord(_Model):
    category: str
    check_context: str
    verification_result: Literal["pass", "fail"]
    verification_notes: str | None = None
    evidence_status: Literal[
        "not_addressed", "evidence_recorded", "evidence_unavailable"
    ]
    entries: list[WorkflowContextEvidenceEntry] = Field(default_factory=list)
    student_explanation: str | None = None
    unavailable_reason: str | None = None
    stale_support_omitted: bool = False


class WorkflowContextEvidence(_Model):
    state: ArtifactState
    records: list[WorkflowContextEvidenceRecord] = Field(default_factory=list)
    manual_entries: list[WorkflowContextEvidenceEntry] = Field(default_factory=list)
    manual_summary: str | None = None
    truncated: bool = False


class CuratedWorkflowContext(_Model):
    schema_version: str = WORKFLOW_CONTEXT_SCHEMA_VERSION
    phase_number: int = Field(ge=1)
    state: ArtifactState
    change_map: WorkflowContextChangeMap
    review: WorkflowContextReview
    verification: WorkflowContextVerification
    evidence: WorkflowContextEvidence
    content_truncated: bool = False
    content_redacted: bool = False
