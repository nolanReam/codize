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

import json
import re
from pathlib import Path

from app.services import llm_service, template_service
from app.services.llm_service import LLMService
from app.services.project_repository import ProjectRepository

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

    template = template_service.get_template(project["archetype_id"])
    prompt = build_prompt(template, project)
    try:
        raw = await llm.complete(prompt, temperature=ROADMAP_TEMPERATURE)
    except llm_service.LLMError as e:
        raise RoadmapGenerationError("Roadmap generation failed. Please try again.") from e

    roadmap = _parse_roadmap(raw)
    drift = validate_roadmap_structure(roadmap, template)
    if drift:
        # Fail closed: a structurally drifted roadmap is never stored.
        raise RoadmapGenerationError(
            "Generated roadmap failed structure validation and was discarded."
        )

    fields: dict = {"roadmap": roadmap, "status": "active"}
    if isinstance(roadmap.get("stack_warning"), str) and roadmap["stack_warning"].strip():
        fields["stack_warning"] = roadmap["stack_warning"]
    project = await repo.update_project(user_id, project["id"], fields)
    return _roadmap_response(project)
