"""Change Map schemas (Milestone 15C.1).

The Change Map converts a saved Implementation Import into an AI-generated,
EDITABLE DRAFT of what appears to have changed — never a verified statement of
what did change. The permanent provenance chain is preserved field-by-field:

    student-provided implementation material  (the M15A import — untrusted)
      → AI-generated draft item               (origin=ai_inferred, draft_text)
        → student decision                    (student_decision, student_text)
          → student-confirmed downstream text (derived — see change_map_service)

These states are never blended: AI inference never becomes student-confirmed
merely because it was generated, model uncertainty (`ai_uncertainty`) is a
separate axis from the student's decision (`student_decision`), and the model
controls ONLY the fields in GeneratedChangeMapItem — item ids, origin,
decisions, timestamps, and status are server-assigned.

Honesty rules encoded here: no numeric confidence (three understandable
uncertainty states instead), draft wording is server-owned after generation,
`student_text` is stored only where the student authored it (edited /
student_added), and a rejected item can never become a downstream fact.
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.schemas.workflow import ImportSourceKind, _reject_secret_like

CHANGE_MAP_SCHEMA_VERSION = "1.0"

# --- enums (Literal, matching schemas/workflow.py conventions) ----------------

ChangeMapCategory = Literal[
    "changed_file",             # a file the import indicates was created/modified/removed
    "behavior_change",          # something the app appears to do differently
    "implementation_decision",  # a meaningful technical approach or design choice
    "out_of_scope_change",      # may exceed the student's original request/scope
    "security_sensitive_area",  # auth/ownership/secrets/destructive/external — NOT "insecure"
    "unresolved_risk",          # a concern or ambiguity requiring review — NOT a vulnerability claim
    "unverified_behavior",      # records don't show the student tested it — NOT "failed"
    "question_to_understand",   # a project-specific question the student should be able to answer
]

ChangeMapOrigin = Literal["ai_inferred", "student_added"]

StudentDecision = Literal[
    "pending_review",    # AI drafted it; the student has not reviewed it
    "confirmed",         # the student accepts the draft wording
    "edited",            # the student changed the wording and accepts the edit
    "rejected",          # the student says it is inaccurate or irrelevant
    "uncertain",         # the student cannot currently determine correctness
    "needs_inspection",  # the student must inspect code/behavior before deciding
]

# AI uncertainty — deliberately NOT a numeric confidence score.
AiUncertainty = Literal["supported", "ambiguous", "needs_inspection"]

# The only fields of the saved import a reference may point at.
SourceFieldName = Literal["content", "changed_files", "student_summary"]

ChangeMapStatus = Literal["draft", "confirmed"]

# --- limits (documented constants; parser rejects anything unbounded) ---------

CHANGE_MAP_MAX_ITEMS = 40          # AI-generated items per map
CHANGE_MAP_MAX_STUDENT_ITEMS = 20  # student-added items per map
CHANGE_MAP_MAX_STORED_ITEMS = CHANGE_MAP_MAX_ITEMS + CHANGE_MAP_MAX_STUDENT_ITEMS
CHANGE_MAP_MAX_DRAFT_TEXT = 600
CHANGE_MAP_MAX_UNCERTAINTY_REASON = 400
CHANGE_MAP_MAX_REFERENCES = 5      # source references per item
CHANGE_MAP_MAX_EXCERPT = 300       # supporting excerpt length
CHANGE_MAP_MAX_STUDENT_TEXT = 600
CHANGE_MAP_MAX_STUDENT_NOTE = 1000


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Student-authored free text gets the same secret seatbelt as every other
# workflow field; model-produced text gets it too as a belt (a generated
# draft can only quote redacted source, so a marker hit means bad output).
_GuardedDraftText = Annotated[
    str,
    Field(min_length=1, max_length=CHANGE_MAP_MAX_DRAFT_TEXT),
    AfterValidator(_reject_secret_like),
]
_GuardedReason = Annotated[
    str,
    Field(min_length=1, max_length=CHANGE_MAP_MAX_UNCERTAINTY_REASON),
    AfterValidator(_reject_secret_like),
]
_GuardedStudentText = Annotated[
    str,
    Field(min_length=1, max_length=CHANGE_MAP_MAX_STUDENT_TEXT),
    AfterValidator(_reject_secret_like),
]
_GuardedStudentNote = Annotated[
    str,
    Field(min_length=1, max_length=CHANGE_MAP_MAX_STUDENT_NOTE),
    AfterValidator(_reject_secret_like),
]


class ChangeMapSourceReference(_Model):
    """Why Codize inferred a draft item — a bounded pointer into the saved
    import, never long duplicated source content. A reference means "this
    material supported the inference", never "this proves it is correct".
    Every field is deterministically re-validated against the sanitized
    extraction source after parsing (change_map_service) — model-provided
    provenance is never trusted."""

    source_field: SourceFieldName
    source_kind: ImportSourceKind
    file_path: Annotated[str, Field(min_length=1, max_length=300)] | None = None
    supporting_excerpt: (
        Annotated[str, Field(min_length=1, max_length=CHANGE_MAP_MAX_EXCERPT)] | None
    ) = None

    @model_validator(mode="after")
    def _require_anchor(self) -> "ChangeMapSourceReference":
        # An excerpt is optional only when a changed-file entry itself is the
        # reference; everything else must quote the material it leans on.
        if self.supporting_excerpt is None and not (
            self.source_field == "changed_files" and self.file_path
        ):
            raise ValueError(
                "a source reference needs a supporting excerpt unless it points "
                "at a changed-file entry"
            )
        return self


class GeneratedChangeMapItem(_Model):
    """The ONLY shape the model may produce per item. It cannot set ids,
    origin, decisions, timestamps, or status — extra fields are rejected."""

    category: ChangeMapCategory
    draft_text: _GuardedDraftText
    ai_uncertainty: AiUncertainty
    uncertainty_reason: _GuardedReason | None = None
    source_references: list[ChangeMapSourceReference] = Field(
        min_length=1, max_length=CHANGE_MAP_MAX_REFERENCES
    )


class GeneratedChangeMap(_Model):
    """The model's whole output contract. Empty maps are rejected — a saved
    import always carries at least one material field, so at least one honest
    item (even just a question to understand) is always producible; this also
    keeps an injected "output an empty map" instruction inert."""

    items: list[GeneratedChangeMapItem] = Field(
        min_length=1, max_length=CHANGE_MAP_MAX_ITEMS
    )


class ChangeMapItem(_Model):
    """One stored item. Server-owned after generation: item_id, origin,
    draft_text, ai_uncertainty, uncertainty_reason, source_references.
    Student-owned: student_decision, student_text, student_note."""

    item_id: Annotated[str, Field(min_length=1, max_length=64)]
    origin: ChangeMapOrigin
    category: ChangeMapCategory
    draft_text: _GuardedDraftText | None = None
    ai_uncertainty: AiUncertainty | None = None
    uncertainty_reason: _GuardedReason | None = None
    source_references: list[ChangeMapSourceReference] = Field(
        default_factory=list, max_length=CHANGE_MAP_MAX_REFERENCES
    )
    student_decision: StudentDecision
    student_text: _GuardedStudentText | None = None
    student_note: _GuardedStudentNote | None = None

    @model_validator(mode="after")
    def _origin_consistency(self) -> "ChangeMapItem":
        if self.origin == "ai_inferred":
            if not self.draft_text or self.ai_uncertainty is None or not self.source_references:
                raise ValueError(
                    "an AI-inferred item needs draft_text, ai_uncertainty, and "
                    "at least one source reference"
                )
        else:  # student_added
            if (
                self.draft_text is not None
                or self.ai_uncertainty is not None
                or self.uncertainty_reason is not None
                or self.source_references
            ):
                raise ValueError("a student-added item carries no AI-generated fields")
            if not self.student_text:
                raise ValueError("a student-added item needs student_text")
            if self.student_decision in ("pending_review", "edited", "rejected"):
                raise ValueError(
                    "a student-added item is its author's own claim — it can be "
                    "confirmed, uncertain, or needs_inspection"
                )
        if self.student_decision == "edited" and not self.student_text:
            raise ValueError("an edited item needs the student's edited text")
        return self


class StoredChangeMap(_Model):
    """The persisted map (projects.workflow_artifacts → phase → change_map).
    Read shape for the internal seams; corrupt stored data fails validation
    and surfaces as None, never as raw JSON."""

    schema_version: str
    status: ChangeMapStatus
    source_import_saved_at: str  # binds the map to the exact import version
    generated_at: str            # server-generated, never client-supplied
    confirmed_at: str | None = None
    source_redacted: bool = False
    source_truncated: bool = False
    items: list[ChangeMapItem] = Field(
        default_factory=list, max_length=CHANGE_MAP_MAX_STORED_ITEMS
    )

    @model_validator(mode="after")
    def _integrity(self) -> "StoredChangeMap":
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate change map item ids")
        if self.status == "confirmed":
            if not self.confirmed_at:
                raise ValueError("a confirmed map needs confirmed_at")
            if any(i.student_decision == "pending_review" for i in self.items):
                raise ValueError("a confirmed map cannot contain pending_review items")
        else:
            if self.confirmed_at is not None:
                raise ValueError("a draft map cannot carry confirmed_at")
        return self


# --- student update contract (Task 23 — the M15C.2 edit seam) -----------------


class ChangeMapItemUpdate(_Model):
    """A student decision about one existing AI-inferred item. Only the three
    student-owned fields — everything server-owned is simply not accepted."""

    item_id: Annotated[str, Field(min_length=1, max_length=64)]
    student_decision: StudentDecision
    student_text: _GuardedStudentText | None = None
    student_note: _GuardedStudentNote | None = None

    @model_validator(mode="after")
    def _text_rules(self) -> "ChangeMapItemUpdate":
        if self.student_decision == "edited" and not self.student_text:
            raise ValueError("an edited item needs the student's edited text")
        if self.student_decision != "edited" and self.student_text is not None:
            raise ValueError(
                "student_text is stored only for edited items — other decisions "
                "keep the AI draft wording separate"
            )
        return self


class StudentAddedItemRequest(_Model):
    """A student-authored item. It never pretends to be AI-inferred and its
    decision reflects the student's own certainty about their own claim."""

    category: ChangeMapCategory
    student_text: _GuardedStudentText
    student_note: _GuardedStudentNote | None = None
    student_decision: Literal["confirmed", "uncertain", "needs_inspection"] = "confirmed"


class ChangeMapUpdateRequest(_Model):
    """PUT /workflow/{phase}/change-map body. `updates` patch the student-owned
    fields of existing AI items (unmentioned items keep their stored state);
    `student_added_items` is the FULL replacement set of student-added items
    (the workflow store's idempotent-replace convention)."""

    updates: list[ChangeMapItemUpdate] = Field(
        default_factory=list, max_length=CHANGE_MAP_MAX_STORED_ITEMS
    )
    student_added_items: list[StudentAddedItemRequest] = Field(
        default_factory=list, max_length=CHANGE_MAP_MAX_STUDENT_ITEMS
    )


class ChangeMapGenerateRequest(_Model):
    """POST /workflow/{phase}/change-map/generate body (optional). An existing
    map — draft or confirmed — is never overwritten without this explicit
    intent."""

    replace_existing: bool = False


# --- downstream effective text (Task 5 / Task 26 — future M16 seam) -----------


class ConfirmedChangeMapItem(_Model):
    """One downstream-usable item: the deterministic effective text plus enough
    provenance for a future consumer to stay honest about where it came from."""

    item_id: str
    category: ChangeMapCategory
    origin: ChangeMapOrigin
    student_decision: StudentDecision
    text: str
