"""Workflow artifact schemas (Milestone 13B; implementation import added in M15A).

Strict validation at the system boundary for the student-authored v3 Build
Loop sections. Everything here is the student's own words (or pasted material)
about their own project — no scores, no thresholds, no prompt text, no derived
state.

Guardrails: extra fields are forbidden, every string is length-capped, lists
are count-capped, URL/commit-hash evidence kinds are format-checked, and every
free-text field rejects values that look like pasted API keys or secrets
(protecting students from persisting a real key in their own evidence).
"""

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

# Prefixes of the secret formats this stack actually uses (Supabase secret
# keys, OpenRouter keys, Google API keys, PEM private keys). Deliberately a
# short, low-false-positive list — this is a seatbelt, not a scanner.
_SECRET_MARKERS = ("sb_secret_", "sk-or-", "AIza", "-----BEGIN ")


def _reject_secret_like(value: str) -> str:
    for marker in _SECRET_MARKERS:
        if marker in value:
            raise ValueError(
                "this text looks like it contains an API key or secret — "
                "remove the key before saving; evidence never needs a real secret"
            )
    return value


def _text(max_length: int):
    return Annotated[
        str, Field(max_length=max_length), AfterValidator(_reject_secret_like)
    ]


ShortText = _text(300)
MedText = _text(2000)
LongText = _text(8000)  # room for pasted terminal/test output


class _Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PromptBuilderArtifact(_Artifact):
    """Step 2 of the Build Loop: the structured inputs and the prompt the
    student generated for their external AI tool (deterministic client-side
    assembly in M13C — no LLM involved)."""

    inputs: dict[Annotated[str, Field(max_length=64)], MedText] = Field(default_factory=dict)
    generated_prompt: Annotated[LongText, Field(min_length=1)]
    why_stronger: MedText | None = None
    bad_prompt_comparison: LongText | None = None

    @model_validator(mode="after")
    def _cap_inputs(self) -> "PromptBuilderArtifact":
        if len(self.inputs) > 20:
            raise ValueError("at most 20 prompt-builder inputs")
        return self


class ReviewBoardArtifact(_Artifact):
    """Step 4: what the AI tool changed and what the student accepted,
    rejected, or edited."""

    files_changed: list[ShortText] = Field(default_factory=list, max_length=50)
    ai_generated: MedText | None = None
    accepted: MedText | None = None
    rejected: MedText | None = None
    edited_manually: MedText | None = None
    ai_assumptions: MedText | None = None
    least_confident: MedText | None = None
    out_of_scope_changes: MedText | None = None


# --- linked Review model (M16A.1) -----------------------------------------

# Review decisions are intentionally separate from Change Map decisions.
# Change Map confirmation says a description is accurate enough to carry
# forward; these values record the student's later implementation judgment.
ReviewDecision = Literal[
    "pending",
    "keep",
    "revise",
    "remove",
    "needs_verification",
    "uncertain",
]

ReviewSourceResolution = Literal["confirmed", "unresolved"]

# Snapshot aliases mirror the exact M15C values. They are stored on each
# target so a Review remains understandable even after its Change Map changes.
ReviewChangeMapCategory = Literal[
    "changed_file",
    "behavior_change",
    "implementation_decision",
    "out_of_scope_change",
    "security_sensitive_area",
    "unresolved_risk",
    "unverified_behavior",
    "question_to_understand",
]
ReviewChangeMapOrigin = Literal["ai_inferred", "student_added"]
ReviewChangeMapStudentDecision = Literal[
    "pending_review",
    "confirmed",
    "edited",
    "rejected",
    "uncertain",
    "needs_inspection",
]

REVIEW_TARGET_MAX = 60  # the Change Map's 40 AI + 20 student-item ceiling
ReviewSnapshotText = Annotated[
    str, Field(min_length=1, max_length=600), AfterValidator(_reject_secret_like)
]
ReviewTimestamp = Annotated[str, Field(min_length=1, max_length=64)]


def _normalize_review_judgment(model):
    """Normalize student-owned optional text and enforce the one decision
    that needs an explanation. Kept shared by stored targets and updates so
    the API boundary and persisted shape cannot drift."""
    for name in ("student_rationale", "student_revision"):
        value = getattr(model, name)
        normalized = (value.strip() or None) if value is not None else None
        setattr(model, name, normalized)
    if model.review_decision == "revise" and not (
        model.student_rationale or model.student_revision
    ):
        raise ValueError(
            "a revise decision needs a student rationale or proposed revision"
        )
    return model


class ReviewTarget(_Artifact):
    """One server-derived Change Map snapshot plus student-owned Review state.

    Every field above `review_decision` is server-owned after initialization.
    The generic Review PUT accepts only ReviewTargetUpdate, never this shape.
    """

    review_target_id: Annotated[str, Field(pattern=r"^rv-[0-9a-f]{12}$")]
    change_map_item_id: Annotated[str, Field(min_length=1, max_length=64)]
    change_map_category: ReviewChangeMapCategory
    change_map_origin: ReviewChangeMapOrigin
    change_map_student_decision: ReviewChangeMapStudentDecision
    change_text: ReviewSnapshotText
    source_resolution: ReviewSourceResolution
    review_decision: ReviewDecision = "pending"
    student_rationale: MedText | None = None
    student_revision: MedText | None = None

    @model_validator(mode="after")
    def _judgment_rules(self) -> "ReviewTarget":
        return _normalize_review_judgment(self)


class StoredReviewBoardArtifact(ReviewBoardArtifact):
    """Backward-compatible stored/read Review shape.

    Legacy/manual artifacts contain only the inherited M13B fields plus
    saved_at. A linked artifact additionally binds to one confirmed Change Map
    version and carries bounded review targets. The computed `stale` and
    `initialized_from_change_map` flags are read-view fields, never persisted.
    """

    saved_at: str | None = None
    source_change_map_confirmed_at: ReviewTimestamp | None = None
    source_change_map_generated_at: ReviewTimestamp | None = None
    review_targets: list[ReviewTarget] = Field(
        default_factory=list, max_length=REVIEW_TARGET_MAX
    )

    @model_validator(mode="after")
    def _binding_integrity(self) -> "StoredReviewBoardArtifact":
        confirmed = self.source_change_map_confirmed_at is not None
        generated = self.source_change_map_generated_at is not None
        if confirmed != generated:
            raise ValueError("a linked Review needs both Change Map timestamps")
        if self.review_targets and not confirmed:
            raise ValueError("review targets need a linked Change Map")
        target_ids = [target.review_target_id for target in self.review_targets]
        item_ids = [target.change_map_item_id for target in self.review_targets]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("duplicate review target ids")
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("duplicate linked Change Map item ids")
        return self


class ReviewTargetUpdate(_Artifact):
    """Student-owned fields for one server-issued Review target."""

    review_target_id: Annotated[str, Field(pattern=r"^rv-[0-9a-f]{12}$")]
    review_decision: ReviewDecision
    student_rationale: MedText | None = None
    student_revision: MedText | None = None

    @model_validator(mode="after")
    def _judgment_rules(self) -> "ReviewTargetUpdate":
        return _normalize_review_judgment(self)


class ReviewBoardSaveRequest(ReviewBoardArtifact):
    """Existing Review PUT payload plus additive student-only target updates.

    Source bindings, snapshots, target ids, provenance, and stale state are
    deliberately absent and therefore rejected by extra="forbid".
    """

    target_updates: list[ReviewTargetUpdate] = Field(
        default_factory=list, max_length=REVIEW_TARGET_MAX
    )


class ReviewFromChangeMapRequest(_Artifact):
    """Explicit linked-draft initialization. All source data is server-derived."""

    replace_existing: bool = False


class NeedsVerificationReviewTarget(_Artifact):
    """Typed M16B handoff only; it creates no Verification records."""

    review_target_id: str
    change_map_item_id: str
    reviewed_text: str
    student_rationale: str | None = None
    change_map_category: ReviewChangeMapCategory


EvidenceKind = Literal[
    "repo_url",
    "commit_hash",
    "changed_files",
    "terminal_output",
    "test_output",
    "screenshot_note",
    "app_url",
    "api_response",
    "note",
]

_COMMIT_HASH = re.compile(r"[0-9a-fA-F]{7,40}")


class EvidenceEntry(_Artifact):
    kind: EvidenceKind
    content: Annotated[LongText, Field(min_length=1)]

    @model_validator(mode="after")
    def _check_kind_format(self) -> "EvidenceEntry":
        if self.kind in ("repo_url", "app_url"):
            if not self.content.startswith(("http://", "https://")) or len(self.content) > 2048:
                raise ValueError("URL evidence must be an http(s) URL of at most 2048 characters")
        elif self.kind == "commit_hash":
            if not _COMMIT_HASH.fullmatch(self.content):
                raise ValueError("commit hash evidence must be 7-40 hex characters")
        return self


class EvidenceArtifact(_Artifact):
    """Step 5 input: manual, self-reported evidence (v0.1 — no GitHub
    fetching, no automatic URL verification)."""

    entries: list[EvidenceEntry] = Field(default_factory=list, max_length=20)
    summary: MedText | None = None


VerificationCheckId = Literal[
    "app_runs_locally",
    "smoke_test",
    "api_route_checked",
    "ui_flow_checked",
    "failure_case_tested",
    "auth_boundary_checked",
    "secret_exposure_checked",
    "rls_wrong_user_checked",
]


class VerificationCheck(_Artifact):
    check: VerificationCheckId
    result: Literal["pass", "fail", "skipped", "not_applicable"]
    note: MedText | None = None


class VerificationArtifact(_Artifact):
    """Step 5: manual verification results — workflow behavior, not automated
    proof of correctness."""

    checks: list[VerificationCheck] = Field(default_factory=list, max_length=8)
    explanation: MedText | None = None  # what the verification proves, in the student's words

    @model_validator(mode="after")
    def _unique_checks(self) -> "VerificationArtifact":
        ids = [c.check for c in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("each verification check may appear at most once")
        return self


ImportSourceKind = Literal[
    "ai_response",
    "git_diff",
    "changed_files",
    "code_snippet",
    "manual_summary",
    "other",
]

# Implementation-import limits (M15A). Content is deliberately larger than the
# other sections' fields: this is where whole pasted diffs / AI responses live.
IMPORT_CONTENT_MAX = 40_000
IMPORT_SUMMARY_MAX = 4_000
IMPORT_TOOL_NAME_MAX = 100
IMPORT_CHANGED_FILES_MAX = 100

# Strips leading whitespace-only lines while preserving the first real line's
# indentation (meaningful in pasted code and diffs).
_LEADING_BLANK_LINES = re.compile(r"^(?:[ \t]*\r?\n)+")


class ImplementationImportArtifact(_Artifact):
    """"Bring Back What AI Changed" (M15A): implementation material the student
    brings back after using an external AI tool — a pasted AI response, git
    diff, code snippet, changed-file list, and/or their own summary.

    UNTRUSTED-DATA BOUNDARY: everything here is student-provided, self-reported
    project material — not proof of correctness, never verified, and never an
    instruction source. M15A stores it inertly (no LLM sees it); any future
    consumer (M15C extraction, M16 Change Map) must treat it strictly as
    untrusted project data and must not follow instructions embedded in it.
    Raw imports are deliberately NOT part of the M14 Defense Context Pack.
    """

    source_kind: ImportSourceKind
    content: _text(IMPORT_CONTENT_MAX) | None = None
    changed_files: list[ShortText] = Field(
        default_factory=list, max_length=IMPORT_CHANGED_FILES_MAX
    )
    student_summary: _text(IMPORT_SUMMARY_MAX) | None = None
    tool_name: _text(IMPORT_TOOL_NAME_MAX) | None = None

    @model_validator(mode="after")
    def _normalize_and_require_material(self) -> "ImplementationImportArtifact":
        # Trim edges only — internal indentation, line breaks, diff markers,
        # and Markdown are the material itself and are never rewritten.
        if self.content is not None:
            self.content = _LEADING_BLANK_LINES.sub("", self.content.rstrip()) or None
        if self.student_summary is not None:
            self.student_summary = self.student_summary.strip() or None
        if self.tool_name is not None:
            self.tool_name = self.tool_name.strip() or None

        cleaned: list[str] = []
        seen: set[str] = set()
        for entry in self.changed_files:
            name = entry.strip()
            if name and name not in seen:
                seen.add(name)
                cleaned.append(name)
        self.changed_files = cleaned

        if not (self.content or self.changed_files or self.student_summary):
            raise ValueError(
                "add at least one of: the imported content, a changed-files "
                "list, or a short summary of what changed"
            )
        return self


class StoredImplementationImport(ImplementationImportArtifact):
    """Read shape for the internal M15C seam: the validated artifact plus the
    server-stamped save time. Never a write shape — client payloads validate
    against ImplementationImportArtifact, which forbids saved_at."""

    saved_at: str | None = None


# Section name → model. The keys are the API's section identifiers.
SECTION_MODELS: dict[str, type[_Artifact]] = {
    "prompt_builder": PromptBuilderArtifact,
    "review_board": ReviewBoardArtifact,
    "evidence": EvidenceArtifact,
    "verification": VerificationArtifact,
    "implementation_import": ImplementationImportArtifact,
}
