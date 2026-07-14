"""Student-safe Defense Report backend foundation (M16C.1)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.workflow_context import CuratedWorkflowContext

REPORT_SCHEMA_VERSION = "1.0"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportDefenseTurn(_Model):
    turn: int
    question: str
    answer: str | None = None


class ReportDefenseRecord(_Model):
    state: Literal["not_started", "in_progress", "passed", "failed"]
    turns: list[ReportDefenseTurn]
    evaluator_outcome: Literal["PASS", "FAIL"] | None = None
    evaluator_reason: str | None = None


class DefenseReportContext(_Model):
    schema_version: str = REPORT_SCHEMA_VERSION
    phase_number: int
    phase_title: str
    workflow_context_source: Literal["defense_attempt", "current_workflow"]
    workflow_context: CuratedWorkflowContext
    defense: ReportDefenseRecord
    truth_notice: str = (
        "This report preserves student decisions, student-recorded Verification "
        "results, student-provided Evidence, and the Project Defense evaluator's "
        "outcome under Codize's gate contract. These records are not independent "
        "proof that the implementation or Evidence is correct."
    )
