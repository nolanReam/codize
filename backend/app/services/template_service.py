"""Archetype template engine (Milestone 5).

Loads, validates, and serves the three hardcoded archetype JSON templates.
The template structure is fixed by the master spec: exactly three archetypes,
ids 1–3, phase structure immutable at runtime. There is no write API, callers
receive copies, and validation rejects any fourth archetype outright.

No LLM calls happen here. Classification is a temperature-0 LLM call in a
later milestone; only the spec's deterministic tiebreaker lives here.
"""

import copy
import json
from functools import lru_cache
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Fixed by the spec: exactly these three, ever. Filename → (id, name).
EXPECTED_TEMPLATES = {
    "archetype_1_ai_app.json": (1, "AI-Powered App"),
    "archetype_2_rest_api.json": (2, "REST API Backend"),
    "archetype_3_fullstack.json": (3, "Full-Stack Web App"),
}

TOP_LEVEL_KEYS = {"archetype_id", "archetype_name", "description", "default_stack", "phases"}
PHASE_KEYS = {
    "phase", "phase_title", "core_concept", "ai_appropriate_tasks",
    "human_required_tasks", "explanation_gate_targets", "gate_depth",
    "unlock_condition", "functional_unlock",
}
FINAL_PHASE_TITLE = "Pre-Deployment Security Checklist"

# Verbatim security constraints every template must carry (see
# scripts/validate_prebuild_artifacts.py for the full pre-build audit).
RLS_FIRST_TASK = (
    "Enable RLS on this table and write an ownership policy before continuing. "
    "Do not proceed until this is done."
)
AUTH_NOTE = (
    "Hiding this in the UI does not protect it. This check must happen here, "
    "in the backend, on every request."
)


class TemplateValidationError(RuntimeError):
    """A template file is missing, malformed, or violates a spec invariant."""


class UnknownArchetypeError(ValueError):
    """Requested archetype id is not one of 1, 2, 3."""


def _validate_template(name: str, data: dict, expected_id: int, expected_name: str,
                       errors: list[str]) -> None:
    missing = TOP_LEVEL_KEYS - set(data)
    if missing:
        errors.append(f"{name}: missing top-level fields {sorted(missing)}")
        return
    if data["archetype_id"] != expected_id:
        errors.append(f"{name}: archetype_id {data['archetype_id']!r} != {expected_id}")
    if data["archetype_name"] != expected_name:
        errors.append(f"{name}: archetype_name {data['archetype_name']!r} != {expected_name!r}")

    phases = data["phases"]
    if not isinstance(phases, list) or not phases:
        errors.append(f"{name}: phases must be a non-empty list")
        return

    for i, phase in enumerate(phases, start=1):
        pid = f"{name} phase {i}"
        if set(phase) != PHASE_KEYS:
            errors.append(f"{pid}: keys mismatch: {sorted(set(phase) ^ PHASE_KEYS)}")
            continue
        if phase["phase"] != i:
            errors.append(f"{pid}: phase number {phase['phase']!r} not sequential")
        if not 3 <= len(phase["explanation_gate_targets"]) <= 5:
            errors.append(f"{pid}: {len(phase['explanation_gate_targets'])} gate targets (need 3-5)")

    if phases[-1].get("phase_title") != FINAL_PHASE_TITLE:
        errors.append(f"{name}: final phase is not the {FINAL_PHASE_TITLE!r}")

    # Fixed security constraints, verbatim (encoded from Phase 1, never bolted on).
    rls_phases = [p for p in phases if RLS_FIRST_TASK in p.get("human_required_tasks", [])]
    if not rls_phases:
        errors.append(f"{name}: verbatim RLS-first task missing")
    elif any(p["human_required_tasks"][0] != RLS_FIRST_TASK for p in rls_phases):
        errors.append(f"{name}: RLS task is not the FIRST human-required task")
    if AUTH_NOTE not in json.dumps(data):
        errors.append(f"{name}: verbatim auth middleware NOTE missing")


def load_templates(directory: Path = TEMPLATES_DIR) -> dict[int, dict]:
    """Load and validate all templates; raise TemplateValidationError on any drift.

    Exactly three archetypes, ids 1/2/3 — a fourth template file or an
    unexpected archetype id is a validation error, never silently accepted.
    """
    errors: list[str] = []
    found = sorted(p.name for p in directory.glob("*.json"))
    if found != sorted(EXPECTED_TEMPLATES):
        errors.append(
            f"templates dir must hold exactly {sorted(EXPECTED_TEMPLATES)}, found {found}"
        )

    templates: dict[int, dict] = {}
    for fname, (aid, aname) in EXPECTED_TEMPLATES.items():
        path = directory / fname
        if not path.exists():
            continue  # already reported above
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{fname}: invalid JSON ({e})")
            continue
        _validate_template(fname, data, aid, aname, errors)
        templates[aid] = data

    if errors:
        raise TemplateValidationError(
            f"{len(errors)} template validation error(s): " + "; ".join(errors)
        )
    return templates


@lru_cache(maxsize=1)
def _store() -> dict[int, dict]:
    return load_templates()


def validate_at_startup() -> None:
    """Load the real templates once; called from create_app() to fail fast."""
    _store()


def list_archetypes() -> list[dict]:
    """Metadata for exactly the three archetypes (no phase bodies)."""
    return [
        {
            "archetype_id": t["archetype_id"],
            "archetype_name": t["archetype_name"],
            "description": t["description"],
            "default_stack": t["default_stack"],
            "phase_count": len(t["phases"]),
        }
        for _, t in sorted(_store().items())
    ]


def get_template(archetype_id: int) -> dict:
    """Full template for one archetype. Returns a copy — the stored templates
    can never be mutated through a caller."""
    store = _store()
    if archetype_id not in store:
        raise UnknownArchetypeError(f"Unknown archetype id: {archetype_id!r}")
    return copy.deepcopy(store[archetype_id])


def resolve_archetype(llm_api_is_core: bool, has_frontend_or_database: bool) -> int:
    """The spec's deterministic classification tiebreaker.

    The temperature-0 classification call (later milestone) extracts the two
    booleans; this mapping itself is fixed: LLM API as a core feature → 1,
    else frontend/database present → 3, else → 2.
    """
    if llm_api_is_core:
        return 1
    if has_frontend_or_database:
        return 3
    return 2
