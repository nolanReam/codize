"""M16B.3A authenticated Evidence handoff API and deterministic smoke."""

import copy
import json

from app.services import llm_service
from app.services.project_repository import get_project_repository
from tests.test_phase_routes import (  # noqa: F401 (client fixture)
    USER_A,
    USER_B,
    activate_project,
    auth_headers,
    client,
)
from tests.test_review_service import seed_map
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, VERIFICATION


PREVIEW_ROUTE = "/workflow/1/evidence/from-verification"


def prepare_linked_verification(
    client, user_id=USER_A, *, results=("pass", "fail", "skipped", "not_applicable", None)
):
    repo = client.app.dependency_overrides[get_project_repository]()
    seed_map(repo=repo, user=user_id)
    initialized = client.post(
        "/workflow/1/review/from-change-map", headers=auth_headers(user_id)
    )
    assert initialized.status_code == 200
    review_targets = initialized.json()["artifact"]["review_targets"]
    saved_review = client.put(
        "/workflow/1/review_board",
        json={"target_updates": [
            {
                "review_target_id": target["review_target_id"],
                "review_decision": "needs_verification",
                "student_rationale": "I need to test this behavior.",
            }
            for target in review_targets
        ]},
        headers=auth_headers(user_id),
    )
    assert saved_review.status_code == 200
    created = client.post(
        "/workflow/1/verification/from-review",
        json={"replace_existing": True},
        headers=auth_headers(user_id),
    )
    assert created.status_code == 200
    artifact = created.json()["artifact"]
    updates = []
    for target, result in zip(artifact["verification_targets"], results):
        if result is None:
            continue
        update = {
            "verification_target_id": target["verification_target_id"],
            "result": result,
            "result_notes": f"Student recorded {result}.",
        }
        if not updates:
            update["student_check"] = "Perform the student-edited check."
        updates.append(update)
    if updates:
        saved = client.put(
            "/workflow/1/verification",
            json={"target_updates": updates},
            headers=auth_headers(user_id),
        )
        assert saved.status_code == 200
        artifact = saved.json()["artifact"]
    return artifact


def test_handoff_routes_require_auth_and_workspace_phase_validation(client):
    assert client.get(PREVIEW_ROUTE).status_code == 401
    assert client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": ["vt-0123456789ab"]
    }).status_code == 401
    assert client.get(PREVIEW_ROUTE, headers=auth_headers()).status_code == 409

    activate_project(client)
    assert client.get("/workflow/99/evidence/from-verification",
                      headers=auth_headers()).status_code == 404
    assert client.post("/workflow/99/evidence/from-verification", json={
        "selected_verification_target_ids": ["vt-0123456789ab"]
    }, headers=auth_headers()).status_code == 404


def test_preview_missing_manual_and_mixed_linked_states(client):
    activate_project(client)
    missing = client.get(PREVIEW_ROUTE, headers=auth_headers())
    assert missing.status_code == 200
    assert missing.json()["verification_state"] == "verification_required"
    assert client.get("/workflow/1", headers=auth_headers()).json()["sections"]["evidence"] is None

    client.put("/workflow/1/verification", json=VERIFICATION, headers=auth_headers())
    manual = client.get(PREVIEW_ROUTE, headers=auth_headers())
    assert manual.status_code == 200
    assert manual.json()["mode"] == "manual_verification"

    linked = prepare_linked_verification(client)
    preview = client.get(PREVIEW_ROUTE, headers=auth_headers())
    assert preview.status_code == 200
    body = preview.json()
    assert body["verification_state"] == "current"
    assert [target["result"] for target in body["targets"][:5]] == [
        "pass", "fail", "skipped", "not_applicable", "unrecorded"
    ]
    assert body["eligible_count"] >= 2
    assert body["targets"][0]["check"] == "Perform the student-edited check."
    serialized = json.dumps(body)
    assert linked["verification_targets"][0]["review_target_id"] not in serialized
    assert "source_review_binding" not in serialized
    assert "fingerprint" not in serialized
    assert client.get("/workflow/1", headers=auth_headers()).json()["sections"]["evidence"] is None


def test_explicit_selection_initializes_no_content_and_protects_provenance(client):
    activate_project(client)
    verification = prepare_linked_verification(client)
    pass_target, fail_target = verification["verification_targets"][:2]
    empty = client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": []
    }, headers=auth_headers())
    assert empty.status_code == 422

    created = client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [
            fail_target["verification_target_id"],
            pass_target["verification_target_id"],
        ]
    }, headers=auth_headers())
    assert created.status_code == 200
    artifact = created.json()["artifact"]
    assert artifact["evidence_record_complete"] is False
    assert artifact["entries"] == [] and artifact["summary"] is None
    assert [target["verification_result_snapshot"] for target in artifact["evidence_targets"]] == [
        "pass", "fail"
    ]
    assert all(target["entries"] == [] for target in artifact["evidence_targets"])
    assert all(target["evidence_status"] == "not_addressed" for target in artifact["evidence_targets"])
    serialized = json.dumps(artifact)
    assert "source_review_target_id" not in serialized
    assert "source_change_map_item_id" not in serialized
    assert "source_verification_binding" not in serialized

    forged = client.put("/workflow/1/evidence", json={
        "source_verification_binding": {},
        "stale": False,
    }, headers=auth_headers())
    assert forged.status_code == 422


def test_ineligible_unknown_duplicate_existing_and_replacement_contract(client):
    activate_project(client)
    verification = prepare_linked_verification(client)
    ids = [target["verification_target_id"] for target in verification["verification_targets"]]
    for target_id in ids[2:5]:
        response = client.post(PREVIEW_ROUTE, json={
            "selected_verification_target_ids": [target_id]
        }, headers=auth_headers())
        assert response.status_code == 422
        assert "only performed" in response.json()["error"]["message"]
    assert client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": ["vt-000000000000"]
    }, headers=auth_headers()).status_code == 422
    assert client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [ids[0], ids[0]]
    }, headers=auth_headers()).status_code == 422

    assert client.put("/workflow/1/evidence", json=EVIDENCE,
                      headers=auth_headers()).status_code == 200
    conflict = client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [ids[0]]
    }, headers=auth_headers())
    assert conflict.status_code == 409
    replaced = client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [ids[0]],
        "replace_existing": True,
    }, headers=auth_headers())
    assert replaced.status_code == 200
    assert replaced.json()["artifact"]["entries"] == []


def test_linked_student_updates_unavailable_and_secret_errors_are_safe(client):
    activate_project(client)
    verification = prepare_linked_verification(client)
    ids = [target["verification_target_id"] for target in verification["verification_targets"][:2]]
    artifact = client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": ids
    }, headers=auth_headers()).json()["artifact"]
    first, second = artifact["evidence_targets"]
    response = client.put("/workflow/1/evidence", json={
        "target_updates": [
            {
                "evidence_target_id": first["evidence_target_id"],
                "evidence_status": "evidence_recorded",
                "entries": [{"kind": "test_output", "content": "2 passed"}],
                "explanation": "This is the student-provided output.",
            },
            {
                "evidence_target_id": second["evidence_target_id"],
                "evidence_status": "evidence_unavailable",
                "entries": [],
                "unavailable_reason": "The temporary logs were not retained.",
            },
        ]
    }, headers=auth_headers())
    assert response.status_code == 200
    saved = response.json()["artifact"]
    assert saved["evidence_record_complete"] is True
    assert saved["evidence_targets"][1]["entries"] == []

    before = client.get("/workflow/1", headers=auth_headers()).json()
    invalid = client.put("/workflow/1/evidence", json={
        "target_updates": [{
            "evidence_target_id": first["evidence_target_id"],
            "evidence_status": "evidence_recorded",
            "entries": [{
                "kind": "terminal_output",
                "content": "sb_secret_fake_test_marker",
            }],
        }]
    }, headers=auth_headers())
    assert invalid.status_code == 422
    assert "sb_secret_fake_test_marker" not in invalid.text
    assert client.get("/workflow/1", headers=auth_headers()).json() == before


def test_stale_linked_evidence_is_readable_preserved_and_not_editable(client):
    activate_project(client)
    verification = prepare_linked_verification(client)
    source_id = verification["verification_targets"][0]["verification_target_id"]
    artifact = client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [source_id]
    }, headers=auth_headers()).json()["artifact"]
    evidence_id = artifact["evidence_targets"][0]["evidence_target_id"]
    client.put("/workflow/1/evidence", json={"target_updates": [{
        "evidence_target_id": evidence_id,
        "evidence_status": "evidence_recorded",
        "entries": [{"kind": "note", "content": "Preserve this student Evidence."}],
    }]}, headers=auth_headers())
    client.put("/workflow/1/verification", json={"target_updates": [{
        "verification_target_id": source_id,
        "result_notes": "Selected context changed.",
    }]}, headers=auth_headers())

    preview = client.get(PREVIEW_ROUTE, headers=auth_headers()).json()
    assert preview["verification_state"] == "current"
    current = client.get("/workflow/1", headers=auth_headers()).json()["sections"]["evidence"]
    assert current["stale"] is True
    assert current["evidence_targets"][0]["entries"][0]["content"] == "Preserve this student Evidence."
    blocked = client.put("/workflow/1/evidence", json={"target_updates": [{
        "evidence_target_id": evidence_id,
        "explanation": "Blocked while stale.",
    }]}, headers=auth_headers())
    assert blocked.status_code == 409
    assert "rebuild" in blocked.json()["error"]["message"].lower()


def test_owner_phase_isolation_no_provider_and_neighbor_preservation(client, monkeypatch):
    activate_project(client, USER_A)
    verification = prepare_linked_verification(client, USER_A)
    source_id = verification["verification_targets"][0]["verification_target_id"]
    client.put("/workflow/1/prompt_builder", json=PROMPT_BUILDER,
               headers=auth_headers(USER_A))
    before = client.get("/workflow/1", headers=auth_headers(USER_A)).json()

    async def explode(self, prompt, temperature):
        raise AssertionError("Evidence handoff called a provider")

    for provider in (
        llm_service.StubProvider,
        llm_service.GeminiProvider,
        llm_service.OpenRouterProvider,
    ):
        monkeypatch.setattr(provider, "complete", explode, raising=True)
    assert client.get(PREVIEW_ROUTE, headers=auth_headers(USER_A)).status_code == 200
    assert client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [source_id]
    }, headers=auth_headers(USER_A)).status_code == 200

    after = client.get("/workflow/1", headers=auth_headers(USER_A)).json()
    for key in ("prompt_builder", "review_board", "verification", "implementation_import"):
        assert after["sections"][key] == before["sections"][key]
    assert after["change_map"] == before["change_map"]
    assert client.get(PREVIEW_ROUTE, headers=auth_headers(USER_B)).status_code == 409
    assert client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [source_id]
    }, headers=auth_headers(USER_B)).status_code == 409
    assert client.get("/workflow/2/evidence/from-verification",
                      headers=auth_headers(USER_A)).json()["verification_state"] == "verification_required"


def test_authenticated_deterministic_m16b3a_smoke(client, monkeypatch, caplog):
    checks = []

    def check(condition, label):
        assert condition, label
        checks.append(label)

    activate_project(client, USER_A)
    verification = prepare_linked_verification(client, USER_A)
    headers = auth_headers(USER_A)
    before = client.get("/workflow/1", headers=headers).json()
    check(client.get("/roadmap", headers=headers).status_code == 200, "1 owner authenticates")
    check(verification["initialized_from_review"] is True, "2 linked Verification loads")

    async def explode(self, prompt, temperature):
        raise AssertionError("Evidence handoff called a provider")

    for provider in (llm_service.StubProvider, llm_service.GeminiProvider,
                     llm_service.OpenRouterProvider):
        monkeypatch.setattr(provider, "complete", explode, raising=True)

    preview_response = client.get(PREVIEW_ROUTE, headers=headers)
    preview = preview_response.json()
    check(preview_response.status_code == 200, "3 preview loads")
    check(preview["targets"][0]["eligibility"] == "eligible", "4 pass eligible")
    check(preview["targets"][1]["eligibility"] == "eligible", "5 fail eligible")
    check(preview["targets"][2]["eligibility"] == "ineligible", "6 skipped ineligible")
    check(preview["targets"][3]["eligibility"] == "ineligible", "7 N/A ineligible")
    check(preview["targets"][4]["result"] == "unrecorded", "8 unrecorded ineligible")
    check(client.get("/workflow/1", headers=headers).json()["sections"]["evidence"] is None,
          "9 preview creates no Evidence")
    check(client.post(PREVIEW_ROUTE, json={"selected_verification_target_ids": []},
                      headers=headers).status_code == 422, "10 explicit selection required")

    pass_id = preview["targets"][0]["verification_target_id"]
    fail_id = preview["targets"][1]["verification_target_id"]
    created_response = client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [pass_id, fail_id]
    }, headers=headers)
    created = created_response.json()["artifact"]
    check(created_response.status_code == 200, "11 selected pass initializes")
    check(len(created["evidence_targets"]) == 2, "12 selected fail initializes")
    check(client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [preview["targets"][2]["verification_target_id"]],
        "replace_existing": True,
    }, headers=headers).status_code == 422, "13 skipped rejected")
    check(client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": [preview["targets"][3]["verification_target_id"]],
        "replace_existing": True,
    }, headers=headers).status_code == 422, "14 N/A rejected")
    check(client.post(PREVIEW_ROUTE, json={
        "selected_verification_target_ids": ["vt-000000000000"],
        "replace_existing": True,
    }, headers=headers).status_code == 422, "15 unknown rejected")
    check(all(not target["entries"] for target in created["evidence_targets"]),
          "16 no Evidence fabricated")
    check(all(target["evidence_status"] == "not_addressed" for target in created["evidence_targets"]),
          "17 no target marked evidenced")
    check(created["evidence_record_complete"] is False, "18 no automatic completion")

    first, second = created["evidence_targets"]
    saved_response = client.put("/workflow/1/evidence", json={"target_updates": [
        {
            "evidence_target_id": first["evidence_target_id"],
            "evidence_status": "evidence_recorded",
            "entries": [{"kind": "test_output", "content": "1 passed"}],
        },
        {
            "evidence_target_id": second["evidence_target_id"],
            "evidence_status": "evidence_unavailable",
            "entries": [],
            "unavailable_reason": "Output was not retained.",
        },
    ]}, headers=headers)
    saved = saved_response.json()["artifact"]
    check(saved_response.status_code == 200, "19 student Evidence saves")
    check(saved["evidence_targets"][1]["unavailable_reason"] is not None,
          "20 unavailable reason required")
    check(saved["evidence_targets"][1]["entries"] == [], "21 unavailable is not Evidence")
    check(client.get("/workflow/1", headers=headers).json()["sections"]["verification"] == before["sections"]["verification"],
          "22 Verification unchanged")
    current = client.get("/workflow/1", headers=headers).json()
    check(current["sections"]["review_board"] == before["sections"]["review_board"],
          "23 neighboring sections unchanged")
    check(client.get(PREVIEW_ROUTE, headers=auth_headers(USER_B)).status_code == 409,
          "24 cross-user denied")
    check(client.get("/workflow/2/evidence/from-verification", headers=headers).json()["eligible_count"] == 0,
          "25 phase isolation")

    client.put("/workflow/1/verification", json={"target_updates": [{
        "verification_target_id": pass_id,
        "result_notes": "Changed after Evidence initialization.",
    }]}, headers=headers)
    stale = client.get("/workflow/1", headers=headers).json()["sections"]["evidence"]
    check(stale["stale"] is True, "26 selected context stales Evidence")
    check(stale["evidence_targets"][0]["entries"][0]["content"] == "1 passed",
          "27 stale Evidence remains readable")

    client.put("/workflow/2/evidence", json=EVIDENCE, headers=headers)
    check(client.get("/workflow/2", headers=headers).json()["sections"]["evidence"]["summary"] == EVIDENCE["summary"],
          "28 manual Evidence remains compatible")
    check("Evidence handoff called a provider" not in caplog.text, "29 zero provider calls")
    check(first["check_snapshot"] not in caplog.text, "30 source content not logged")

    fake = client.app.dependency_overrides[get_project_repository]()
    fake._rows.clear()
    check(fake._rows == [], "31 temporary data cleaned")
    assert len(checks) == 31
