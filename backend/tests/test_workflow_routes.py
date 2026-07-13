"""Workflow artifact route tests (M13B): auth-enforced, controlled errors,
per-user isolation, storage-only behavior over HTTP, and no LLM involvement.

Reuses the offline ES256 auth pattern and activates projects through the real
intake + roadmap routes (no-key stub LLM path).
"""

import pytest

from app.core.config import get_settings
from app.services import llm_service
from tests.test_phase_routes import (  # noqa: F401 (client fixture)
    USER_A,
    USER_B,
    activate_project,
    auth_headers,
    client,
)
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, REVIEW_BOARD, SAMPLE, VERIFICATION

WORKFLOW_ROUTES = (
    ("GET", "/workflow/1"),
    ("PUT", "/workflow/1/evidence"),
)


def test_workflow_routes_require_auth(client):
    for method, path in WORKFLOW_ROUTES:
        resp = client.request(method, path, json=EVIDENCE)
        assert resp.status_code == 401
        assert resp.json()["error"]["status"] == 401


def test_workflow_before_roadmap_is_controlled_409(client):
    for method, path in WORKFLOW_ROUTES:
        resp = client.request(method, path, json=EVIDENCE, headers=auth_headers())
        assert resp.status_code == 409
        assert resp.json()["error"]["status"] == 409


def test_full_workflow_artifact_flow(client):
    activate_project(client)

    empty = client.get("/workflow/1", headers=auth_headers())
    assert empty.status_code == 200
    assert empty.json() == {
        "phase": 1,
        "sections": {"prompt_builder": None, "review_board": None,
                     "evidence": None, "verification": None,
                     "implementation_import": None},
    }

    for section, payload in SAMPLE.items():
        resp = client.put(f"/workflow/1/{section}", json=payload, headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["section"] == section
        assert resp.json()["artifact"]["saved_at"]

    stored = client.get("/workflow/1", headers=auth_headers()).json()["sections"]
    assert stored["prompt_builder"]["generated_prompt"] == PROMPT_BUILDER["generated_prompt"]
    assert stored["review_board"]["files_changed"] == REVIEW_BOARD["files_changed"]
    assert stored["evidence"]["entries"][0]["kind"] == "repo_url"
    assert stored["verification"]["checks"][0]["check"] == "app_runs_locally"

    # Re-PUT replaces one section; other sections and phases are untouched.
    client.put("/workflow/2/review_board", json={"accepted": "Phase 2 review."},
               headers=auth_headers())
    assert client.get("/workflow/1", headers=auth_headers()).json()["sections"][
        "review_board"]["accepted"] == REVIEW_BOARD["accepted"]
    phase2 = client.get("/workflow/2", headers=auth_headers()).json()["sections"]
    assert phase2["review_board"]["accepted"] == "Phase 2 review."
    assert phase2["evidence"] is None


def test_invalid_phase_section_and_payload_are_controlled_errors(client):
    activate_project(client)
    resp = client.get("/workflow/99", headers=auth_headers())
    assert resp.status_code == 404
    resp = client.put("/workflow/1/reflection", json={}, headers=auth_headers())
    assert resp.status_code == 404
    assert "reflection" not in resp.json()["error"]["message"]  # input not echoed
    resp = client.get("/workflow/not-a-number", headers=auth_headers())
    assert resp.status_code == 422
    resp = client.put("/workflow/1/prompt_builder", json={"generated_prompt": ""},
                      headers=auth_headers())
    assert resp.status_code == 422
    big = {"entries": [{"kind": "note", "content": "x" * 7000} for _ in range(5)]}
    resp = client.put("/workflow/1/evidence", json=big, headers=auth_headers())
    assert resp.status_code == 422
    assert "too large" in resp.json()["error"]["message"]


def test_wrong_user_cannot_see_or_touch_artifacts(client):
    activate_project(client, USER_A)
    assert client.put("/workflow/1/evidence", json=EVIDENCE,
                      headers=auth_headers(USER_A)).status_code == 200

    # B has no active project: refused, and A's artifacts are untouched.
    assert client.get("/workflow/1", headers=auth_headers(USER_B)).status_code == 409
    assert client.put("/workflow/1/evidence", json={"entries": []},
                      headers=auth_headers(USER_B)).status_code == 409
    mine = client.get("/workflow/1", headers=auth_headers(USER_A)).json()
    assert mine["sections"]["evidence"]["summary"] == EVIDENCE["summary"]

    # B with their own active project sees only their own (empty) artifacts.
    activate_project(client, USER_B)
    theirs = client.get("/workflow/1", headers=auth_headers(USER_B)).json()
    assert theirs["sections"]["evidence"] is None


def test_artifact_writes_do_not_change_any_other_engine_state(client):
    # The shared fixture overrides only the project repo; the gate/unlock
    # routes read through their own repos, so fake those too.
    from app.services.project_repository import (
        get_gate_session_repository,
        get_unlock_repository,
    )
    from tests.fakes import InMemoryGateSessionRepository, InMemoryUnlockRepository

    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    client.app.dependency_overrides[get_gate_session_repository] = lambda: gates
    client.app.dependency_overrides[get_unlock_repository] = lambda: unlocks
    activate_project(client)
    reads = {
        "roadmap": lambda: client.get("/roadmap", headers=auth_headers()).json(),
        "phase": lambda: client.get("/phases/1", headers=auth_headers()).json(),
        "gate": lambda: client.get("/gate/current", headers=auth_headers()).json(),
        "unlocks": lambda: client.get("/unlocks", headers=auth_headers()).json(),
        "evaluation": lambda: client.get("/evaluation", headers=auth_headers()).json(),
    }
    before = {name: read() for name, read in reads.items()}
    for section, payload in SAMPLE.items():
        assert client.put(f"/workflow/1/{section}", json=payload,
                          headers=auth_headers()).status_code == 200
    assert {name: read() for name, read in reads.items()} == before


def test_workflow_routes_never_call_an_llm(client, monkeypatch):
    activate_project(client)  # roadmap generation legitimately used the stub LLM

    async def _explode(self, prompt, temperature):
        raise AssertionError("workflow routes must not call the LLM")

    for provider_cls in (llm_service.StubProvider, llm_service.GeminiProvider,
                         llm_service.OpenRouterProvider):
        monkeypatch.setattr(provider_cls, "complete", _explode, raising=True)
    for section, payload in SAMPLE.items():
        assert client.put(f"/workflow/1/{section}", json=payload,
                          headers=auth_headers()).status_code == 200
    assert client.get("/workflow/1", headers=auth_headers()).status_code == 200


def test_workflow_responses_contain_no_secrets(client, monkeypatch):
    activate_project(client)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    get_settings.cache_clear()
    client.put("/workflow/1/evidence", json=EVIDENCE, headers=auth_headers())
    text = client.get("/workflow/1", headers=auth_headers()).text
    assert "fake-service-role-key-for-tests" not in text
    assert "fake-gemini-key-for-tests" not in text
