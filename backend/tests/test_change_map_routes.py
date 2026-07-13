"""Change Map route tests (M15C.1): auth-enforced, controlled errors, the
full generate → decide → confirm lifecycle over HTTP, overwrite protection,
staleness, per-user isolation, and the guarantee that the generic workflow
section PUT can never write the server-owned map.

Reuses the offline ES256 auth pattern; projects activate through the real
intake + roadmap routes (no-key stub LLM path) and the change map generates
through the real stub provider — the same deterministic validation a live
model must pass.
"""

import json

from app.services.llm_service import LLMError, LLMService, get_llm_service
from tests.fakes import ScriptedLLM
from tests.test_phase_routes import (  # noqa: F401 (client fixture)
    USER_A,
    USER_B,
    activate_project,
    auth_headers,
    client,
)

IMPORT_PAYLOAD = {
    "source_kind": "git_diff",
    "content": (
        "diff --git a/app/routes/tasks.py b/app/routes/tasks.py\n"
        "+    if task.user_id != user_id:\n"
        "+        raise PermissionError"
    ),
    "changed_files": ["app/routes/tasks.py"],
    "student_summary": "The AI added task ownership checks.",
}

CHANGE_MAP_ROUTES = (
    ("POST", "/workflow/1/change-map/generate"),
    ("PUT", "/workflow/1/change-map"),
    ("POST", "/workflow/1/change-map/confirm"),
)


def save_import(client, user_id=USER_A, phase=1, payload=IMPORT_PAYLOAD):
    resp = client.put(f"/workflow/{phase}/implementation_import", json=payload,
                      headers=auth_headers(user_id))
    assert resp.status_code == 200


def generate(client, user_id=USER_A, phase=1, body=None):
    return client.post(f"/workflow/{phase}/change-map/generate",
                       json=body, headers=auth_headers(user_id))


def decide_all(client, user_id=USER_A, phase=1, decision="confirmed"):
    stored = client.get(f"/workflow/{phase}", headers=auth_headers(user_id)).json()
    updates = [{"item_id": i["item_id"], "student_decision": decision}
               for i in stored["change_map"]["items"] if i["origin"] == "ai_inferred"]
    return client.put(f"/workflow/{phase}/change-map", json={"updates": updates},
                      headers=auth_headers(user_id))


def test_change_map_routes_require_auth(client):
    for method, path in CHANGE_MAP_ROUTES:
        resp = client.request(method, path, json={})
        assert resp.status_code == 401


def test_change_map_before_roadmap_is_controlled_409(client):
    for method, path in CHANGE_MAP_ROUTES:
        resp = client.request(method, path, json={}, headers=auth_headers())
        assert resp.status_code == 409


def test_generate_without_an_import_is_409(client):
    activate_project(client)
    resp = generate(client)
    assert resp.status_code == 409
    assert "Bring back implementation material" in resp.json()["error"]["message"]


def test_full_lifecycle_over_http(client):
    activate_project(client)
    save_import(client)

    # Generate (real stub provider) — server-owned fields assigned.
    resp = generate(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert body["stale"] is False
    assert body["source_redacted"] is False
    assert body["source_truncated"] is False
    assert body["items"]
    for item in body["items"]:
        assert item["origin"] == "ai_inferred"
        assert item["student_decision"] == "pending_review"
        assert item["item_id"].startswith("cm-")
        assert item["source_references"]

    # Readable through GET /workflow/{phase}, top-level (never a section).
    stored = client.get("/workflow/1", headers=auth_headers()).json()
    assert stored["change_map"]["generated_at"] == body["generated_at"]
    assert "change_map" not in stored["sections"]

    # Pending items block confirmation.
    resp = client.post("/workflow/1/change-map/confirm", headers=auth_headers())
    assert resp.status_code == 409
    assert "pending review" in resp.json()["error"]["message"]

    # Decide every item (one honest unresolved), add a student item, confirm.
    first = body["items"][0]["item_id"]
    updates = [{"item_id": i["item_id"], "student_decision": "confirmed"}
               for i in body["items"] if i["item_id"] != first]
    updates.append({"item_id": first, "student_decision": "needs_inspection"})
    resp = client.put("/workflow/1/change-map", json={
        "updates": updates,
        "student_added_items": [{
            "category": "implementation_decision",
            "student_text": "I kept the old route alongside the new one.",
        }],
    }, headers=auth_headers())
    assert resp.status_code == 200
    added = [i for i in resp.json()["items"] if i["origin"] == "student_added"]
    assert len(added) == 1 and added[0]["item_id"].startswith("sa-")

    resp = client.post("/workflow/1/change-map/confirm", headers=auth_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
    assert resp.json()["confirmed_at"]

    # Duplicate confirm → controlled 409.
    resp = client.post("/workflow/1/change-map/confirm", headers=auth_headers())
    assert resp.status_code == 409


def test_existing_map_needs_explicit_replace(client):
    activate_project(client)
    save_import(client)
    assert generate(client).status_code == 200
    resp = generate(client)
    assert resp.status_code == 409
    assert "replace_existing" in resp.json()["error"]["message"]
    assert generate(client, body={"replace_existing": True}).status_code == 200


def test_import_replacement_makes_map_stale_and_blocks_confirm(client):
    activate_project(client)
    save_import(client)
    assert generate(client).status_code == 200
    assert decide_all(client).status_code == 200
    # Replace the import → stale is server-derived on read.
    save_import(client, payload={**IMPORT_PAYLOAD, "student_summary": "Now with pagination."})
    stored = client.get("/workflow/1", headers=auth_headers()).json()
    assert stored["change_map"]["stale"] is True
    resp = client.post("/workflow/1/change-map/confirm", headers=auth_headers())
    assert resp.status_code == 409
    assert "regenerate" in resp.json()["error"]["message"].lower()
    # Explicit regeneration clears staleness.
    resp = generate(client, body={"replace_existing": True})
    assert resp.status_code == 200
    assert resp.json()["stale"] is False


def test_controlled_404s_and_422s(client):
    activate_project(client)
    save_import(client)
    # Unknown phase → 404; update/confirm with no map → 404.
    assert generate(client, phase=99).status_code == 404
    assert client.put("/workflow/1/change-map", json={"updates": []},
                      headers=auth_headers()).status_code == 404
    assert client.post("/workflow/1/change-map/confirm",
                       headers=auth_headers()).status_code == 404
    # Invalid update payloads → 422 without echoing values.
    assert generate(client).status_code == 200
    resp = client.put("/workflow/1/change-map",
                      json={"updates": [{"item_id": "cm-nope", "student_decision": "confirmed"}]},
                      headers=auth_headers())
    assert resp.status_code == 422
    resp = client.put("/workflow/1/change-map",
                      json={"updates": [], "generated_at": "2020-01-01T00:00:00Z"},
                      headers=auth_headers())
    assert resp.status_code == 422
    resp = generate(client, body={"replace_existing": True, "surprise": 1})
    assert resp.status_code == 422


def test_provider_failure_is_502_with_nothing_stored(client):
    activate_project(client)
    save_import(client)
    client.app.dependency_overrides[get_llm_service] = (
        lambda: LLMService([ScriptedLLM([LLMError("down")])])
    )
    resp = generate(client)
    assert resp.status_code == 502
    client.app.dependency_overrides.pop(get_llm_service)
    stored = client.get("/workflow/1", headers=auth_headers()).json()
    assert stored["change_map"] is None


def test_generic_section_put_cannot_write_the_change_map(client):
    activate_project(client)
    resp = client.put("/workflow/1/change_map",
                      json={"status": "confirmed", "items": []},
                      headers=auth_headers())
    assert resp.status_code == 404  # not a workflow section, by construction


def test_other_user_cannot_read_generate_update_or_confirm(client):
    activate_project(client, USER_A)
    save_import(client, USER_A)
    assert generate(client, USER_A).status_code == 200

    # B has no active project: every change-map action refused.
    assert generate(client, USER_B).status_code == 409
    assert client.put("/workflow/1/change-map", json={"updates": []},
                      headers=auth_headers(USER_B)).status_code == 409
    assert client.post("/workflow/1/change-map/confirm",
                       headers=auth_headers(USER_B)).status_code == 409

    # B with their own project sees only their own (absent) map.
    activate_project(client, USER_B)
    theirs = client.get("/workflow/1", headers=auth_headers(USER_B)).json()
    assert theirs["change_map"] is None
    mine = client.get("/workflow/1", headers=auth_headers(USER_A)).json()
    assert mine["change_map"] is not None


def test_change_map_ops_do_not_change_any_other_engine_state(client):
    from app.services.project_repository import (
        get_gate_session_repository,
        get_unlock_repository,
    )
    from tests.fakes import InMemoryGateSessionRepository, InMemoryUnlockRepository

    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    client.app.dependency_overrides[get_gate_session_repository] = lambda: gates
    client.app.dependency_overrides[get_unlock_repository] = lambda: unlocks
    activate_project(client)
    save_import(client)
    reads = {
        "roadmap": lambda: client.get("/roadmap", headers=auth_headers()).json(),
        "phase": lambda: client.get("/phases/1", headers=auth_headers()).json(),
        "gate": lambda: client.get("/gate/current", headers=auth_headers()).json(),
        "unlocks": lambda: client.get("/unlocks", headers=auth_headers()).json(),
        "evaluation": lambda: client.get("/evaluation", headers=auth_headers()).json(),
        "context_summary": lambda: client.get("/gate/context-summary",
                                              headers=auth_headers()).json(),
        "sections": lambda: client.get("/workflow/1", headers=auth_headers()).json()["sections"],
    }
    before = {name: read() for name, read in reads.items()}
    assert generate(client).status_code == 200
    assert decide_all(client).status_code == 200
    assert client.post("/workflow/1/change-map/confirm",
                       headers=auth_headers()).status_code == 200
    assert {name: read() for name, read in reads.items()} == before


def test_responses_carry_no_secrets_prompts_or_raw_import(client, monkeypatch):
    from app.core.config import get_settings
    activate_project(client)
    fake_bearer = "Bearer faketoken0123456789abcdef"
    save_import(client, payload={
        "source_kind": "code_snippet",
        "content": f"headers = {{'Authorization': '{fake_bearer}'}}\nprint('ok')",
        "student_summary": "Added an auth header.",
    })
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key-for-tests")
    get_settings.cache_clear()
    resp = generate(client)
    assert resp.status_code == 200
    text = json.dumps(resp.json())
    assert "faketoken0123456789abcdef" not in text
    assert "fake-service-role-key-for-tests" not in text
    assert "CODIZE CHANGE MAP EXTRACTION" not in text  # no prompt leakage
    assert resp.json()["source_redacted"] is True
    stored = client.get("/workflow/1", headers=auth_headers()).text
    assert "faketoken0123456789abcdef" not in stored.replace(
        fake_bearer, "")  # only the student's own stored import carries it
