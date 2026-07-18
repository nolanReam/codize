"""Roadmap service tests — generation rules, persistence, and the fail-closed
structure validator, all against the in-memory fake repo and the stub LLM."""

import asyncio
import copy
import json

import pytest

from app.services import roadmap_service, template_service
from app.services.llm_service import LLMError, LLMService, StubProvider
from app.services.roadmap_service import (
    RoadmapAlreadyGeneratedError,
    RoadmapNotFoundError,
    RoadmapNotReadyError,
    build_prompt,
    generate_roadmap,
    get_roadmap,
    validate_roadmap_structure,
)
from tests.fakes import InMemoryProjectRepository

USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_USER = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

INTAKE_FIELDS = {
    "intake_purpose": "Help my volleyball league track scores so organizers stop using paper.",
    "intake_scope": "A REST backend exposing match stats through HTTP endpoints.",
    "intake_stack": "Python and FastAPI",
    "intake_self_assessment": "Sometimes, depends",
    "intake_timeline": "About six weeks",
}


def run(coro):
    return asyncio.run(coro)


def stub_llm() -> LLMService:
    return LLMService([StubProvider()])


def seed_project(repo, user=USER, archetype_id=2, **overrides):
    fields = {**INTAKE_FIELDS,
              "intake_completed_at": "2026-07-02T00:00:00+00:00",
              "archetype_id": archetype_id, **overrides}
    return run(repo.create_project(user, fields))


class FailingProvider:
    name = "failing"

    async def complete(self, prompt: str, temperature: float) -> str:
        raise LLMError("provider down")


class BadJSONProvider:
    name = "badjson"

    async def complete(self, prompt: str, temperature: float) -> str:
        return "this is not JSON at all"


class DriftingProvider:
    """Returns valid JSON that drops the final security-checklist phase."""

    name = "drifting"

    async def complete(self, prompt: str, temperature: float) -> str:
        raw = await StubProvider().complete(prompt, temperature)
        roadmap = json.loads(raw)
        roadmap["phases"] = roadmap["phases"][:-1]
        return json.dumps(roadmap)


class ExclusionBreakingProvider:
    """Keeps the shape but invents a forbidden product capability."""

    name = "exclusion-breaking"

    async def complete(self, prompt: str, temperature: float) -> str:
        raw = await StubProvider().complete(prompt, temperature)
        roadmap = json.loads(raw)
        roadmap["phases"][0]["ai_appropriate_tasks"][0] = (
            "Add an OpenAI model provider and API key"
        )
        return json.dumps(roadmap)


# --- generation preconditions ----------------------------------------------------

def test_cannot_generate_before_any_intake():
    repo = InMemoryProjectRepository()
    with pytest.raises(RoadmapNotReadyError):
        run(generate_roadmap(repo, stub_llm(), USER))


def test_cannot_generate_before_intake_completion():
    repo = InMemoryProjectRepository()
    run(repo.create_project(USER, {**INTAKE_FIELDS}))  # answers but not completed
    with pytest.raises(RoadmapNotReadyError):
        run(generate_roadmap(repo, stub_llm(), USER))


def test_cannot_generate_without_archetype_id():
    repo = InMemoryProjectRepository()
    seed_project(repo, archetype_id=None)
    with pytest.raises(RoadmapNotReadyError, match="archetype"):
        run(generate_roadmap(repo, stub_llm(), USER))


def test_cannot_generate_twice():
    repo = InMemoryProjectRepository()
    seed_project(repo)
    run(generate_roadmap(repo, stub_llm(), USER))
    with pytest.raises(RoadmapAlreadyGeneratedError):
        run(generate_roadmap(repo, stub_llm(), USER))


# --- template selection and structure preservation --------------------------------

@pytest.mark.parametrize("archetype_id", [1, 2, 3])
def test_loads_correct_template_and_preserves_structure(archetype_id):
    repo = InMemoryProjectRepository()
    seed_project(repo, archetype_id=archetype_id)
    result = run(generate_roadmap(repo, stub_llm(), USER))
    roadmap = result["roadmap"]
    template = template_service.get_template(archetype_id)

    assert result["archetype_id"] == archetype_id
    assert roadmap["archetype_id"] == archetype_id
    # Phase count, order, numbers, and titles all match the source template.
    assert [p["phase"] for p in roadmap["phases"]] == [p["phase"] for p in template["phases"]]
    assert [p["phase_title"] for p in roadmap["phases"]] == [
        p["phase_title"] for p in template["phases"]
    ]
    for gen, tpl in zip(roadmap["phases"], template["phases"]):
        assert gen["gate_depth"] == tpl["gate_depth"]
        assert gen["unlock_condition"] == tpl["unlock_condition"]
        assert len(gen["explanation_gate_targets"]) == len(tpl["explanation_gate_targets"])
        assert len(gen["ai_appropriate_tasks"]) == len(tpl["ai_appropriate_tasks"])
        assert len(gen["human_required_tasks"]) == len(tpl["human_required_tasks"])
    assert roadmap["phases"][-1]["phase_title"] == "Pre-Deployment Security Checklist"


def test_successful_generation_stores_roadmap_and_flips_status():
    repo = InMemoryProjectRepository()
    seed_project(repo)
    result = run(generate_roadmap(repo, stub_llm(), USER))
    project = run(repo.get_project(USER))
    assert project["status"] == "active"
    assert project["roadmap"] == result["roadmap"]
    assert result["status"] == "active"


@pytest.mark.parametrize("provider", [FailingProvider, BadJSONProvider, DriftingProvider])
def test_personalization_failure_falls_back_to_valid_template_roadmap(provider):
    """M13C.1B: a provider error, unparseable output, or structural drift must
    NOT block the student. Codize discards the bad LLM output and falls back to
    a valid template-backed roadmap; the project becomes active."""
    repo = InMemoryProjectRepository()
    seed_project(repo, archetype_id=2)
    result = run(generate_roadmap(repo, LLMService([provider()]), USER))

    template = template_service.get_template(2)
    # The stored structure is fully valid — invalid LLM output was never stored.
    assert validate_roadmap_structure(result["roadmap"], template) == []
    assert result["status"] == "active"
    project = run(repo.get_project(USER))
    assert project["status"] == "active"
    assert project["roadmap"] == result["roadmap"]
    # DriftingProvider drops the final phase; the fallback keeps all of them.
    assert len(result["roadmap"]["phases"]) == len(template["phases"])
    assert result["roadmap"]["phases"][-1]["phase_title"] == "Pre-Deployment Security Checklist"


def test_fallback_equals_deterministic_builder_and_weaves_in_purpose():
    repo = InMemoryProjectRepository()
    project = seed_project(repo, archetype_id=1)
    result = run(generate_roadmap(repo, LLMService([FailingProvider()]), USER))
    template = template_service.get_template(1)
    assert result["roadmap"] == roadmap_service.build_fallback_roadmap(template, project)
    blob = json.dumps(result["roadmap"])
    assert "[PROJECT_PURPOSE]" not in blob  # no raw placeholder tokens leak
    assert "[PROJECT_SCALE]" not in blob
    assert "volleyball" in blob  # the intake purpose is woven into the wording


@pytest.mark.parametrize("archetype_id", [1, 2, 3])
def test_build_fallback_roadmap_passes_existing_validation(archetype_id):
    repo = InMemoryProjectRepository()
    project = seed_project(repo, archetype_id=archetype_id)
    template = template_service.get_template(archetype_id)
    fallback = roadmap_service.build_fallback_roadmap(template, project)
    assert validate_roadmap_structure(fallback, template) == []
    assert fallback["phases"][-1]["phase_title"] == "Pre-Deployment Security Checklist"
    assert isinstance(fallback["timeline_estimate"], str) and fallback["timeline_estimate"].strip()


def test_unsupported_archetype_fails_safely_without_storing():
    """No template for the archetype → controlled failure, nothing stored, no
    fabricated fallback (safe failure preserved)."""
    repo = InMemoryProjectRepository()
    seed_project(repo, archetype_id=99)  # never produced by classification
    with pytest.raises(RoadmapNotReadyError):
        run(generate_roadmap(repo, stub_llm(), USER))
    project = run(repo.get_project(USER))
    assert project["status"] == "intake"
    assert project["roadmap"] is None


def test_fallback_response_leaks_no_validator_internals():
    """The fallback path returns a normal roadmap — no drift descriptions,
    validator prompts, or stack traces reach the caller."""
    repo = InMemoryProjectRepository()
    seed_project(repo, archetype_id=2)
    result = run(generate_roadmap(repo, LLMService([DriftingProvider()]), USER))
    blob = json.dumps(result)
    for leak in ("Traceback", "drifted", "failed structure validation", "phase keys changed"):
        assert leak not in blob


def test_get_roadmap_before_generation_is_not_found():
    repo = InMemoryProjectRepository()
    seed_project(repo)
    with pytest.raises(RoadmapNotFoundError):
        run(get_roadmap(repo, USER))


def test_users_roadmaps_are_isolated():
    repo = InMemoryProjectRepository()
    seed_project(repo, USER)
    run(generate_roadmap(repo, stub_llm(), USER))
    with pytest.raises(RoadmapNotFoundError):
        run(get_roadmap(repo, OTHER_USER))
    with pytest.raises(RoadmapNotReadyError):  # B has no completed intake either
        run(generate_roadmap(repo, stub_llm(), OTHER_USER))


# --- prompt assembly ---------------------------------------------------------------

def test_prompt_contains_template_and_verbatim_answers_with_no_placeholders():
    repo = InMemoryProjectRepository()
    project = seed_project(repo)
    template = template_service.get_template(2)
    prompt = build_prompt(template, project)
    assert "{{" not in prompt  # every backend placeholder filled
    for answer in INTAKE_FIELDS.values():
        assert answer in prompt  # intake answers injected verbatim
    assert json.dumps(template, indent=2) in prompt


# --- structure validator: every drift category fails closed ------------------------

def valid_roadmap(archetype_id=2) -> tuple[dict, dict]:
    template = template_service.get_template(archetype_id)
    roadmap = copy.deepcopy(template)
    roadmap["timeline_estimate"] = "Six weeks, roughly one phase per week."
    return roadmap, template


def test_validator_accepts_untampered_roadmap():
    roadmap, template = valid_roadmap()
    assert validate_roadmap_structure(roadmap, template) == []
    roadmap["stack_warning"] = "Honest paragraph about the gap."  # optional field allowed
    assert validate_roadmap_structure(roadmap, template) == []


def tamper_cases():
    def missing_phase(r):
        r["phases"].pop(3)

    def extra_phase(r):
        r["phases"].append(copy.deepcopy(r["phases"][-1]))

    def reordered_phases(r):
        r["phases"][0], r["phases"][1] = r["phases"][1], r["phases"][0]

    def changed_phase_number(r):
        r["phases"][2]["phase"] = 99

    def dropped_gate_target(r):
        r["phases"][0]["explanation_gate_targets"].pop()

    def added_gate_target(r):
        r["phases"][0]["explanation_gate_targets"].append("an easier extra target")

    def changed_gate_depth(r):
        r["phases"][2]["gate_depth"] = "light"  # heavy in the template

    def changed_unlock_condition(r):
        r["phases"][0]["unlock_condition"] = "phase completion"

    def removed_functional_unlock(r):
        r["phases"][0]["functional_unlock"] = ""

    def task_moved_between_lists(r):
        r["phases"][0]["ai_appropriate_tasks"].append(
            r["phases"][0]["human_required_tasks"].pop()
        )

    def wrong_archetype_id(r):
        r["archetype_id"] = 4

    def note_constraint_removed(r):
        # Archetype 2 phase 3 carries a verbatim NOTE: security constraint.
        r["phases"][2]["human_required_tasks"][2] = "Decide where each key is used."

    def rls_first_task_altered(r):
        r["phases"][2]["human_required_tasks"][0] = "Enable RLS when convenient."

    def missing_timeline_estimate(r):
        del r["timeline_estimate"]

    def unexpected_top_level_field(r):
        r["bonus_phase_pack"] = {}

    return [
        missing_phase, extra_phase, reordered_phases, changed_phase_number,
        dropped_gate_target, added_gate_target, changed_gate_depth,
        changed_unlock_condition, removed_functional_unlock,
        task_moved_between_lists, wrong_archetype_id, note_constraint_removed,
        rls_first_task_altered, missing_timeline_estimate,
        unexpected_top_level_field,
    ]


@pytest.mark.parametrize("tamper", tamper_cases(), ids=lambda f: f.__name__)
def test_validator_rejects_every_drift_category(tamper):
    roadmap, template = valid_roadmap()
    tamper(roadmap)
    assert validate_roadmap_structure(roadmap, template) != []


def test_validator_allows_personalized_wording():
    roadmap, template = valid_roadmap()
    roadmap["phases"][0]["core_concept"] = "REST semantics for your volleyball league tracker"
    roadmap["phases"][0]["functional_unlock"] = (
        "Pre-configured FastAPI skeleton matching your league's resource list"
    )
    roadmap["phases"][0]["explanation_gate_targets"][0] = (
        "Why these resources model your volleyball league, and what you left out"
    )
    assert validate_roadmap_structure(roadmap, template) == []


def test_studyflow_gets_a_strict_browser_only_roadmap_without_invented_systems():
    repo = InMemoryProjectRepository()
    project = seed_project(
        repo,
        archetype_id=3,
        intake_purpose="Help students keep homework and due dates organized.",
        intake_scope=(
            "A browser-based homework tracker where students add assignments with a title, "
            "subject, and due date; mark them complete; filter and delete them; and preserve "
            "them through browser local storage. No accounts. No backend. No database. "
            "No AI features. No notifications. No calendar integration."
        ),
        intake_stack="Plain HTML, CSS, JavaScript",
        intake_self_assessment=(
            "I get confused when AI generates several connected functions or changes multiple files."
        ),
    )
    result = run(generate_roadmap(repo, LLMService([FailingProvider()]), USER))
    roadmap = result["roadmap"]
    assert roadmap["archetype_id"] == 3
    assert roadmap["archetype_name"] == "Browser App"
    assert roadmap["default_stack"] == "Plain HTML + CSS + JavaScript"
    assert len(roadmap["phases"]) == 7
    serialized = json.dumps(roadmap).lower()
    for invented in (
        "llm", "model provider", "api key", "python", "fastapi", "backend",
        "database", "authentication", "conversation history", "calendar", "notification",
    ):
        assert invented not in serialized
    assert "local storage" in serialized
    assert run(repo.get_project(USER))["roadmap"] == roadmap
    assert project["roadmap"] is None


def test_browser_scope_drift_is_discarded_without_weakening_structure_validation():
    repo = InMemoryProjectRepository()
    seed_project(
        repo,
        archetype_id=3,
        intake_purpose="Help volunteers track shifts.",
        intake_scope=(
            "A browser app using local storage. No accounts. No backend. No database. "
            "No AI features."
        ),
        intake_stack="HTML, CSS, JavaScript",
    )
    result = run(generate_roadmap(repo, LLMService([ExclusionBreakingProvider()]), USER))
    serialized = json.dumps(result["roadmap"]).lower()
    assert "openai" not in serialized
    assert "api key" not in serialized
    assert "local storage" in serialized
