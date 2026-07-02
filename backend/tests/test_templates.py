"""Template engine (service layer) tests — no HTTP, no LLM calls."""

import json
import shutil

import pytest

from app.services import template_service
from app.services.template_service import (
    TEMPLATES_DIR,
    TemplateValidationError,
    UnknownArchetypeError,
    get_template,
    list_archetypes,
    load_templates,
    resolve_archetype,
)

EXPECTED = {
    1: "AI-Powered App",
    2: "REST API Backend",
    3: "Full-Stack Web App",
}


def copy_templates(tmp_path):
    """Real templates copied to a scratch dir so tests can break them safely."""
    for f in TEMPLATES_DIR.glob("*.json"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


def rewrite(directory, fname, mutate):
    path = directory / fname
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


# --- loading -----------------------------------------------------------------

def test_all_three_templates_load():
    templates = load_templates()
    assert set(templates) == {1, 2, 3}
    for aid, name in EXPECTED.items():
        assert templates[aid]["archetype_name"] == name


def test_list_archetypes_returns_exactly_three():
    metas = list_archetypes()
    assert [m["archetype_id"] for m in metas] == [1, 2, 3]
    for meta in metas:
        assert meta["archetype_name"] == EXPECTED[meta["archetype_id"]]
        assert meta["default_stack"]
        assert meta["phase_count"] == 7
        assert "phases" not in meta  # metadata only


@pytest.mark.parametrize("archetype_id", [1, 2, 3])
def test_get_template_works_for_each_archetype(archetype_id):
    t = get_template(archetype_id)
    assert t["archetype_id"] == archetype_id
    assert t["archetype_name"] == EXPECTED[archetype_id]
    assert t["phases"][-1]["phase_title"] == "Pre-Deployment Security Checklist"


@pytest.mark.parametrize("bad_id", [0, 4, 99, -1])
def test_invalid_archetype_id_is_a_controlled_error(bad_id):
    with pytest.raises(UnknownArchetypeError):
        get_template(bad_id)


# --- immutability ------------------------------------------------------------

def test_templates_are_immutable_from_caller_perspective():
    t = get_template(1)
    t["archetype_name"] = "Tampered"
    t["phases"].pop()
    t["phases"][0]["human_required_tasks"].append("injected task")

    fresh = get_template(1)
    assert fresh["archetype_name"] == "AI-Powered App"
    assert len(fresh["phases"]) == 7
    assert "injected task" not in fresh["phases"][0]["human_required_tasks"]

    metas = list_archetypes()
    metas.pop()
    assert len(list_archetypes()) == 3


# --- validation --------------------------------------------------------------

def test_validation_catches_missing_top_level_field(tmp_path):
    d = copy_templates(tmp_path)
    rewrite(d, "archetype_2_rest_api.json", lambda t: t.pop("default_stack"))
    with pytest.raises(TemplateValidationError, match="default_stack"):
        load_templates(d)


def test_validation_catches_missing_phase_field(tmp_path):
    d = copy_templates(tmp_path)
    rewrite(d, "archetype_3_fullstack.json", lambda t: t["phases"][2].pop("gate_depth"))
    with pytest.raises(TemplateValidationError, match="gate_depth"):
        load_templates(d)


def test_validation_catches_non_sequential_phases(tmp_path):
    d = copy_templates(tmp_path)

    def swap(t):
        t["phases"][1]["phase"] = 5

    rewrite(d, "archetype_1_ai_app.json", swap)
    with pytest.raises(TemplateValidationError, match="not sequential"):
        load_templates(d)


def test_validation_catches_too_few_gate_targets(tmp_path):
    d = copy_templates(tmp_path)

    def strip_targets(t):
        t["phases"][0]["explanation_gate_targets"] = t["phases"][0]["explanation_gate_targets"][:2]

    rewrite(d, "archetype_1_ai_app.json", strip_targets)
    with pytest.raises(TemplateValidationError, match="gate targets"):
        load_templates(d)


def test_validation_catches_missing_final_checklist_phase(tmp_path):
    d = copy_templates(tmp_path)

    def rename_final(t):
        t["phases"][-1]["phase_title"] = "Deployment"

    rewrite(d, "archetype_2_rest_api.json", rename_final)
    with pytest.raises(TemplateValidationError, match="Pre-Deployment Security Checklist"):
        load_templates(d)


def test_validation_catches_dropped_security_constraint(tmp_path):
    d = copy_templates(tmp_path)

    def drop_rls(t):
        for phase in t["phases"]:
            phase["human_required_tasks"] = [
                task for task in phase["human_required_tasks"]
                if not task.startswith("Enable RLS on this table")
            ]

    rewrite(d, "archetype_3_fullstack.json", drop_rls)
    with pytest.raises(TemplateValidationError, match="RLS"):
        load_templates(d)


# --- no fourth archetype, ever -----------------------------------------------

def test_fourth_template_file_is_rejected(tmp_path):
    d = copy_templates(tmp_path)
    fourth = json.loads((d / "archetype_1_ai_app.json").read_text(encoding="utf-8"))
    fourth["archetype_id"] = 4
    fourth["archetype_name"] = "Mobile App"
    (d / "archetype_4_mobile.json").write_text(json.dumps(fourth), encoding="utf-8")
    with pytest.raises(TemplateValidationError, match="exactly"):
        load_templates(d)


def test_unexpected_archetype_id_inside_a_template_is_rejected(tmp_path):
    d = copy_templates(tmp_path)

    def change_id(t):
        t["archetype_id"] = 4

    rewrite(d, "archetype_2_rest_api.json", change_id)
    with pytest.raises(TemplateValidationError, match="archetype_id"):
        load_templates(d)


def test_missing_template_file_is_rejected(tmp_path):
    d = copy_templates(tmp_path)
    (d / "archetype_1_ai_app.json").unlink()
    with pytest.raises(TemplateValidationError):
        load_templates(d)


# --- deterministic classification tiebreaker ----------------------------------

@pytest.mark.parametrize(
    ("llm_core", "frontend_or_db", "expected"),
    [
        (True, True, 1),   # LLM API as core feature always wins
        (True, False, 1),
        (False, True, 3),  # else frontend/database → full-stack
        (False, False, 2), # else REST API backend
    ],
)
def test_resolve_archetype_tiebreaker(llm_core, frontend_or_db, expected):
    assert resolve_archetype(llm_core, frontend_or_db) == expected


def test_resolve_archetype_only_ever_returns_a_known_archetype():
    results = {
        resolve_archetype(a, b) for a in (True, False) for b in (True, False)
    }
    assert results <= {1, 2, 3}
    assert set(template_service.EXPECTED_TEMPLATES) == {
        "archetype_1_ai_app.json",
        "archetype_2_rest_api.json",
        "archetype_3_fullstack.json",
    }
