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
