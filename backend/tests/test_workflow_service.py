"""Workflow artifact store tests (M13B) — eligibility, per-section round-trips,
phase/section isolation, strict validation, and the storage-only guarantee,
against the in-memory fake.
"""

import copy
import json

import pytest

from app.schemas.workflow import SECTION_MODELS
from app.services.phase_service import PhaseNotFoundError, WorkspaceNotReadyError
from app.services.workflow_service import (
    SECTIONS,
    InvalidArtifactError,
    SectionNotFoundError,
    get_phase_artifacts,
    save_section,
)
from tests.fakes import InMemoryProjectRepository
from tests.test_phase_service import USER, run, seed_active_project, seed_intake_only

PROMPT_BUILDER = {
    "inputs": {"goal": "Add the match-creation endpoint", "files": "app/routes/matches.py"},
    "generated_prompt": (
        "I'm building a volleyball league tracker with FastAPI. Add ONLY a "
        "POST /matches route that validates team ids. Do not touch other files. "
        "Tell me what I should manually verify."
    ),
    "why_stronger": "Scopes the request to one endpoint and forbids unrelated changes.",
}

REVIEW_BOARD = {
    "files_changed": ["app/routes/matches.py", "app/models.py"],
    "ai_generated": "The POST /matches handler and the Match model.",
    "accepted": "The handler.",
    "rejected": "An unrequested rewrite of main.py.",
    "edited_manually": "Renamed the score fields.",
    "ai_assumptions": "Assumed scores are always integers.",
    "least_confident": "The validation on nested team data.",
    "out_of_scope_changes": "It reformatted imports in main.py.",
}

EVIDENCE = {
    "entries": [
        {"kind": "repo_url", "content": "https://github.com/student/league-tracker"},
        {"kind": "commit_hash", "content": "a1b2c3d"},
        {"kind": "terminal_output", "content": "1 passed in 0.12s"},
    ],
    "summary": "Smoke test passing on the new endpoint.",
}

VERIFICATION = {
    "checks": [
        {"check": "app_runs_locally", "result": "pass", "note": "uvicorn boots clean"},
        {"check": "failure_case_tested", "result": "pass", "note": "400 on a missing team id"},
        {"check": "secret_exposure_checked", "result": "pass"},
    ],
    "explanation": "The endpoint works, rejects bad input, and no keys are in the repo.",
}

IMPLEMENTATION_IMPORT = {
    "source_kind": "git_diff",
    "content": (
        "diff --git a/app/routes/matches.py b/app/routes/matches.py\n"
        "+    @router.post(\"/matches\")\n"
        "+    async def create_match(body: MatchIn):\n"
        "+        return await save_match(body)"
    ),
    "changed_files": ["app/routes/matches.py"],
    "student_summary": "The AI added the match-creation route.",
    "tool_name": "Claude",
}

SAMPLE = {
    "prompt_builder": PROMPT_BUILDER,
    "review_board": REVIEW_BOARD,
    "evidence": EVIDENCE,
    "verification": VERIFICATION,
    "implementation_import": IMPLEMENTATION_IMPORT,
}


# --- defaults & eligibility --------------------------------------------------------


def test_new_project_rows_default_to_empty_artifacts():
    repo = InMemoryProjectRepository()
    project = seed_intake_only(repo)
    assert project["workflow_artifacts"] == {}


def test_workflow_refused_without_active_project():
    repo = InMemoryProjectRepository()
    with pytest.raises(WorkspaceNotReadyError):
        run(get_phase_artifacts(repo, USER, 1))
    seed_intake_only(repo)  # intake done, no roadmap yet
    with pytest.raises(WorkspaceNotReadyError):
        run(save_section(repo, USER, 1, "evidence", EVIDENCE))


# --- reads & writes ----------------------------------------------------------------


def test_empty_state_has_all_sections_null():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    state = run(get_phase_artifacts(repo, USER, 1))
    assert state["phase"] == 1
    assert set(state["sections"]) == set(SECTIONS)
    assert all(v is None for v in state["sections"].values())


@pytest.mark.parametrize("section", SECTIONS)
def test_each_section_round_trips(section):
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    saved = run(save_section(repo, USER, 1, section, SAMPLE[section]))
    assert saved["phase"] == 1 and saved["section"] == section
    assert saved["artifact"]["saved_at"]  # server-side timestamp metadata

    stored = run(get_phase_artifacts(repo, USER, 1))["sections"][section]
    expected = SECTION_MODELS[section].model_validate(SAMPLE[section]).model_dump(mode="json")
    assert stored == {**expected, "saved_at": stored["saved_at"]}


def test_saving_one_section_keeps_the_others():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(save_section(repo, USER, 1, "prompt_builder", PROMPT_BUILDER))
    run(save_section(repo, USER, 1, "review_board", REVIEW_BOARD))
    sections = run(get_phase_artifacts(repo, USER, 1))["sections"]
    assert sections["prompt_builder"]["generated_prompt"] == PROMPT_BUILDER["generated_prompt"]
    assert sections["review_board"]["accepted"] == "The handler."

    # Full-section replace: a new PUT replaces that section, not merges into it.
    run(save_section(repo, USER, 1, "review_board", {"accepted": "Everything this time."}))
    sections = run(get_phase_artifacts(repo, USER, 1))["sections"]
    assert sections["review_board"]["accepted"] == "Everything this time."
    assert sections["review_board"]["rejected"] is None
    assert sections["prompt_builder"]["generated_prompt"] == PROMPT_BUILDER["generated_prompt"]


def test_saving_one_phase_keeps_other_phases():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(save_section(repo, USER, 1, "evidence", EVIDENCE))
    run(save_section(repo, USER, 2, "verification", VERIFICATION))
    assert run(get_phase_artifacts(repo, USER, 1))["sections"]["evidence"]["summary"] == EVIDENCE["summary"]
    assert run(get_phase_artifacts(repo, USER, 2))["sections"]["verification"]["explanation"]
    assert run(get_phase_artifacts(repo, USER, 2))["sections"]["evidence"] is None


# --- validation --------------------------------------------------------------------


def test_unknown_section_and_phase_are_rejected():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    with pytest.raises(SectionNotFoundError):
        run(save_section(repo, USER, 1, "reflection", {}))
    with pytest.raises(PhaseNotFoundError):
        run(save_section(repo, USER, 99, "evidence", EVIDENCE))
    with pytest.raises(PhaseNotFoundError):
        run(get_phase_artifacts(repo, USER, 99))


def test_oversized_and_overlong_payloads_are_rejected():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    # Total-size cap (each field is legal, together they exceed 30 KB).
    big = {"entries": [{"kind": "note", "content": "x" * 7000} for _ in range(5)]}
    with pytest.raises(InvalidArtifactError, match="too large"):
        run(save_section(repo, USER, 1, "evidence", big))
    # Per-field cap.
    with pytest.raises(InvalidArtifactError):
        run(save_section(repo, USER, 1, "prompt_builder", {"generated_prompt": "x" * 8001}))
    # List cap.
    with pytest.raises(InvalidArtifactError):
        run(save_section(repo, USER, 1, "review_board", {"files_changed": ["f"] * 51}))


def test_malformed_fields_are_rejected():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    bad = [
        ("evidence", {"entries": [{"kind": "repo_url", "content": "not-a-url"}]}),
        ("evidence", {"entries": [{"kind": "commit_hash", "content": "zzz"}]}),
        ("evidence", {"entries": [{"kind": "selfie", "content": "hi"}]}),
        ("verification", {"checks": [{"check": "vibes", "result": "pass"}]}),
        ("verification", {"checks": [{"check": "smoke_test", "result": "pass"},
                                     {"check": "smoke_test", "result": "fail"}]}),
        ("prompt_builder", {"generated_prompt": "ok", "surprise_field": "nope"}),
        ("prompt_builder", {}),  # generated_prompt is required
    ]
    for section, payload in bad:
        with pytest.raises(InvalidArtifactError):
            run(save_section(repo, USER, 1, section, payload))


def test_secret_looking_content_is_rejected():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    for text in ("apikey=sb_secret_abc123", "key: AIzaFakeFakeFake", "-----BEGIN EC PRIVATE KEY-----"):
        with pytest.raises(InvalidArtifactError, match="secret"):
            run(save_section(repo, USER, 1, "evidence",
                             {"entries": [{"kind": "terminal_output", "content": text}]}))


# --- storage-only guarantee --------------------------------------------------------


def test_writes_touch_only_workflow_artifacts():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    before = copy.deepcopy(repo._rows)
    for section in SECTIONS:
        run(save_section(repo, USER, 1, section, SAMPLE[section]))
    after = copy.deepcopy(repo._rows)

    assert len(before) == len(after) == 1
    changed = {k for k in after[0] if after[0][k] != before[0][k]}
    assert changed == {"workflow_artifacts"}
    # Explicitly: nothing the other engines own moved.
    for field in ("roadmap", "task_progress", "current_phase", "status",
                  "gate_history_summary", "intake_purpose"):
        assert after[0][field] == before[0][field]
    # The service takes only the ProjectRepository — it cannot reach gate
    # sessions, unlocks, or profiles by construction.


def test_corrupted_stored_artifacts_are_dropped_on_read():
    repo = InMemoryProjectRepository()
    project = seed_active_project(repo)
    run(repo.update_project(USER, project["id"], {
        "workflow_artifacts": {"1": {"evidence": "not-a-dict", "junk_section": {"a": 1}}},
    }))
    sections = run(get_phase_artifacts(repo, USER, 1))["sections"]
    assert set(sections) == set(SECTIONS)
    assert all(v is None for v in sections.values())


def test_no_llm_involved():
    # The workflow store is deterministic storage: the module neither imports
    # nor accepts an LLM. (Route-level proof lives in test_workflow_routes.)
    import inspect

    from app.services import workflow_service

    assert "llm_service" not in inspect.getsource(workflow_service)
    assert not any("llm" in name.lower() for name in vars(workflow_service))
