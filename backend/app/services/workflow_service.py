"""Workflow artifact store (Milestone 13B; implementation import added in M15A).

Durable storage for the student-authored v3 Build Loop sections
(prompt_builder, review_board, evidence, verification, and — since M15A —
implementation_import, the "Bring Back What Changed" material), phase-
scoped, in the projects.workflow_artifacts JSONB column (task_progress
precedent: outside the roadmap jsonb, so storing artifacts can never mutate
the fixed structure).

This module is STORAGE ONLY: no LLM call, no gate involvement, no report
generation. A write touches exactly one column — roadmap, task_progress, gate
state, unlocks, current_phase, and reconnection timestamps cannot change
through it (the service takes only the ProjectRepository, so it cannot reach
the others by construction). Implementation imports are stored inertly as
untrusted student-provided material: M15A performs no extraction, no
summarization, no correctness analysis, and does NOT feed raw imports into
the M14 Defense Context Pack (a future M15C/M16 milestone may add a
normalized Change Map through the spec-guardian process — never raw imports).

Eligibility mirrors the phase workspace: active project + roadmap
(phase_service.load_active_project), artifacts scoped to real roadmap phases
(phase_service.require_phase). Payloads are validated fail-closed against the
strict schemas in app.schemas.workflow, plus a total-size cap; unknown keys in
stored data are dropped on read (corruption defense, like task_progress).
"""

import copy
import json
from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.change_map import StoredChangeMap
from app.schemas.workflow import (
    SECTION_MODELS,
    StoredImplementationImport,
    StoredPromptBuilderArtifact,
)
from app.services import (
    evidence_service,
    phase_service,
    review_service,
    verification_service,
)
from app.services.project_repository import ProjectRepository

SECTIONS = tuple(SECTION_MODELS)
# prompt_builder, review_board, evidence, verification, implementation_import

# The Change Map (M15C.1) lives as a SIBLING key beside the five student
# sections inside the same per-phase map — same column, no migration — but it
# is NOT a workflow section: it is server-generated + lifecycle-managed, so
# the generic full-replace PUT must never accept it (it is not in
# SECTION_MODELS → 404 by construction) and _stored_sections filters it out of
# every section read, which also keeps it out of the M14 defense context
# (stored_sections is the only artifact feed into the pack builder).
CHANGE_MAP_KEY = "change_map"
PROMPT_HISTORY_KEY = "prompt_history"
MAX_PROMPT_HISTORY = 20
_MAX_PROMPT_WRITE_RETRIES = 3

# Belt over the per-field caps: one section, serialized, must stay small
# enough to render and to aggregate into a Project Defense Report. The
# implementation import (M15A) carries whole pasted diffs / AI responses, so
# it gets a larger belt — the per-field caps in schemas/workflow.py remain the
# authoritative limits; the belt only rejects grossly oversized bodies before
# validation.
MAX_SECTION_CHARS = 30_000
MAX_IMPORT_SECTION_CHARS = 100_000
_SECTION_CHAR_LIMITS = {"implementation_import": MAX_IMPORT_SECTION_CHARS}


class WorkflowError(Exception):
    """Base for controlled workflow-store errors; messages are safe client strings."""


class SectionNotFoundError(WorkflowError):
    """Section name is not one of the four workflow sections."""


class InvalidArtifactError(WorkflowError):
    """Payload failed validation or exceeds the size cap."""


class WorkflowConflictError(WorkflowError):
    """A bounded optimistic write could not preserve concurrent work."""


def _stored_sections(project: dict, phase_number: int) -> dict:
    """The stored section map for one phase — only well-formed, known sections
    survive the read (corruption defense)."""
    stored = project.get("workflow_artifacts")
    phase_map = stored.get(str(phase_number)) if isinstance(stored, dict) else None
    if not isinstance(phase_map, dict):
        return {}
    return {
        name: phase_map[name]
        for name in SECTIONS
        if isinstance(phase_map.get(name), dict)
    }


def _phase_view(project: dict, phase_number: int) -> dict:
    stored = _stored_sections(project, phase_number)
    # A raw dict is not enough to call an Import present. Formal Defense uses
    # the typed seam below, so the client-facing workflow view must apply the
    # same corruption boundary or global navigation can advertise downstream
    # readiness that the server will correctly refuse.
    if "implementation_import" in stored:
        imported = get_implementation_import(project, phase_number)
        if imported is None:
            stored.pop("implementation_import", None)
        else:
            stored["implementation_import"] = imported.model_dump(mode="json")
    # Review is the one additive section with a server-derived read view:
    # linked Change Map bindings/snapshots are persisted, while initialized /
    # stale are computed on read and can never be client-controlled.
    if "review_board" in stored:
        stored["review_board"] = review_service.review_board_view(
            project, phase_number
        )
    if "verification" in stored:
        stored["verification"] = verification_service.verification_view(
            project, phase_number
        )
    if "evidence" in stored:
        stored["evidence"] = evidence_service.evidence_view(project, phase_number)
    return {
        "phase": phase_number,
        "sections": {name: stored.get(name) for name in SECTIONS},
        # Top-level, deliberately NOT inside `sections`: the frontend counts
        # section values for its "N/5 captured" progress, and the change map
        # is not a student-captured section.
        "change_map": change_map_view(project, phase_number),
        "prompt_history": prompt_history_view(project, phase_number),
    }


def prompt_history_view(project: dict, phase_number: int) -> list[dict]:
    """Validated prior Prompts, newest last; corrupt entries are never exposed."""
    artifacts = project.get("workflow_artifacts")
    phase_map = artifacts.get(str(phase_number)) if isinstance(artifacts, dict) else None
    raw = phase_map.get(PROMPT_HISTORY_KEY) if isinstance(phase_map, dict) else None
    if not isinstance(raw, list):
        return []
    history: list[dict] = []
    for item in raw[-MAX_PROMPT_HISTORY:]:
        try:
            history.append(
                StoredPromptBuilderArtifact.model_validate(item).model_dump(mode="json")
            )
        except ValidationError:
            continue
    return history


def stored_sections(project: dict, phase_number: int) -> dict:
    """One phase's stored section map from an already-loaded project (only
    well-formed known sections survive) — shared with the defense context
    builder (M14A), which loads the project once itself. Read-only."""
    return _stored_sections(project, phase_number)


def get_implementation_import(
    project: dict, phase_number: int
) -> StoredImplementationImport | None:
    """Typed read seam for future M15C extraction: the normalized, validated
    implementation import for one phase from an already-loaded project, or
    None when absent or corrupt (corruption never surfaces raw stored data).

    The returned material is STUDENT-PROVIDED AND UNTRUSTED — self-reported
    project material, not verified, not proof of correctness. Any future LLM
    consumer must treat it as untrusted project data only and must never
    follow instructions embedded in it. Read-only; never touches the
    repository."""
    stored = _stored_sections(project, phase_number).get("implementation_import")
    if stored is None:
        return None
    try:
        return StoredImplementationImport.model_validate(stored)
    except ValidationError:
        return None


def _raw_change_map(project: dict, phase_number: int):
    stored = project.get("workflow_artifacts")
    phase_map = stored.get(str(phase_number)) if isinstance(stored, dict) else None
    if not isinstance(phase_map, dict):
        return None
    raw = phase_map.get(CHANGE_MAP_KEY)
    return raw if isinstance(raw, dict) else None


def get_change_map(project: dict, phase_number: int) -> StoredChangeMap | None:
    """Typed read seam (M15C.1; future M16 consumers): the validated Change
    Map for one phase from an already-loaded project, or None when absent or
    corrupt — corruption never surfaces raw stored data. Read-only."""
    raw = _raw_change_map(project, phase_number)
    if raw is None:
        return None
    try:
        return StoredChangeMap.model_validate(raw)
    except ValidationError:
        return None


def change_map_is_stale(
    project: dict, phase_number: int, change_map: StoredChangeMap
) -> bool:
    """Server-derived, deterministic, never client-controlled: the map is
    stale when the implementation import it was generated from is no longer
    the stored one (replaced after generation, or missing/corrupt)."""
    imported = get_implementation_import(project, phase_number)
    if imported is None:
        return True
    return (change_map.source_import_saved_at or "") != (imported.saved_at or "")


def change_map_view(project: dict, phase_number: int) -> dict | None:
    """The client-facing Change Map shape: the stored map plus the computed
    stale flag. Contains no raw import, no prompts, no provider output beyond
    the validated draft items themselves."""
    change_map = get_change_map(project, phase_number)
    if change_map is None:
        return None
    view = change_map.model_dump(mode="json")
    view["stale"] = change_map_is_stale(project, phase_number, change_map)
    return view


async def store_change_map(
    repo: ProjectRepository, user_id: str, project: dict, phase_number: int, data: dict
) -> dict:
    """Persist one phase's Change Map (same merge discipline as save_section:
    the write touches ONLY workflow_artifacts, and every other key in the
    phase map — the five student sections included — is preserved).
    Callers (change_map_service) validate `data` against StoredChangeMap
    before handing it over."""
    existing = project.get("workflow_artifacts")
    artifacts = dict(existing) if isinstance(existing, dict) else {}
    phase_map = artifacts.get(str(phase_number))
    phase_map = dict(phase_map) if isinstance(phase_map, dict) else {}
    phase_map[CHANGE_MAP_KEY] = copy.deepcopy(data)
    artifacts[str(phase_number)] = phase_map
    return await repo.update_project(
        user_id, project["id"], {"workflow_artifacts": artifacts}
    )


async def store_change_map_if_current(
    repo: ProjectRepository,
    user_id: str,
    project: dict,
    phase_number: int,
    data: dict,
) -> dict | None:
    """Store a map only when no concurrent artifact write has occurred."""
    existing = project.get("workflow_artifacts")
    expected = existing if isinstance(existing, dict) else {}
    artifacts = dict(expected)
    phase_map = artifacts.get(str(phase_number))
    phase_map = dict(phase_map) if isinstance(phase_map, dict) else {}
    phase_map[CHANGE_MAP_KEY] = copy.deepcopy(data)
    artifacts[str(phase_number)] = phase_map
    return await repo.update_workflow_artifacts_if_current(
        user_id, project["id"], expected, artifacts
    )


async def store_review_board(
    repo: ProjectRepository, user_id: str, project: dict, phase_number: int, data: dict
) -> dict:
    """Persist a validated manual or linked Review Board artifact.

    Same one-column merge discipline as every workflow write: sibling
    sections and the Change Map remain untouched. Review lifecycle/provenance
    validation lives in review_service; this function is storage only.
    """
    existing = project.get("workflow_artifacts")
    artifacts = dict(existing) if isinstance(existing, dict) else {}
    phase_map = artifacts.get(str(phase_number))
    phase_map = dict(phase_map) if isinstance(phase_map, dict) else {}
    phase_map["review_board"] = copy.deepcopy(data)
    artifacts[str(phase_number)] = phase_map
    return await repo.update_project(
        user_id, project["id"], {"workflow_artifacts": artifacts}
    )


async def store_verification(
    repo: ProjectRepository, user_id: str, project: dict, phase_number: int, data: dict
) -> dict:
    """Persist a validated manual or linked Verification artifact.

    Same one-column merge discipline as every workflow write: sibling
    sections, Review, and the Change Map remain untouched. Linked lifecycle
    and provenance validation live in verification_service.
    """
    existing = project.get("workflow_artifacts")
    artifacts = dict(existing) if isinstance(existing, dict) else {}
    phase_map = artifacts.get(str(phase_number))
    phase_map = dict(phase_map) if isinstance(phase_map, dict) else {}
    phase_map["verification"] = copy.deepcopy(data)
    artifacts[str(phase_number)] = phase_map
    return await repo.update_project(
        user_id, project["id"], {"workflow_artifacts": artifacts}
    )


async def store_evidence(
    repo: ProjectRepository, user_id: str, project: dict, phase_number: int, data: dict
) -> dict:
    """Persist validated manual or linked Evidence without touching siblings."""
    existing = project.get("workflow_artifacts")
    artifacts = dict(existing) if isinstance(existing, dict) else {}
    phase_map = artifacts.get(str(phase_number))
    phase_map = dict(phase_map) if isinstance(phase_map, dict) else {}
    phase_map["evidence"] = copy.deepcopy(data)
    artifacts[str(phase_number)] = phase_map
    return await repo.update_project(
        user_id, project["id"], {"workflow_artifacts": artifacts}
    )


async def get_phase_artifacts(
    repo: ProjectRepository, user_id: str, phase_number: int
) -> dict:
    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)
    return _phase_view(project, phase_number)


def _safe_validation_message(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first["loc"]) or "body"
    return f"Invalid workflow artifact ({loc}): {first['msg']}"


def _validate_prompt_assignment(project: dict, phase_number: int, task_id: str) -> None:
    """A new association may name only the server-selected current AI task."""
    if phase_number != project.get("current_phase"):
        raise InvalidArtifactError(
            "A Prompt can only be associated with the selected task in the current phase."
        )
    selection = phase_service.current_assignment_view(project)
    assignment = selection.get("assignment")
    if (
        selection.get("state") != "selected"
        or not isinstance(assignment, dict)
        or assignment.get("task_id") != task_id
        or assignment.get("owner") != "ai"
    ):
        raise InvalidArtifactError(
            "Select this current-phase AI task on Project Home before saving its Prompt."
        )


async def _store_prompt_builder(
    repo: ProjectRepository,
    user_id: str,
    project: dict,
    phase_number: int,
    stored_section: dict,
) -> dict:
    """CAS merge so assignment/history and every sibling workflow key survive."""
    for attempt in range(_MAX_PROMPT_WRITE_RETRIES):
        current = project if attempt == 0 else await phase_service.load_active_project(repo, user_id)
        phase_service.require_phase(current, phase_number)
        task_id = stored_section.get("assignment_task_id")
        if task_id is not None:
            _validate_prompt_assignment(current, phase_number, task_id)

        existing = current.get("workflow_artifacts")
        expected = copy.deepcopy(existing) if isinstance(existing, dict) else {}
        artifacts = copy.deepcopy(expected)
        raw_phase_map = artifacts.get(str(phase_number))
        phase_map = dict(raw_phase_map) if isinstance(raw_phase_map, dict) else {}

        history = prompt_history_view(current, phase_number)
        previous = phase_map.get("prompt_builder")
        if isinstance(previous, dict) and previous.get("assignment_task_id") != task_id:
            try:
                preserved = StoredPromptBuilderArtifact.model_validate(previous).model_dump(
                    mode="json"
                )
            except ValidationError:
                preserved = None
            if preserved is not None:
                identity = (preserved.get("saved_at"), preserved.get("assignment_task_id"))
                if not any(
                    (item.get("saved_at"), item.get("assignment_task_id")) == identity
                    for item in history
                ):
                    history.append(preserved)
        phase_map[PROMPT_HISTORY_KEY] = history[-MAX_PROMPT_HISTORY:]
        phase_map["prompt_builder"] = copy.deepcopy(stored_section)
        artifacts[str(phase_number)] = phase_map

        updated = await repo.update_workflow_artifacts_if_current(
            user_id, current["id"], expected, artifacts
        )
        if updated is not None:
            return {
                "phase": phase_number,
                "section": "prompt_builder",
                "artifact": copy.deepcopy(stored_section),
                "prompt_history": prompt_history_view(updated, phase_number),
            }
    raise WorkflowConflictError(
        "Workflow state changed in another tab. Reload Prompt Builder and save again."
    )


async def save_section(
    repo: ProjectRepository, user_id: str, phase_number: int, section: str, payload: dict
) -> dict:
    """Idempotent full-section replace: the payload becomes the section's new
    content (no merge semantics). The write touches ONLY workflow_artifacts."""
    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)

    model = SECTION_MODELS.get(section)
    if model is None:
        # Deliberately does not echo the submitted name back.
        raise SectionNotFoundError(
            f"Unknown workflow section. Valid sections: {', '.join(SECTIONS)}."
        )

    limit = _SECTION_CHAR_LIMITS.get(section, MAX_SECTION_CHARS)
    # Count the API's established Unicode code-point units, not the ASCII
    # escape expansion produced by json.dumps' default ensure_ascii=True.
    if len(json.dumps(payload, ensure_ascii=False)) > limit:
        raise InvalidArtifactError(
            f"This section is too large to save (max {limit // 1000} KB) — "
            "trim pasted output and try again."
        )

    # M16A.1 keeps the generic Review route for compatibility, but linked
    # Review provenance cannot use generic full-replace validation. The
    # dedicated service accepts the old payload unchanged plus student-only
    # target_updates and copies every server-owned field from storage.
    if section == "review_board":
        try:
            return await review_service.save_review_board(
                repo, user_id, project, phase_number, payload
            )
        except review_service.InvalidReviewUpdateError as exc:
            # Preserve the M13B service contract: invalid generic section PUTs
            # raise InvalidArtifactError, including the additive target path.
            raise InvalidArtifactError(str(exc))

    # M16B.1 follows the linked Review precedent: the existing manual
    # Verification payload remains valid, while target_updates may change only
    # future student-owned result fields. Source identity and suggestions are
    # always copied from storage.
    if section == "verification":
        try:
            return await verification_service.save_verification(
                repo, user_id, project, phase_number, payload
            )
        except verification_service.InvalidVerificationUpdateError as exc:
            raise InvalidArtifactError(str(exc))

    # M16B.3A applies the same additive pattern to Evidence. Manual payloads
    # remain full-section replacements; linked target updates can mutate only
    # student Evidence fields while source snapshots/bindings stay in storage.
    if section == "evidence":
        try:
            return await evidence_service.save_evidence(
                repo, user_id, project, phase_number, payload
            )
        except evidence_service.InvalidEvidenceUpdateError as exc:
            raise InvalidArtifactError(str(exc))

    try:
        artifact = model.model_validate(payload)
    except ValidationError as exc:
        raise InvalidArtifactError(_safe_validation_message(exc))

    stored_section = artifact.model_dump(mode="json")
    stored_section["saved_at"] = datetime.now(timezone.utc).isoformat()

    if section == "prompt_builder":
        return await _store_prompt_builder(
            repo, user_id, project, phase_number, stored_section
        )

    existing = project.get("workflow_artifacts")
    artifacts = dict(existing) if isinstance(existing, dict) else {}
    phase_map = artifacts.get(str(phase_number))
    phase_map = dict(phase_map) if isinstance(phase_map, dict) else {}
    phase_map[section] = stored_section
    artifacts[str(phase_number)] = phase_map

    project = await repo.update_project(
        user_id, project["id"], {"workflow_artifacts": artifacts}
    )
    return {
        "phase": phase_number,
        "section": section,
        "artifact": copy.deepcopy(stored_section),
    }
