"""M16B.1 authenticated linked Verification API and deterministic smoke."""

import json

import pytest

from app.services import llm_service
from app.services.project_repository import (
    get_gate_session_repository,
    get_project_repository,
)
from tests.fakes import InMemoryGateSessionRepository
from tests.test_phase_routes import (  # noqa: F401 (client fixture)
    USER_A,
    USER_B,
    activate_project,
    auth_headers,
    client,
)
from tests.test_review_routes import prepare_confirmed_map
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, REVIEW_BOARD, VERIFICATION

INIT_ROUTE = "/workflow/1/verification/from-review"


def prepare_completed_review(client, user_id=USER_A, phase=1, *, needs_count=1):
    prepare_confirmed_map(client, user_id=user_id, phase=phase)
    initialized = client.post(
        f"/workflow/{phase}/review/from-change-map", headers=auth_headers(user_id)
    )
    assert initialized.status_code == 200
    targets = initialized.json()["artifact"]["review_targets"]
    updates = [
        {
            "review_target_id": target["review_target_id"],
            "review_decision": "needs_verification" if index < needs_count else "keep",
            "student_rationale": "I need to test this behavior." if index < needs_count else None,
        }
        for index, target in enumerate(targets)
    ]
    saved = client.put(
        f"/workflow/{phase}/review_board",
        json={"target_updates": updates},
        headers=auth_headers(user_id),
    )
    assert saved.status_code == 200
    return saved.json()["artifact"]


def test_initialization_requires_auth(client):
    response = client.post(INIT_ROUTE)
    assert response.status_code == 401
    assert response.json()["error"]["status"] == 401


def test_review_readiness_errors_are_safe_conflicts(client):
    assert client.post(INIT_ROUTE, headers=auth_headers()).status_code == 409
    activate_project(client)
    response = client.post(INIT_ROUTE, headers=auth_headers())
    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Complete Review before creating Verification suggestions."
    )

    prepare_confirmed_map(client)
    client.post("/workflow/1/review/from-change-map", headers=auth_headers())
    response = client.post(INIT_ROUTE, headers=auth_headers())
    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Finish and save Review before creating Verification suggestions."
    )
    assert client.post(
        "/workflow/99/verification/from-review", headers=auth_headers()
    ).status_code == 404


def test_explicit_initialization_read_and_legacy_put_compatibility(client):
    activate_project(client)
    review = prepare_completed_review(client)
    response = client.post(INIT_ROUTE, headers=auth_headers())
    assert response.status_code == 200
    artifact = response.json()["artifact"]
    assert artifact["initialized_from_review"] is True
    assert artifact["stale"] is False
    assert len(artifact["verification_targets"]) == 1
    target = artifact["verification_targets"][0]
    source = next(
        item for item in review["review_targets"]
        if item["review_target_id"] == target["review_target_id"]
    )
    assert target["source_text"] == source["change_text"]
    assert target["result"] is None

    read = client.get("/workflow/1", headers=auth_headers()).json()
    assert read["sections"]["verification"] == artifact

    # The current frontend payload is still accepted and linked provenance is
    # copied server-side rather than removed by the legacy full-section save.
    saved = client.put(
        "/workflow/1/verification", json=VERIFICATION, headers=auth_headers()
    )
    assert saved.status_code == 200
    after = saved.json()["artifact"]
    assert [
        {key: value for key, value in check.items() if value is not None}
        for check in after["checks"]
    ] == VERIFICATION["checks"]
    assert after["source_review_binding"] == artifact["source_review_binding"]
    assert after["verification_targets"] == artifact["verification_targets"]


def test_target_update_and_provenance_protection_over_http(client):
    activate_project(client)
    prepare_completed_review(client)
    artifact = client.post(INIT_ROUTE, headers=auth_headers()).json()["artifact"]
    target = artifact["verification_targets"][0]
    updated = client.put("/workflow/1/verification", json={
        "target_updates": [{
            "verification_target_id": target["verification_target_id"],
            "student_check": "Perform the proposed normal-flow check.",
            "result": "pass",
            "result_notes": "Observed the expected response.",
        }]
    }, headers=auth_headers())
    assert updated.status_code == 200
    result = updated.json()["artifact"]["verification_targets"][0]
    assert result["result"] == "pass"
    assert result["source_text"] == target["source_text"]

    forbidden = {
        "verification_target_id": target["verification_target_id"],
        "result": "pass",
        "suggested_check": "Forged",
    }
    assert client.put(
        "/workflow/1/verification",
        json={"target_updates": [forbidden]},
        headers=auth_headers(),
    ).status_code == 422
    assert client.put(
        "/workflow/1/verification",
        json={"source_review_binding": {}, "stale": False},
        headers=auth_headers(),
    ).status_code == 422


def test_existing_work_is_never_silently_overwritten_and_replacement_rebinds(client):
    activate_project(client)
    prepare_completed_review(client)
    assert client.put(
        "/workflow/1/verification", json=VERIFICATION, headers=auth_headers()
    ).status_code == 200
    conflict = client.post(INIT_ROUTE, headers=auth_headers())
    assert conflict.status_code == 409
    assert conflict.json()["error"]["message"] == (
        "Verification work already exists for this phase."
    )
    replaced = client.post(
        INIT_ROUTE, json={"replace_existing": True}, headers=auth_headers()
    )
    assert replaced.status_code == 200
    artifact = replaced.json()["artifact"]
    assert artifact["checks"] == []
    assert all(target["result"] is None for target in artifact["verification_targets"])


def test_zero_target_initialization_is_successful_and_not_complete(client):
    activate_project(client)
    prepare_completed_review(client, needs_count=0)
    response = client.post(INIT_ROUTE, headers=auth_headers())
    assert response.status_code == 200
    artifact = response.json()["artifact"]
    assert artifact["verification_targets"] == []
    assert artifact["checks"] == []
    assert artifact["initialized_from_review"] is True


def test_no_provider_is_called_by_initialization(client, monkeypatch):
    activate_project(client)
    prepare_completed_review(client)

    async def explode(self, prompt, temperature):
        raise AssertionError("Verification initialization called a provider")

    for provider in (
        llm_service.StubProvider,
        llm_service.GeminiProvider,
        llm_service.OpenRouterProvider,
    ):
        monkeypatch.setattr(provider, "complete", explode, raising=True)
    assert client.post(INIT_ROUTE, headers=auth_headers()).status_code == 200


def test_owner_phase_isolation_and_no_cross_user_inference(client):
    activate_project(client, USER_A)
    prepare_completed_review(client, USER_A)
    mine = client.post(INIT_ROUTE, headers=auth_headers(USER_A)).json()["artifact"]
    target_id = mine["verification_targets"][0]["verification_target_id"]

    assert client.post(INIT_ROUTE, headers=auth_headers(USER_B)).status_code == 409
    assert client.get("/workflow/1", headers=auth_headers(USER_B)).status_code == 409
    assert client.put(
        "/workflow/1/verification",
        json={"target_updates": [{
            "verification_target_id": target_id,
            "result": "pass",
        }]},
        headers=auth_headers(USER_B),
    ).status_code == 409
    assert client.get("/workflow/2", headers=auth_headers(USER_A)).json()["sections"][
        "verification"
    ] is None


def test_authenticated_deterministic_m16b1_smoke(client, monkeypatch, caplog):
    checks = []

    def check(condition, label):
        assert condition, label
        checks.append(label)

    activate_project(client, USER_A)
    client.app.dependency_overrides[get_gate_session_repository] = (
        lambda: InMemoryGateSessionRepository()
    )
    check(client.get("/roadmap", headers=auth_headers(USER_A)).status_code == 200,
          "1 owner creates active project")
    review = prepare_completed_review(client, USER_A)
    state_before = client.get("/workflow/1", headers=auth_headers(USER_A)).json()
    check(state_before["sections"]["implementation_import"] is not None,
          "2 owner saves Implementation Import")
    check(state_before["change_map"] is not None,
          "3 Change Map generated through stub flow")
    check(all(item["student_decision"] != "pending_review"
              for item in state_before["change_map"]["items"]),
          "4 student reviews Change Map")
    check(state_before["change_map"]["status"] == "confirmed",
          "5 student confirms Change Map")
    check(review["initialized_from_change_map"] is True,
          "6 Review initializes")
    needs = [t for t in review["review_targets"] if t["review_decision"] == "needs_verification"]
    check(bool(needs), "7 selected Review item marked needs verification")
    check(all(t["review_decision"] != "pending" for t in review["review_targets"]),
          "8 Review completed and saved")
    check(state_before["sections"]["verification"] is None,
          "9 no automatic Verification initialization")

    async def explode(self, prompt, temperature):
        raise AssertionError("Verification initialization called a provider")

    for provider in (llm_service.StubProvider, llm_service.GeminiProvider,
                     llm_service.OpenRouterProvider):
        monkeypatch.setattr(provider, "complete", explode, raising=True)
    created_response = client.post(INIT_ROUTE, headers=auth_headers(USER_A))
    check(created_response.status_code == 200, "10 explicit Verification initialization succeeds")
    check(created_response.status_code == 200, "11 zero provider calls during initialization")
    artifact = created_response.json()["artifact"]
    targets = artifact["verification_targets"]
    check(len(targets) == len(needs), "12 only needs-testing targets included")
    check({t["review_target_id"] for t in targets} == {t["review_target_id"] for t in needs},
          "13 other Review decisions excluded")
    target = targets[0]
    source = needs[0]
    check(target["category"] == source["change_map_category"], "14 category preserved")
    check(target["source_text"] == source["change_text"], "15 effective text preserved")
    check(target["source_rationale"] == source["student_rationale"], "16 rationale preserved")
    first_id, first_suggestion = target["verification_target_id"], target["suggested_check"]
    replacement = client.post(INIT_ROUTE, json={"replace_existing": True},
                              headers=auth_headers(USER_A)).json()["artifact"]
    check(replacement["verification_targets"][0]["suggested_check"] == first_suggestion,
          "17 suggestions deterministic")
    check(replacement["verification_targets"][0]["verification_target_id"] == first_id,
          "18 target ids deterministic")
    check(all(t["result"] is None for t in targets), "19 every result unperformed")
    check(not any(t["result"] == "pass" for t in targets), "20 no pass")
    check(not any(t["result"] == "fail" for t in targets), "21 no fail")
    check(not any(t["result"] == "skipped" for t in targets), "22 no skipped")
    check(not any(t["result"] == "not_applicable" for t in targets), "23 no not-applicable")
    serialized = json.dumps(artifact)
    check(state_before["sections"]["implementation_import"]["content"] not in serialized,
          "24 raw import absent")
    check("source_references" not in serialized and "supporting_excerpt" not in serialized,
          "25 Change Map excerpts absent")
    check(target["source_text"] not in caplog.text, "26 source content not logged")
    check(client.post(INIT_ROUTE, headers=auth_headers(USER_A)).status_code == 409,
          "27 existing Verification protected")
    check(replacement["stale"] is False, "28 explicit replacement works")

    review_target = review["review_targets"][0]
    changed = client.put("/workflow/1/review_board", json={
        "target_updates": [{
            "review_target_id": review_target["review_target_id"],
            "review_decision": "keep",
        }]
    }, headers=auth_headers(USER_A))
    check(changed.status_code == 200, "29 Review decision changed")
    stale = client.get("/workflow/1", headers=auth_headers(USER_A)).json()["sections"]["verification"]
    check(stale["stale"] is True, "30 changed Review makes Verification stale")
    check(stale["verification_targets"][0]["verification_target_id"] == first_id,
          "31 stale Verification remains readable")
    check(client.put("/workflow/1/verification", json={"stale": False},
                     headers=auth_headers(USER_A)).status_code == 422,
          "32 client cannot clear stale")
    rebound = client.post(INIT_ROUTE, json={"replace_existing": True},
                          headers=auth_headers(USER_A))
    check(rebound.status_code == 200 and rebound.json()["artifact"]["stale"] is False,
          "33 explicit replacement rebinds")
    check(client.post(INIT_ROUTE, headers=auth_headers(USER_B)).status_code == 409,
          "34 another user cannot initialize")
    check(client.get("/workflow/1", headers=auth_headers(USER_B)).status_code == 409,
          "35 another user cannot read")
    check(client.put("/workflow/1/verification", json=VERIFICATION,
                     headers=auth_headers(USER_B)).status_code == 409,
          "36 another user cannot update")
    check(client.get("/workflow/2", headers=auth_headers(USER_A)).json()["sections"]["verification"] is None,
          "37 another phase isolated")
    final = client.get("/workflow/1", headers=auth_headers(USER_A)).json()
    check(final["sections"]["prompt_builder"] is None, "38 Prompt Builder intact")
    check(final["sections"]["implementation_import"] == state_before["sections"]["implementation_import"],
          "39 Import intact")
    check(final["change_map"] == state_before["change_map"], "40 Change Map intact")
    check(final["sections"]["review_board"] is not None, "41 Review intact")
    check(final["sections"]["evidence"] is None, "42 Evidence unchanged")
    check(client.get("/gate/current", headers=auth_headers(USER_A)).status_code == 200,
          "43 Project Defense unchanged and no unexpected API errors")

    fake = client.app.dependency_overrides[get_project_repository]()
    fake._rows.clear()
    assert fake._rows == []
    assert len(checks) == 43
