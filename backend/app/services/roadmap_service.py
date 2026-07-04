"""Roadmap generation engine (Milestone 7).

The archetype's hardcoded JSON template is the structural source of truth. The
LLM personalizes wording only; this module validates the returned roadmap
against the source template and FAILS CLOSED on any structural drift — a
drifted roadmap is never stored and never reaches the student.

Flow: intake complete + archetype assigned → fill the roadmap_generation
prompt (template JSON + verbatim intake answers) → one LLM call at
temperature 0.7 (prompts/README.md) → parse → validate → persist roadmap
JSONB and flip projects.status 'intake' → 'active' in the same write. The
status flip therefore cannot happen unless generation succeeded.
"""

import copy
import json
import logging
import re
from pathlib import Path

from app.services import llm_service, template_service
from app.services.llm_service import LLMService
from app.services.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
ROADMAP_TEMPERATURE = 0.7  # fixed by prompts/README.md — roadmap_generation.md row

# Extra top-level fields the prompt tells the LLM to add. Nothing else may
# appear beyond the template's own keys.
REQUIRED_EXTRA_KEYS = {"timeline_estimate"}
OPTIONAL_EXTRA_KEYS = {"stack_warning"}

# Prompt placeholder → projects column (intake answers, verbatim).
_PROMPT_FIELDS = {
    "INTAKE_PURPOSE": "intake_purpose",
    "INTAKE_DESCRIPTION": "intake_scope",
    "INTAKE_STACK": "intake_stack",
    "INTAKE_SELF_ASSESSMENT": "intake_self_assessment",
    "INTAKE_DEADLINE": "intake_timeline",
}


class RoadmapError(Exception):
    """Base for controlled roadmap errors; messages are safe client strings."""


class RoadmapNotReadyError(RoadmapError):
    """Intake incomplete or no archetype assigned — generation refused."""


class RoadmapAlreadyGeneratedError(RoadmapError):
    """This project already has a roadmap."""


class RoadmapNotFoundError(RoadmapError):
    """No roadmap has been generated yet."""


class RoadmapGenerationError(RoadmapError):
    """The LLM call failed or its output drifted from the template."""


def build_prompt(template: dict, project: dict) -> str:
    """Fill roadmap_generation.md. Every {{PLACEHOLDER}} must be filled —
    sending an unfilled prompt is a programming error, not a client error."""
    prompt = (PROMPTS_DIR / "roadmap_generation.md").read_text(encoding="utf-8")
    prompt = prompt.replace(
        "{{ARCHETYPE_TEMPLATE_JSON}}", json.dumps(template, indent=2)
    )
    for placeholder, column in _PROMPT_FIELDS.items():
        prompt = prompt.replace(f"{{{{{placeholder}}}}}", project[column])
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", prompt)
    if leftover:
        raise RuntimeError(f"unfilled prompt placeholders: {leftover}")
    return prompt


def _parse_roadmap(raw: str) -> dict:
    """Parse the model output, tolerating a markdown code fence around it."""
    text = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*)\s*```$", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        roadmap = json.loads(text)
    except json.JSONDecodeError as e:
        raise RoadmapGenerationError("Roadmap generation failed. Please try again.") from e
    if not isinstance(roadmap, dict):
        raise RoadmapGenerationError("Roadmap generation failed. Please try again.")
    return roadmap


def validate_roadmap_structure(roadmap: dict, template: dict) -> list[str]:
    """Every structural invariant the LLM must not touch, checked against the
    source template. Returns a list of drift descriptions (empty = valid).

    Exact-equality fields: archetype_id/name, phase numbers, phase titles,
    gate_depth, unlock_condition — plus the verbatim security constraints
    (NOTE: sentences, the RLS-first task). Personalizable fields (concepts,
    task wording, gate-target wording, functional_unlock wording) are checked
    for presence, type, and count — a task can't move between the AI and human
    lists, and no gate target may be added or dropped.
    """
    errors: list[str] = []

    allowed = set(template) | REQUIRED_EXTRA_KEYS | OPTIONAL_EXTRA_KEYS
    extra = set(roadmap) - allowed
    if extra:
        errors.append(f"unexpected top-level fields {sorted(extra)}")
    missing = (set(template) | REQUIRED_EXTRA_KEYS) - set(roadmap)
    if missing:
        errors.append(f"missing top-level fields {sorted(missing)}")
        return errors

    if roadmap["archetype_id"] != template["archetype_id"]:
        errors.append(
            f"archetype_id changed: {roadmap['archetype_id']!r} != {template['archetype_id']!r}"
        )
    if roadmap["archetype_name"] != template["archetype_name"]:
        errors.append("archetype_name changed")

    phases = roadmap["phases"]
    tpl_phases = template["phases"]
    if not isinstance(phases, list) or len(phases) != len(tpl_phases):
        errors.append(
            f"phase count changed: {len(phases) if isinstance(phases, list) else 'not a list'}"
            f" != {len(tpl_phases)}"
        )
        return errors

    for gen, tpl in zip(phases, tpl_phases):
        pid = f"phase {tpl['phase']}"
        if not isinstance(gen, dict) or set(gen) != template_service.PHASE_KEYS:
            errors.append(f"{pid}: phase keys changed")
            continue
        # Fixed verbatim: identity, order, gate depth, unlock condition.
        if gen["phase"] != tpl["phase"]:
            errors.append(f"{pid}: phase number changed to {gen['phase']!r}")
        if gen["phase_title"] != tpl["phase_title"]:
            errors.append(f"{pid}: phase_title changed")
        if gen["gate_depth"] != tpl["gate_depth"]:
            errors.append(f"{pid}: gate_depth changed")
        if gen["unlock_condition"] != tpl["unlock_condition"]:
            errors.append(f"{pid}: unlock_condition changed")
        # Personalizable wording, fixed presence/count.
        if not (isinstance(gen["core_concept"], str) and gen["core_concept"].strip()):
            errors.append(f"{pid}: core_concept missing or empty")
        if not (isinstance(gen["functional_unlock"], str) and gen["functional_unlock"].strip()):
            errors.append(f"{pid}: functional_unlock missing or empty")
        for field in ("ai_appropriate_tasks", "human_required_tasks", "explanation_gate_targets"):
            gen_items = gen[field]
            if (not isinstance(gen_items, list)
                    or len(gen_items) != len(tpl[field])
                    or not all(isinstance(t, str) and t.strip() for t in gen_items)):
                errors.append(f"{pid}: {field} count or content changed")
        # Verbatim security constraints (spec: encoded from Phase 1, never
        # weakened by personalization).
        raw_tasks = gen["human_required_tasks"]
        gen_tasks = [t for t in raw_tasks if isinstance(t, str)] if isinstance(raw_tasks, list) else []
        for i, task in enumerate(tpl["human_required_tasks"]):
            if "NOTE:" in task:
                note = task[task.index("NOTE:"):]
                if i >= len(gen_tasks) or note not in gen_tasks[i]:
                    errors.append(f"{pid}: verbatim NOTE constraint missing from task {i + 1}")
        if tpl["human_required_tasks"][0] == template_service.RLS_FIRST_TASK:
            if not gen_tasks or gen_tasks[0] != template_service.RLS_FIRST_TASK:
                errors.append(f"{pid}: RLS-first task altered or displaced")

    if not errors and phases[-1]["phase_title"] != template_service.FINAL_PHASE_TITLE:
        errors.append("final phase is not the Pre-Deployment Security Checklist")

    if not isinstance(roadmap.get("timeline_estimate"), str) or not roadmap["timeline_estimate"].strip():
        errors.append("timeline_estimate missing or empty")

    return errors


# --- deterministic template fallback (M13C.1B) --------------------------------
#
# The LLM personalizes wording; the hardcoded template protects structure. When
# personalization fails (provider error, unparseable output, or structural
# drift), the student must not be blocked from the workspace — Codize builds a
# structurally valid roadmap straight from the archetype template instead.

_PLACEHOLDER_RE = re.compile(r"\[[A-Z][A-Z_]*\]")

# The ONLY phase fields that carry [PLACEHOLDER] slots (audited across all three
# templates). The fallback personalizes exactly these; the fields the validator
# checks for exact equality (phase number/title, gate_depth, unlock_condition)
# and the verbatim NOTE:/RLS-first security constraints are copied through
# untouched, so a fallback roadmap is valid by construction.
_PERSONALIZABLE_PHASE_FIELDS = (
    "core_concept",
    "functional_unlock",
    "ai_appropriate_tasks",
    "human_required_tasks",
    "explanation_gate_targets",
)

_MAX_PURPOSE_IN_TEMPLATE = 200  # keep the substituted purpose from bloating 20+ slots


def _personalize(text: str, purpose: str) -> str:
    text = text.replace("[PROJECT_PURPOSE]", purpose)
    # Any other slot (e.g. [PROJECT_SCALE]) → a neutral phrase; never leak a raw
    # bracket token to the student.
    return _PLACEHOLDER_RE.sub("your project", text)


def _fallback_timeline_estimate(project: dict) -> str:
    deadline = (project.get("intake_timeline") or "").strip()
    base = (
        "Codize built this roadmap from the verified archetype template. Work "
        "through the phases in order — each one gates on understanding, not speed."
    )
    return f'Your stated timeline: "{deadline}". {base}' if deadline else base


def build_fallback_roadmap(template: dict, project: dict) -> dict:
    """A deterministic, structurally valid roadmap built straight from the
    archetype template — no LLM, no network. Structure is the template's (so it
    always passes validate_roadmap_structure); wording is lightly personalized
    by substituting the verbatim intake purpose into the template's
    personalization slots. No hallucinated or unsupported requirements."""
    roadmap = copy.deepcopy(template)
    purpose = (project.get("intake_purpose") or "").strip() or "your project"
    if len(purpose) > _MAX_PURPOSE_IN_TEMPLATE:
        purpose = purpose[: _MAX_PURPOSE_IN_TEMPLATE - 1].rstrip() + "…"

    for phase in roadmap["phases"]:
        for field in _PERSONALIZABLE_PHASE_FIELDS:
            value = phase[field]
            if isinstance(value, str):
                phase[field] = _personalize(value, purpose)
            elif isinstance(value, list):
                phase[field] = [
                    _personalize(item, purpose) if isinstance(item, str) else item
                    for item in value
                ]
    roadmap["timeline_estimate"] = _fallback_timeline_estimate(project)
    return roadmap


async def _personalized_roadmap(
    template: dict, project: dict, llm: LLMService
) -> dict | None:
    """One LLM personalization attempt. Returns a roadmap that passed strict
    structure validation, or None when the provider failed, returned
    unparseable output, or drifted — each of which is a signal to fall back to
    the template, not an error to surface. A drifted roadmap is never stored."""
    prompt = build_prompt(template, project)  # a bad prompt is a programming error → raises
    try:
        raw = await llm.complete(prompt, temperature=ROADMAP_TEMPERATURE)
        candidate = _parse_roadmap(raw)
    except (llm_service.LLMError, RoadmapGenerationError) as exc:
        logger.warning(
            "roadmap personalization unavailable for project %s; using template fallback: %s",
            project.get("id"), exc,
        )
        return None

    drift = validate_roadmap_structure(candidate, template)
    if drift:
        # Log the drift detail for observability; it never reaches the client.
        logger.warning(
            "roadmap personalization drifted for project %s (archetype %s); "
            "using template fallback: %s",
            project.get("id"), project.get("archetype_id"), "; ".join(drift),
        )
        return None
    return candidate


def _roadmap_response(project: dict) -> dict:
    return {
        "roadmap": project["roadmap"],
        "archetype_id": project["archetype_id"],
        "status": project["status"],
    }


async def get_roadmap(repo: ProjectRepository, user_id: str) -> dict:
    project = await repo.get_project(user_id)
    if project is None or not project.get("roadmap"):
        raise RoadmapNotFoundError("No roadmap has been generated yet.")
    return _roadmap_response(project)


async def generate_roadmap(repo: ProjectRepository, llm: LLMService, user_id: str) -> dict:
    project = await repo.get_project(user_id)
    if project is None or not project.get("intake_completed_at"):
        raise RoadmapNotReadyError("Complete the five intake questions before generating a roadmap.")
    if not project.get("archetype_id"):
        raise RoadmapNotReadyError("This project has no archetype assigned.")
    if project.get("roadmap"):
        raise RoadmapAlreadyGeneratedError("A roadmap has already been generated for this project.")

    try:
        template = template_service.get_template(project["archetype_id"])
    except template_service.UnknownArchetypeError as e:
        # No template to personalize OR to fall back to — fail safely, store nothing.
        raise RoadmapNotReadyError("This project's archetype is not recognized.") from e

    # Personalize with the LLM; fall back to the verified template on any failure
    # or drift. Either way the stored roadmap is strictly validated — an invalid
    # structure is never persisted.
    roadmap = await _personalized_roadmap(template, project, llm)
    if roadmap is None:
        roadmap = build_fallback_roadmap(template, project)
        residual = validate_roadmap_structure(roadmap, template)
        if residual:
            # Impossible by construction; never store an invalid structure.
            logger.error(
                "template fallback roadmap invalid for archetype %s: %s",
                project.get("archetype_id"), "; ".join(residual),
            )
            raise RoadmapGenerationError("Roadmap generation failed. Please try again.")
        logger.info(
            "stored template-fallback roadmap for project %s (archetype %s)",
            project.get("id"), project.get("archetype_id"),
        )

    fields: dict = {"roadmap": roadmap, "status": "active"}
    if isinstance(roadmap.get("stack_warning"), str) and roadmap["stack_warning"].strip():
        fields["stack_warning"] = roadmap["stack_warning"]
    project = await repo.update_project(user_id, project["id"], fields)
    return _roadmap_response(project)
