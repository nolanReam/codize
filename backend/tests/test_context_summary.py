"""Defense context summary tests (Milestone 14C) — the metadata-only view of
the M14A pack that the Project Defense UI consumes.

Safety contract under test: the summary carries presence/truncation metadata
only — never artifact text, intake answers, rendered context, or grounding
terms; ownership rides the same authenticated-identity path as every gate
read; building it is a pure read with no LLM call and no DB write.

All strings in this file are fake fixtures.
"""

import asyncio
import copy
import inspect
import json
import time
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import security
from app.main import create_app
from app.services import defense_context_service as dcs
from app.services import roadmap_service, workflow_service
from app.services.defense_context_service import (
    SUMMARY_LABELS,
    build_context_summary,
    build_defense_context,
    summarize_defense_context,
)
from app.services.llm_service import LLMService, StubProvider, get_llm_service
from app.services.phase_service import PhaseNotFoundError, WorkspaceNotReadyError
from app.services.project_repository import get_project_repository
from tests.fakes import InMemoryProjectRepository, ScriptedLLM

USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_USER = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

INTAKE_FIELDS = {
    "intake_purpose": "Help my climbing gym publish route ratings so setters get feedback.",
    "intake_scope": "A REST backend exposing route data through HTTP endpoints.",
    "intake_stack": "Python and FastAPI",
    "intake_self_assessment": "Sometimes, depends",
    "intake_timeline": "About six weeks",
}

PROMPT_BUILDER = {
    "inputs": {"ai_task": "propose a schema for routes"},
    "generated_prompt": "Your task: propose a schema for routes. Constraints: Python only.",
    "why_stronger": "It scopes the request to one task.",
}
REVIEW_BOARD = {
    "files_changed": ["app/models.py", "app/routes/ratings.py"],
    "ai_generated": "the Route model and the POST route",
    "least_confident": "the aggregate rating query",
}
EVIDENCE = {
    "entries": [{"kind": "test_output", "content": "4 passed in 0.31s"}],
    "summary": "the create plus fetch cycle passes",
}
VERIFICATION = {
    "checks": [
        {"check": "app_runs_locally", "result": "pass", "note": "uvicorn boots"},
        {"check": "smoke_test", "result": "skipped"},
    ],
    "explanation": "Basic cycle works; auth untouched so far.",
}

# Every content-bearing fixture string: none may appear in a serialized summary.
CONTENT_STRINGS = (
    INTAKE_FIELDS["intake_purpose"],
    INTAKE_FIELDS["intake_scope"],
    PROMPT_BUILDER["generated_prompt"],
    PROMPT_BUILDER["why_stronger"],
    "propose a schema for routes",
    "app/models.py",
    "the Route model and the POST route",
    "the aggregate rating query",
    "4 passed in 0.31s",
    "the create plus fetch cycle passes",
    "uvicorn boots",
    "Basic cycle works",
)

ALL_SOURCE_IDS = [source_id for source_id, _, _ in dcs._SOURCE_DEFS]
WORKFLOW_SOURCE_IDS = [s for s in ALL_SOURCE_IDS if s.startswith("workflow.")]


def run(coro):
    return asyncio.run(coro)


def seed_active_project(repo, user=USER):
    fields = {**INTAKE_FIELDS,
              "intake_completed_at": "2026-07-02T00:00:00+00:00",
              "archetype_id": 2}
    run(repo.create_project(user, fields))
    run(roadmap_service.generate_roadmap(repo, LLMService([StubProvider()]), user))
    return run(repo.get_project(user))


def save_all_sections(repo, user=USER, phase=1):
    run(workflow_service.save_section(repo, user, phase, "prompt_builder", PROMPT_BUILDER))
    run(workflow_service.save_section(repo, user, phase, "review_board", REVIEW_BOARD))
    run(workflow_service.save_section(repo, user, phase, "evidence", EVIDENCE))
    run(workflow_service.save_section(repo, user, phase, "verification", VERIFICATION))


def full_repo():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    save_all_sections(repo)
    return repo


# --- shape, presence, order ----------------------------------------------------


def test_owner_summary_covers_current_phase_with_all_sources_present():
    repo = full_repo()
    summary = run(build_context_summary(repo, USER))

    assert summary.schema_version == "1.0"
    assert summary.artifact_aware is True
    assert summary.phase_number == 1  # the current phase — what the gate defends
    assert [s.source_id for s in summary.included_sources] == ALL_SOURCE_IDS
    assert summary.missing_sources == []
    assert summary.has_truncation is False


def test_missing_sections_are_first_class_metadata_not_errors():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(workflow_service.save_section(repo, USER, 1, "prompt_builder", PROMPT_BUILDER))

    summary = run(build_context_summary(repo, USER))
    included = [s.source_id for s in summary.included_sources]
    missing = [m.source_id for m in summary.missing_sources]

    assert "workflow.prompt_builder" in included
    assert missing == [
        "workflow.review_board", "workflow.evidence", "workflow.verification"
    ]  # manifest order, deterministically
    for m in summary.missing_sources:
        assert m.label == SUMMARY_LABELS[m.source_id]


def test_labels_are_the_display_map_for_every_entry():
    repo = full_repo()
    summary = run(build_context_summary(repo, USER))
    for s in summary.included_sources:
        assert s.label == SUMMARY_LABELS[s.source_id]
    # source types survive so the UI can group student vs system sources
    types = {s.source_id: s.source_type.value for s in summary.included_sources}
    assert types["workflow.prompt_builder"] == "student_artifact"
    assert types["phase"] == "system_roadmap"


def test_truncation_is_represented_per_source_and_overall():
    repo = InMemoryProjectRepository()
    fields = {**INTAKE_FIELDS,
              "intake_purpose": "route ratings " + "x" * 3500,  # over the 3000 intake budget
              "intake_completed_at": "2026-07-02T00:00:00+00:00",
              "archetype_id": 2}
    run(repo.create_project(USER, fields))
    run(roadmap_service.generate_roadmap(repo, LLMService([StubProvider()]), USER))

    summary = run(build_context_summary(repo, USER))
    assert summary.has_truncation is True
    truncated = {s.source_id: s.truncated for s in summary.included_sources}
    assert truncated["intake"] is True
    assert truncated["phase"] is False


# --- safety: metadata only ------------------------------------------------------


def test_serialized_summary_carries_no_content():
    repo = full_repo()
    summary = run(build_context_summary(repo, USER))
    dumped = json.dumps(summary.model_dump(mode="json"))

    for content in CONTENT_STRINGS:
        assert content not in dumped
    # no pack internals, grounding vocabulary, identity, or secrets vocabulary
    for banned in ("content_notice", "untrusted", "grounding", "generated_prompt",
                   "BEGIN CONTEXT", "purpose", "checks", "entries",
                   USER, "@", "token", "eyJ"):
        assert banned not in dumped
    project = run(repo.get_project(USER))
    assert project["id"] not in dumped


def test_summary_matches_the_pack_manifest_exactly():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    run(workflow_service.save_section(repo, USER, 1, "evidence", EVIDENCE))

    pack = run(build_defense_context(repo, USER, 1))
    summary = summarize_defense_context(pack)

    present_ids = [r.source_id for r in pack.source_manifest if r.present]
    assert [s.source_id for s in summary.included_sources] == present_ids
    assert [m.source_id for m in summary.missing_sources] == pack.missing_sources


# --- ownership, readiness, pure-read --------------------------------------------


def test_no_project_or_no_roadmap_raises_workspace_not_ready():
    empty = InMemoryProjectRepository()
    with pytest.raises(WorkspaceNotReadyError):
        run(build_context_summary(empty, USER))

    intake_only = InMemoryProjectRepository()
    run(intake_only.create_project(USER, {**INTAKE_FIELDS,
                                          "intake_completed_at": "2026-07-02T00:00:00+00:00",
                                          "archetype_id": 2}))
    with pytest.raises(WorkspaceNotReadyError):
        run(build_context_summary(intake_only, USER))


def test_other_user_sees_their_own_scope_never_the_owners():
    repo = full_repo()
    with pytest.raises(WorkspaceNotReadyError):
        run(build_context_summary(repo, OTHER_USER))


def test_corrupt_current_phase_maps_to_phase_not_found():
    repo = full_repo()
    project = run(repo.get_project(USER))
    run(repo.update_project(USER, project["id"], {"current_phase": 99}))
    with pytest.raises(PhaseNotFoundError):
        run(build_context_summary(repo, USER))


def test_summary_is_a_pure_read():
    repo = full_repo()
    before = copy.deepcopy(run(repo.get_project(USER)))
    run(build_context_summary(repo, USER))
    assert run(repo.get_project(USER)) == before


def test_seam_takes_no_llm_and_no_write_capable_repository():
    params = inspect.signature(build_context_summary).parameters
    assert list(params) == ["repo", "user_id"]  # no llm, no gate/unlock repos


# --- the HTTP surface ------------------------------------------------------------

_key = ec.generate_private_key(ec.SECP256R1())

FIVE_ANSWERS = {
    1: "Help my climbing gym publish route ratings so setters get feedback.",
    2: "A REST backend exposing route data through HTTP endpoints.",
    3: "Python and FastAPI.",
    4: "Sometimes, depends",
    5: "About six weeks.",
}


def auth_headers(user_id=USER):
    claims = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {pyjwt.encode(claims, _key, algorithm='ES256')}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://stub-project.supabase.co")
    for var in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        security, "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=_key.public_key())
        ),
    )
    app = create_app()
    project_repo = InMemoryProjectRepository()
    app.dependency_overrides[get_project_repository] = lambda: project_repo
    test_client = TestClient(app)
    test_client.app_ref = app
    return test_client


def activate_project(client, user_id=USER):
    for n in (1, 2, 3, 4, 5):
        resp = client.post("/intake/answers",
                           json={"question": n, "answer": FIVE_ANSWERS[n]},
                           headers=auth_headers(user_id))
        assert resp.status_code == 200
    assert client.post("/intake/complete", headers=auth_headers(user_id)).status_code == 200
    assert client.post("/roadmap/generate", headers=auth_headers(user_id)).status_code == 200


def test_route_requires_auth(client):
    assert client.get("/gate/context-summary").status_code == 401


def test_route_returns_metadata_only_summary(client):
    activate_project(client)
    put = client.put("/workflow/1/prompt_builder", json=PROMPT_BUILDER,
                     headers=auth_headers())
    assert put.status_code == 200

    resp = client.get("/gate/context-summary", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["artifact_aware"] is True
    assert body["phase_number"] == 1
    included = [s["source_id"] for s in body["included_sources"]]
    assert "workflow.prompt_builder" in included
    missing = [m["source_id"] for m in body["missing_sources"]]
    assert missing == ["workflow.review_board", "workflow.evidence",
                       "workflow.verification"]
    for content in CONTENT_STRINGS:
        assert content not in resp.text


def test_route_is_scoped_to_the_authenticated_user(client):
    activate_project(client)  # USER owns the only project
    resp = client.get("/gate/context-summary", headers=auth_headers(OTHER_USER))
    assert resp.status_code == 409  # their own empty workspace, never the owner's
    for content in CONTENT_STRINGS:
        assert content not in resp.text


def test_route_before_roadmap_is_409_not_an_error_page(client):
    for n in (1, 2, 3):
        client.post("/intake/answers", json={"question": n, "answer": FIVE_ANSWERS[n]},
                    headers=auth_headers())
    resp = client.get("/gate/context-summary", headers=auth_headers())
    assert resp.status_code == 409
    assert "error" in resp.json()


def test_route_makes_no_llm_call_and_no_write(client):
    activate_project(client)
    tracking = ScriptedLLM()  # raises if any completion is requested
    client.app_ref.dependency_overrides[get_llm_service] = lambda: tracking

    repo = client.app_ref.dependency_overrides[get_project_repository]()
    before = copy.deepcopy(run(repo.get_project(USER)))

    resp = client.get("/gate/context-summary", headers=auth_headers())
    assert resp.status_code == 200
    assert tracking.calls == []
    assert run(repo.get_project(USER)) == before
