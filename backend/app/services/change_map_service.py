"""Change Map extraction + lifecycle engine (Milestone 15C.1).

Converts a saved Implementation Import (M15A — student-provided, self-reported,
UNTRUSTED material) into an AI-generated, editable draft Change Map, and owns
the draft's lifecycle: student decision updates and confirmation. The map says,
in meaning, "this appears to be what changed — review and correct it"; it never
says the implementation is correct.

Safety order for generation, mirroring the M14B pattern:

    load typed import (workflow_service.get_implementation_import)
      → redact value-shaped secrets (reuses M14A redact_secrets), THEN truncate
        deterministically (redaction before truncation — a cut can never expose
        half a secret) → render inside an explicit untrusted-data boundary
      → one provider call at temperature 0 → strict fail-closed parse
      → deterministic provenance validation (source references must point at
        material that exists; excerpts must be exact substrings of the
        sanitized extraction view) + deterministic identifier grounding
        (reuses grounding_service.extract_grounding_terms — code-shaped names
        in draft text must appear in the supplied material)
      → at most one corrective regeneration, then the retryable 502 shape
        with nothing stored
      → server assigns item ids / origin / decisions / timestamps / status
        and persists via workflow_service.store_change_map (one column write).

The model controls ONLY GeneratedChangeMap fields. Raw import text never
appears in logs, errors, or corrective feedback. The gate, evaluator, unlocks,
and the M14 Defense Context are untouched — raw imports AND the Change Map
stay out of the defense pack by construction (fixed 8-source manifest).
Downstream integration (Review/Verification/Defense/Report) is deliberately
NOT wired: future M16 consumers use confirmed_items()/unresolved_items().
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from app.schemas.change_map import (
    CHANGE_MAP_SCHEMA_VERSION,
    ChangeMapUpdateRequest,
    ConfirmedChangeMapItem,
    GeneratedChangeMap,
    StoredChangeMap,
)
from app.schemas.workflow import StoredImplementationImport
from app.services import grounding_service, llm_service, phase_service, workflow_service
from app.services.defense_context_service import REDACTION_MARKER, redact_secrets
from app.services.llm_service import LLMService
from app.services.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Extraction is analysis, not creativity — temperature 0, like classification
# and gate evaluation (prompts/README.md).
EXTRACTION_TEMPERATURE = 0.0

# One corrective regeneration after a validation rejection, then the retryable
# failure — bounded spend, same shape as the M14B grounding loop.
_MAX_GENERATION_ATTEMPTS = 2

# ---------------------------------------------------------------------------
# Extraction size budgets (characters — no tokenizer dependency, matching the
# M14A convention). Redaction ALWAYS runs before these cuts. Priority when
# material is large: student summary (highest value, effectively never cut at
# its own 4k field cap), then the changed-file list (whole entries only), then
# imported content (head + tail preserved — diff headers live at the top, and
# recent material often at the bottom; the middle is dropped with a visible
# marker). Worst case the rendered import block is ~36k chars, comfortably
# inside every configured provider's context window.
# ---------------------------------------------------------------------------

EXTRACTION_SUMMARY_CHARS = 4_000
EXTRACTION_CHANGED_FILES_CHARS = 12_000
EXTRACTION_CONTENT_CHARS = 20_000
_CONTENT_HEAD_FRACTION = 0.7  # of the content budget; the rest keeps the tail

EXTRACTION_TRUNCATION_MARKER = "\n[TRUNCATED — part of the imported material was omitted here]\n"
_NONE_PROVIDED = "(none provided)"

_IMPORT_BLOCK_HEADER = "=== BEGIN IMPORT (untrusted student-provided material) ==="
_IMPORT_BLOCK_FOOTER = "=== END IMPORT ==="
_SUMMARY_HEADER = "--- STUDENT SUMMARY (self-reported, not independently verified) ---"
_FILES_HEADER = "--- CHANGED FILES (self-reported, one per line) ---"
_CONTENT_HEADER = "--- IMPORTED CONTENT ---"

_GENERIC_FAILURE = "The Change Map could not be generated. Please try again."


class ChangeMapError(Exception):
    """Base for controlled change-map errors; messages are safe client strings."""


class ImportRequiredError(ChangeMapError):
    """No saved implementation import for this phase — nothing to extract from."""


class ChangeMapExistsError(ChangeMapError):
    """A map already exists and replace_existing was not set."""


class ChangeMapNotFoundError(ChangeMapError):
    """No Change Map exists for this phase."""


class ChangeMapStaleError(ChangeMapError):
    """The implementation import changed after this map was generated."""


class ChangeMapPendingItemsError(ChangeMapError):
    """Confirmation refused: items are still pending review."""


class ChangeMapAlreadyConfirmedError(ChangeMapError):
    """This map has already been confirmed."""


class InvalidChangeMapUpdateError(ChangeMapError):
    """The student update payload failed validation."""


class ChangeMapGenerationError(ChangeMapError):
    """The provider call failed or its output stayed invalid — nothing stored."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Extraction view — redacted, truncated, deterministic; NEVER mutates the
# student's stored import
# ---------------------------------------------------------------------------


@dataclass
class ExtractionView:
    """The sanitized view of one import that providers (and validation) see.
    Built from the typed M15A read seam; the stored artifact is untouched."""

    source_kind: str
    tool_name: str | None
    content: str | None
    changed_files: list[str] = field(default_factory=list)
    summary: str | None = None
    redacted: bool = False
    truncated: bool = False
    files_omitted: int = 0


def _safe_cut_point(text: str, pos: int) -> int:
    """A cut position that never splits the redaction marker and prefers a
    nearby newline (so diffs keep whole lines)."""
    marker_start = text.rfind(
        REDACTION_MARKER, max(0, pos - len(REDACTION_MARKER)), pos + len(REDACTION_MARKER)
    )
    if marker_start != -1 and marker_start < pos < marker_start + len(REDACTION_MARKER):
        pos = marker_start
    newline = text.rfind("\n", max(0, pos - 200), pos)
    if newline > 0:
        return newline
    return pos


def _truncate_tail(text: str, limit: int) -> tuple[str, bool]:
    """Keep the head of a text within `limit`, with a visible marker."""
    if len(text) <= limit:
        return text, False
    cut = _safe_cut_point(text, max(0, limit - len(EXTRACTION_TRUNCATION_MARKER)))
    return text[:cut] + EXTRACTION_TRUNCATION_MARKER, True


def _truncate_head_tail(text: str, limit: int) -> tuple[str, bool]:
    """Keep the beginning and the end of a large text (diff headers at the
    top, recent material at the bottom), dropping the middle with a visible
    marker."""
    if len(text) <= limit:
        return text, False
    budget = max(0, limit - len(EXTRACTION_TRUNCATION_MARKER))
    head_len = int(budget * _CONTENT_HEAD_FRACTION)
    tail_len = budget - head_len
    head_cut = _safe_cut_point(text, head_len)
    tail_start = len(text) - tail_len
    marker_start = text.find(REDACTION_MARKER, tail_start - len(REDACTION_MARKER), tail_start + len(REDACTION_MARKER))
    if marker_start != -1 and marker_start < tail_start < marker_start + len(REDACTION_MARKER):
        tail_start = marker_start + len(REDACTION_MARKER)
    newline = text.find("\n", tail_start, tail_start + 200)
    if newline != -1:
        tail_start = newline + 1
    return text[:head_cut] + EXTRACTION_TRUNCATION_MARKER + text[tail_start:], True


def build_extraction_view(imported: StoredImplementationImport) -> ExtractionView:
    """Redact (M14A patterns), THEN truncate deterministically. The order is
    load-bearing: secrets are gone before anything is cut, so a cut can never
    expose half a secret and no raw credential can reach a prompt, an excerpt,
    a log, or an error."""
    redacted_any = False
    truncated_any = False

    content = imported.content
    if content is not None:
        content, hit = redact_secrets(content)
        redacted_any = redacted_any or hit
        content, cut = _truncate_head_tail(content, EXTRACTION_CONTENT_CHARS)
        truncated_any = truncated_any or cut

    summary = imported.student_summary
    if summary is not None:
        summary, hit = redact_secrets(summary)
        redacted_any = redacted_any or hit
        summary, cut = _truncate_tail(summary, EXTRACTION_SUMMARY_CHARS)
        truncated_any = truncated_any or cut

    files: list[str] = []
    files_omitted = 0
    used = 0
    for index, entry in enumerate(imported.changed_files):
        cleaned, hit = redact_secrets(entry)
        redacted_any = redacted_any or hit
        if used + len(cleaned) + 1 > EXTRACTION_CHANGED_FILES_CHARS:
            # Whole entries only: everything from here on is omitted, visibly.
            files_omitted = len(imported.changed_files) - index
            truncated_any = True
            break
        files.append(cleaned)
        used += len(cleaned) + 1

    tool_name = imported.tool_name
    if tool_name is not None:
        tool_name, hit = redact_secrets(tool_name)
        redacted_any = redacted_any or hit

    return ExtractionView(
        source_kind=imported.source_kind,
        tool_name=tool_name,
        content=content,
        changed_files=files,
        summary=summary,
        redacted=redacted_any,
        truncated=truncated_any,
        files_omitted=files_omitted,
    )


def render_import_block(view: ExtractionView) -> str:
    """The deterministic, explicitly-delimited import block embedded in the
    extraction prompt. All three material sections always appear (missing ones
    say "(none provided)") so ordering and absence handling are fixed."""
    files_section = _NONE_PROVIDED
    if view.changed_files:
        files_section = "\n".join(view.changed_files)
        if view.files_omitted:
            files_section += (
                f"\n(TRUNCATED: {view.files_omitted} later file entries were omitted)"
            )
    lines = [
        _IMPORT_BLOCK_HEADER,
        f"source_kind: {view.source_kind}",
        f"tool_name: {view.tool_name or _NONE_PROVIDED}",
        _SUMMARY_HEADER,
        view.summary or _NONE_PROVIDED,
        _FILES_HEADER,
        files_section,
        _CONTENT_HEADER,
        view.content or _NONE_PROVIDED,
        _IMPORT_BLOCK_FOOTER,
    ]
    return "\n".join(lines)


def _fill(prompt: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        prompt = prompt.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", prompt)
    if leftover:  # programming error, not a client error
        raise RuntimeError(f"unfilled prompt placeholders: {leftover}")
    return prompt


def build_extraction_prompt(phase: dict, view: ExtractionView) -> str:
    """Fill change_map_extraction.md: phase identity (context only — never the
    whole roadmap, never intake, never gate transcripts, never the Defense
    Context, never identity data) plus the sanitized import block."""
    prompt = (PROMPTS_DIR / "change_map_extraction.md").read_text(encoding="utf-8")
    return _fill(prompt, {
        "PHASE_NUMBER": str(phase["phase"]),
        "PHASE_TITLE": str(phase["phase_title"]),
        "IMPORT_BLOCK": render_import_block(view),
    })


# ---------------------------------------------------------------------------
# Strict parse + deterministic validation of model output
# ---------------------------------------------------------------------------

_SCHEMA_ISSUE = "the response did not match the required schema"


def parse_generated(raw: str) -> GeneratedChangeMap | None:
    """Fail-closed parse of the model output (fence-tolerant, like the roadmap
    and evaluator parsers). Returns None on anything malformed — raw model
    output never surfaces anywhere."""
    text = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    try:
        return GeneratedChangeMap.model_validate(data)
    except ValidationError:
        return None


def _dedupe(generated: GeneratedChangeMap) -> GeneratedChangeMap:
    """Deterministic normalization of the parsed output: strip stray edge
    whitespace from excerpts and file paths (models add trailing spaces; edge
    whitespace carries no provenance value — the substring check itself stays
    exact, and the normalized form is what gets stored), then drop duplicate
    items (keep-first by category + draft text)."""
    for item in generated.items:
        for ref in item.source_references:
            if ref.supporting_excerpt is not None:
                stripped = ref.supporting_excerpt.strip()
                if stripped:  # never let a whitespace-only excerpt pass trivially
                    ref.supporting_excerpt = stripped
            if ref.file_path is not None:
                stripped = ref.file_path.strip()
                if stripped:
                    ref.file_path = stripped
    seen: set[tuple[str, str]] = set()
    items = []
    for item in generated.items:
        key = (item.category, item.draft_text)
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return GeneratedChangeMap(items=items)


def validate_generated(generated: GeneratedChangeMap, view: ExtractionView) -> list[str]:
    """Deterministic provenance + grounding validation. Model-provided
    provenance is never trusted; everything is checked against the sanitized
    extraction view — the exact material the model saw, from this project and
    phase only. Returns concise issue-category strings (never raw output or
    raw import material)."""
    issues: list[str] = []

    field_texts = {
        "content": view.content or "",
        "changed_files": "\n".join(view.changed_files),
        "student_summary": view.summary or "",
    }
    corpus = "\n".join(field_texts.values())
    corpus_lower = corpus.lower()

    for item in generated.items:
        for ref in item.source_references:
            if not field_texts[ref.source_field]:
                issues.append(
                    f"a source reference uses the {ref.source_field} field, "
                    "which this import does not contain"
                )
                continue
            if ref.source_kind != view.source_kind:
                issues.append("a source reference kind does not match the import")
            if ref.file_path is not None and ref.file_path not in corpus:
                issues.append("a source reference names a file not present in the material")
            if ref.supporting_excerpt is not None:
                if not ref.supporting_excerpt.strip():
                    # Whitespace is trivially a substring of indented code —
                    # it supports nothing.
                    issues.append("a supporting excerpt was empty or whitespace-only")
                elif ref.supporting_excerpt not in field_texts[ref.source_field]:
                    issues.append(
                        "a supporting excerpt was not found verbatim in the "
                        "referenced material"
                    )
                cleaned, hit = redact_secrets(ref.supporting_excerpt)
                if hit:
                    issues.append("a supporting excerpt contained credential-shaped content")

        # Identifier grounding (M14B spirit): every code-shaped name the draft
        # commits to must appear in the supplied material. Plain-language
        # statements carry no such names and pass on their references alone.
        claim_text = item.draft_text + (
            f"\n{item.uncertainty_reason}" if item.uncertainty_reason else ""
        )
        for term in grounding_service.extract_grounding_terms(claim_text):
            if term not in corpus_lower:
                issues.append(f"unsupported identifier: {term}")

    # Deduplicate issue strings deterministically (keep-first).
    seen: set[str] = set()
    unique = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            unique.append(issue)
    return unique


def corrective_feedback(issues: list[str]) -> str:
    """One-shot regeneration instruction. Carries only concise validation
    categories — never raw model output, never raw imported material, never
    credentials."""
    listed = "; ".join(issues[:10])
    return (
        "VALIDATION CORRECTION: your previous response was rejected "
        f"({listed}). Regenerate the full JSON object. Every supporting "
        "excerpt must be an exact character-for-character substring of the "
        "supplied material — quote ONE single line only, never join lines, "
        "and keep leading diff markers (+, -, spaces) exactly as they appear. "
        "Every referenced field must be present in the import, every file "
        "path and code-shaped name must appear in the supplied material, and "
        "the response must match the required schema exactly. If the material "
        "is sparse, return fewer, more cautious items in plain language."
    )


# ---------------------------------------------------------------------------
# Server-assigned stored shape
# ---------------------------------------------------------------------------


def _item_id(category: str, draft_text: str) -> str:
    """Deterministic, timestamp-free item id — stable for the same validated
    generation result."""
    digest = hashlib.sha256(f"{category}\n{draft_text}".encode("utf-8")).hexdigest()
    return f"cm-{digest[:12]}"


def _student_item_id(category: str, student_text: str) -> str:
    digest = hashlib.sha256(f"{category}\n{student_text}".encode("utf-8")).hexdigest()
    return f"sa-{digest[:12]}"


def _stored_from_generated(
    generated: GeneratedChangeMap, view: ExtractionView, import_saved_at: str
) -> dict:
    """The server owns everything the model must not control: ids, origin,
    decisions, timestamps, status, import binding, redaction/truncation
    metadata."""
    items = [
        {
            "item_id": _item_id(item.category, item.draft_text),
            "origin": "ai_inferred",
            "category": item.category,
            "draft_text": item.draft_text,
            "ai_uncertainty": item.ai_uncertainty,
            "uncertainty_reason": item.uncertainty_reason,
            "source_references": [
                ref.model_dump(mode="json") for ref in item.source_references
            ],
            "student_decision": "pending_review",
            "student_text": None,
            "student_note": None,
        }
        for item in generated.items
    ]
    stored = {
        "schema_version": CHANGE_MAP_SCHEMA_VERSION,
        "status": "draft",
        "source_import_saved_at": import_saved_at,
        "generated_at": _now_iso(),
        "confirmed_at": None,
        "source_redacted": view.redacted,
        "source_truncated": view.truncated,
        "items": items,
    }
    # Invariant check before anything persists — a bug here must fail loudly,
    # never store a shape the read seam would reject.
    StoredChangeMap.model_validate(stored)
    return stored


# ---------------------------------------------------------------------------
# Generation flow
# ---------------------------------------------------------------------------


async def _generate_validated(
    llm: LLMService, prompt: str, view: ExtractionView
) -> GeneratedChangeMap:
    """One provider call at temperature 0, strict parse, deterministic
    validation; at most one corrective regeneration. Exhaustion raises the
    retryable error with nothing stored — never a silent fallback to
    hallucinated output."""
    corrective: str | None = None
    for attempt in range(_MAX_GENERATION_ATTEMPTS):
        composed = prompt if corrective is None else f"{prompt}\n\n{corrective}"
        try:
            raw = await llm.complete(composed, EXTRACTION_TEMPERATURE)
        except llm_service.LLMError as exc:
            raise ChangeMapGenerationError(_GENERIC_FAILURE) from exc

        generated = parse_generated(raw)
        if generated is None:
            issues = [_SCHEMA_ISSUE]
        else:
            generated = _dedupe(generated)
            issues = validate_generated(generated, view)
        if not issues:
            return generated
        if attempt + 1 < _MAX_GENERATION_ATTEMPTS:
            corrective = corrective_feedback(issues)
            continue
        # Issue categories only — never raw output, never raw import material.
        logger.warning("change map generation rejected twice: %s", issues[:10])
        raise ChangeMapGenerationError(_GENERIC_FAILURE)
    raise ChangeMapGenerationError(_GENERIC_FAILURE)  # pragma: no cover


def _client_view(project: dict, phase_number: int, stored: StoredChangeMap) -> dict:
    view = stored.model_dump(mode="json")
    view["phase"] = phase_number
    view["stale"] = workflow_service.change_map_is_stale(project, phase_number, stored)
    return view


async def generate_change_map(
    repo: ProjectRepository,
    llm: LLMService,
    user_id: str,
    phase_number: int,
    replace_existing: bool = False,
) -> dict:
    """POST /workflow/{phase}/change-map/generate. Ownership by construction:
    the project loads through the same user_id-filtered path as every
    workspace service; the caller passes the authenticated identity only."""
    project = await phase_service.load_active_project(repo, user_id)
    phase = phase_service.require_phase(project, phase_number)

    imported = workflow_service.get_implementation_import(project, phase_number)
    if imported is None:
        raise ImportRequiredError(
            "Bring back implementation material for this phase before "
            "generating a Change Map."
        )

    existing = workflow_service.get_change_map(project, phase_number)
    if existing is not None and not replace_existing:
        raise ChangeMapExistsError(
            "A Change Map already exists for this phase — set replace_existing "
            "to true to regenerate it. Regenerating replaces the current map "
            "and its review decisions."
        )

    view = build_extraction_view(imported)  # redact → truncate; import untouched
    prompt = build_extraction_prompt(phase, view)
    generated = await _generate_validated(llm, prompt, view)
    stored = _stored_from_generated(generated, view, imported.saved_at or "")

    project = await workflow_service.store_change_map(
        repo, user_id, project, phase_number, stored
    )
    return _client_view(project, phase_number, StoredChangeMap.model_validate(stored))


async def create_manual_change_map(
    repo: ProjectRepository,
    user_id: str,
    phase_number: int,
) -> dict:
    """Create an empty student-authored recovery map without a provider call.

    The student must add at least one item before confirmation. No AI claim,
    source reference, downstream record, or readiness state is fabricated.
    Existing maps are never overwritten by this recovery seam.
    """
    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)
    imported = workflow_service.get_implementation_import(project, phase_number)
    if imported is None:
        raise ImportRequiredError(
            "Bring back implementation material for this phase before creating a Change Map."
        )
    if workflow_service.get_change_map(project, phase_number) is not None:
        raise ChangeMapExistsError(
            "A Change Map already exists for this phase. Keep it or use the explicit regeneration path."
        )

    extraction = build_extraction_view(imported)
    stored = {
        "schema_version": CHANGE_MAP_SCHEMA_VERSION,
        "status": "draft",
        "source_import_saved_at": imported.saved_at or "",
        "generated_at": _now_iso(),
        "confirmed_at": None,
        "source_redacted": extraction.redacted,
        "source_truncated": extraction.truncated,
        "items": [],
    }
    validated = StoredChangeMap.model_validate(stored)
    project = await workflow_service.store_change_map(
        repo, user_id, project, phase_number, stored
    )
    return _client_view(project, phase_number, validated)


# ---------------------------------------------------------------------------
# Student update flow (no LLM call)
# ---------------------------------------------------------------------------


def _safe_validation_message(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first["loc"]) or "body"
    return f"Invalid change map update ({loc}): {first['msg']}"


async def update_change_map(
    repo: ProjectRepository, user_id: str, phase_number: int, payload: dict
) -> dict:
    """PUT /workflow/{phase}/change-map. The client edits ONLY student-owned
    state: decisions/text/notes on existing AI items (by item id) and the full
    replacement set of student-added items. Server-owned provenance — draft
    text, references, uncertainty, origin, timestamps, metadata — is not
    accepted by the schema and is copied through from storage untouched. Any
    successful update returns the map to draft status: a decision change means
    the previous confirmation no longer describes the map."""
    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)

    stored = workflow_service.get_change_map(project, phase_number)
    if stored is None:
        raise ChangeMapNotFoundError(
            "No Change Map exists for this phase yet — generate one first."
        )

    try:
        request = ChangeMapUpdateRequest.model_validate(payload)
    except ValidationError as exc:
        raise InvalidChangeMapUpdateError(_safe_validation_message(exc))

    update_ids = [u.item_id for u in request.updates]
    if len(update_ids) != len(set(update_ids)):
        raise InvalidChangeMapUpdateError(
            "Invalid change map update: the same item appears more than once."
        )

    ai_items = {i.item_id: i for i in stored.items if i.origin == "ai_inferred"}
    for update in request.updates:
        item = ai_items.get(update.item_id)
        if item is None:
            raise InvalidChangeMapUpdateError(
                "Invalid change map update: an item id does not match an "
                "AI-inferred item in this map."
            )

    new_items: list[dict] = []
    updates_by_id = {u.item_id: u for u in request.updates}
    for item in stored.items:
        if item.origin != "ai_inferred":
            continue  # student-added items are rebuilt below (full replace)
        data = item.model_dump(mode="json")
        update = updates_by_id.get(item.item_id)
        if update is not None:
            data["student_decision"] = update.student_decision
            data["student_text"] = update.student_text
            data["student_note"] = update.student_note
        new_items.append(data)

    seen_student_ids: set[str] = set()
    for added in request.student_added_items:
        sid = _student_item_id(added.category, added.student_text)
        if sid in seen_student_ids:
            continue  # deterministic dedupe of identical student items
        seen_student_ids.add(sid)
        new_items.append({
            "item_id": sid,
            "origin": "student_added",
            "category": added.category,
            "draft_text": None,
            "ai_uncertainty": None,
            "uncertainty_reason": None,
            "source_references": [],
            "student_decision": added.student_decision,
            "student_text": added.student_text,
            "student_note": added.student_note,
        })

    updated = stored.model_dump(mode="json")
    updated["items"] = new_items
    updated["status"] = "draft"       # decisions changed → confirmation no longer stands
    updated["confirmed_at"] = None
    validated = StoredChangeMap.model_validate(updated)

    project = await workflow_service.store_change_map(
        repo, user_id, project, phase_number, updated
    )
    return _client_view(project, phase_number, validated)


# ---------------------------------------------------------------------------
# Confirmation flow (no LLM call — a pure state transition)
# ---------------------------------------------------------------------------


async def confirm_change_map(
    repo: ProjectRepository, user_id: str, phase_number: int
) -> dict:
    """POST /workflow/{phase}/change-map/confirm. Confirmation means "I
    reviewed this map and these unresolved items remain" — never "every item
    is correct". Rejected / uncertain / needs_inspection items may stand; only
    pending_review blocks. A stale map (the import changed after generation)
    cannot be confirmed."""
    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)

    stored = workflow_service.get_change_map(project, phase_number)
    if stored is None:
        raise ChangeMapNotFoundError(
            "No Change Map exists for this phase yet — generate one first."
        )
    if stored.status == "confirmed":
        raise ChangeMapAlreadyConfirmedError(
            "This Change Map has already been confirmed."
        )
    if workflow_service.change_map_is_stale(project, phase_number, stored):
        raise ChangeMapStaleError(
            "Your implementation material changed after this map was generated "
            "— regenerate the Change Map before confirming it."
        )
    pending = sum(1 for i in stored.items if i.student_decision == "pending_review")
    if not stored.items:
        raise ChangeMapPendingItemsError(
            "Add at least one change in your own words before confirming this manual Change Map."
        )
    if pending:
        raise ChangeMapPendingItemsError(
            f"{pending} item(s) are still pending review — decide on every "
            "item before confirming (uncertain and needs-inspection are "
            "honest decisions)."
        )

    updated = stored.model_dump(mode="json")
    updated["status"] = "confirmed"
    updated["confirmed_at"] = _now_iso()  # server-stamped, never client-supplied
    validated = StoredChangeMap.model_validate(updated)

    project = await workflow_service.store_change_map(
        repo, user_id, project, phase_number, updated
    )
    return _client_view(project, phase_number, validated)


# ---------------------------------------------------------------------------
# Deterministic downstream effective text (future M16 seams — NOT consumed yet)
# ---------------------------------------------------------------------------


def confirmed_items(change_map: StoredChangeMap) -> list[ConfirmedChangeMapItem]:
    """The items a future downstream consumer (M16) may treat as the student's
    reviewed statement of what changed, with deterministic effective text:

        confirmed      → draft_text (accepted AI wording)
        edited         → student_text
        student_added  → student_text (only when its own decision is confirmed)

    Rejected items are excluded forever; pending_review, uncertain, and
    needs_inspection items are NOT here — see unresolved_items. Origin rides
    along so downstream can stay honest about who authored each statement."""
    out: list[ConfirmedChangeMapItem] = []
    for item in change_map.items:
        if item.student_decision == "confirmed":
            text = item.student_text if item.origin == "student_added" else item.draft_text
        elif item.student_decision == "edited":
            text = item.student_text
        else:
            continue
        if text:
            out.append(ConfirmedChangeMapItem(
                item_id=item.item_id,
                category=item.category,
                origin=item.origin,
                student_decision=item.student_decision,
                text=text,
            ))
    return out


def unresolved_items(change_map: StoredChangeMap) -> list[ConfirmedChangeMapItem]:
    """Items the student flagged as uncertain or needs_inspection — cautious
    unresolved context for future consumers, never project facts. Effective
    text prefers the student's own wording when present."""
    out: list[ConfirmedChangeMapItem] = []
    for item in change_map.items:
        if item.student_decision not in ("uncertain", "needs_inspection"):
            continue
        text = item.student_text or item.draft_text
        if text:
            out.append(ConfirmedChangeMapItem(
                item_id=item.item_id,
                category=item.category,
                origin=item.origin,
                student_decision=item.student_decision,
                text=text,
            ))
    return out
