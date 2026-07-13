"""M16A.1 authenticated linked Review API and deterministic smoke tests."""

import json
import logging

import pytest

from app.services import llm_service
from app.services.project_repository import (
    get_gate_session_repository,
    get_project_repository,
)
from tests.fakes import InMemoryGateSessionRepository
from tests.test_change_map_routes import IMPORT_PAYLOAD, decide_all, generate, save_import
from tests.test_phase_routes import (  # noqa: F401 (client fixture)
    USER_A,
    USER_B,
    activate_project,
    auth_headers,
    client,
)
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, REVIEW_BOARD, VERIFICATION

INIT_ROUTE = "/workflow/1/review/from-change-map"


def prepare_confirmed_map(client, user_id=USER_A, phase=1):
    save_import(client, user_id=user_id, phase=phase)
    created = generate(client, user_id=user_id, phase=phase)
    assert created.status_code == 200
    decided = decide_all(client, user_id=user_id, phase=phase)
    assert decided.status_code == 200
    confirmed = client.post(
        f"/workflow/{phase}/change-map/confirm", headers=auth_headers(user_id)
    )
    assert confirmed.status_code == 200
    return confirmed.json()


def test_review_initialization_requires_auth(client):
    resp = client.post(INIT_ROUTE)
    assert resp.status_code == 401
    assert resp.json()["error"]["status"] == 401


def test_review_initialization_state_errors_use_safe_contract(client):
    resp = client.post(INIT_ROUTE, headers=auth_headers())
    assert resp.status_code == 409

    activate_project(client)
    resp = client.post(INIT_ROUTE, headers=auth_headers())
    assert resp.status_code == 409
    assert resp.json()["error"]["message"] == (
        "Create and review a Change Map before starting Review from it."
    )

    save_import(client)
    assert generate(client).status_code == 200
    resp = client.post(INIT_ROUTE, headers=auth_headers())
    assert resp.status_code == 409
    assert resp.json()["error"]["message"] == (
        "Confirm the reviewed Change Map before using it to start Review."
    )


def test_stale_map_and_invalid_phase_are_controlled(client):
    activate_project(client)
    prepare_confirmed_map(client)
    save_import(client, payload={
        **IMPORT_PAYLOAD, "student_summary": "A newer implementation import.",
    })
    resp = client.post(INIT_ROUTE, headers=auth_headers())
    assert resp.status_code == 409
    assert resp.json()["error"]["message"] == (
        "Regenerate and review the current Change Map before starting Review."
    )
    assert client.post(
        "/workflow/99/review/from-change-map", headers=auth_headers()
    ).status_code == 404


def test_full_linked_review_route_and_existing_frontend_contract(client):
    activate_project(client)
    change_map = prepare_confirmed_map(client)
    resp = client.post(INIT_ROUTE, headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["phase"] == 1 and body["section"] == "review_board"
    artifact = body["artifact"]
    assert artifact["initialized_from_change_map"] is True
    assert artifact["stale"] is False
    assert artifact["source_change_map_confirmed_at"] == change_map["confirmed_at"]
    assert artifact["source_change_map_generated_at"] == change_map["generated_at"]

    # Existing read path exposes the additive contract; no duplicate GET.
    read = client.get("/workflow/1", headers=auth_headers()).json()
    assert read["sections"]["review_board"] == artifact

    # The byte-compatible frontend payload still saves manual notes while
    # preserving linked targets/provenance.
    before_targets = artifact["review_targets"]
    resp = client.put(
        "/workflow/1/review_board", json=REVIEW_BOARD, headers=auth_headers()
    )
    assert resp.status_code == 200
    saved = resp.json()["artifact"]
    assert saved["files_changed"] == REVIEW_BOARD["files_changed"]
    assert saved["review_targets"] == before_targets
    assert saved["source_change_map_confirmed_at"] == change_map["confirmed_at"]


def test_target_update_and_provenance_forgery_protection_over_http(client):
    activate_project(client)
    prepare_confirmed_map(client)
    artifact = client.post(INIT_ROUTE, headers=auth_headers()).json()["artifact"]
    target = artifact["review_targets"][0]
    resp = client.put("/workflow/1/review_board", json={
        "target_updates": [{
            "review_target_id": target["review_target_id"],
            "review_decision": "revise",
            "student_rationale": "The ownership check needs a narrower query.",
        }],
    }, headers=auth_headers())
    assert resp.status_code == 200
    updated = resp.json()["artifact"]["review_targets"][0]
    assert updated["review_decision"] == "revise"

    forbidden = {
        "review_target_id": target["review_target_id"],
        "change_map_item_id": "cm-forged",
        "change_map_category": "behavior_change",
        "change_map_origin": "student_added",
        "change_map_student_decision": "confirmed",
        "change_text": "Forged snapshot",
        "source_resolution": "confirmed",
        "review_decision": "keep",
    }
    for payload in (
        {"review_targets": [forbidden]},
        {"source_change_map_confirmed_at": "forged"},
        {"source_change_map_generated_at": "forged"},
        {"stale": False},
        {"initialized_from_change_map": False},
    ):
        resp = client.put(
            "/workflow/1/review_board", json=payload, headers=auth_headers()
        )
        assert resp.status_code == 422
    current = client.get("/workflow/1", headers=auth_headers()).json()["sections"][
        "review_board"
    ]
    assert current["review_targets"][0]["change_map_item_id"] == target[
        "change_map_item_id"
    ]


def test_overwrite_is_explicit_and_request_cannot_supply_targets(client):
    activate_project(client)
    prepare_confirmed_map(client)
    assert client.put(
        "/workflow/1/review_board", json={"accepted": "Existing work."},
        headers=auth_headers(),
    ).status_code == 200
    resp = client.post(INIT_ROUTE, headers=auth_headers())
    assert resp.status_code == 409
    assert resp.json()["error"]["message"] == "Review work already exists for this phase."
    assert client.post(
        INIT_ROUTE,
        json={"replace_existing": True},
        headers=auth_headers(),
    ).status_code == 200
    for payload in (
        {"review_targets": []},
        {"replace_existing": True, "change_map_item_ids": []},
    ):
        assert client.post(
            INIT_ROUTE, json=payload, headers=auth_headers()
        ).status_code == 422


def test_change_map_updates_make_review_stale_until_explicit_reinitialization(client):
    activate_project(client)
    prepare_confirmed_map(client)
    linked = client.post(INIT_ROUTE, headers=auth_headers()).json()["artifact"]

    # A Change Map edit returns it to draft without rewriting the Review.
    change_map = client.get("/workflow/1", headers=auth_headers()).json()["change_map"]
    updates = [{
        "item_id": item["item_id"],
        "student_decision": item["student_decision"],
    } for item in change_map["items"] if item["origin"] == "ai_inferred"]
    assert client.put(
        "/workflow/1/change-map", json={"updates": updates}, headers=auth_headers()
    ).status_code == 200
    stale = client.get("/workflow/1", headers=auth_headers()).json()["sections"][
        "review_board"
    ]
    assert stale["stale"] is True
    assert stale["review_targets"] == linked["review_targets"]

    # Reconfirmation changes the source version; the old Review remains stale.
    assert client.post(
        "/workflow/1/change-map/confirm", headers=auth_headers()
    ).status_code == 200
    assert client.get("/workflow/1", headers=auth_headers()).json()["sections"][
        "review_board"
    ]["stale"] is True
    rebound = client.post(
        INIT_ROUTE, json={"replace_existing": True}, headers=auth_headers()
    ).json()["artifact"]
    assert rebound["stale"] is False
    assert rebound["source_change_map_confirmed_at"] != linked[
        "source_change_map_confirmed_at"
    ]


def test_other_user_and_other_phase_are_isolated(client):
    activate_project(client, USER_A)
    prepare_confirmed_map(client, USER_A)
    mine = client.post(INIT_ROUTE, headers=auth_headers(USER_A)).json()["artifact"]

    assert client.post(INIT_ROUTE, headers=auth_headers(USER_B)).status_code == 409
    assert client.get("/workflow/1", headers=auth_headers(USER_B)).status_code == 409
    assert client.put(
        "/workflow/1/review_board",
        json={"target_updates": [{
            "review_target_id": mine["review_targets"][0]["review_target_id"],
            "review_decision": "remove",
        }]},
        headers=auth_headers(USER_B),
    ).status_code == 409
    assert client.get("/workflow/2", headers=auth_headers(USER_A)).json()["sections"][
        "review_board"
    ] is None
    assert client.get("/workflow/1", headers=auth_headers(USER_A)).json()["sections"][
        "review_board"
    ]["review_targets"] == mine["review_targets"]


def test_review_initialization_never_calls_any_provider(client, monkeypatch):
    activate_project(client)
    prepare_confirmed_map(client)

    async def explode(self, prompt, temperature):
        raise AssertionError("Review initialization must not call a provider")

    for provider in (
        llm_service.StubProvider,
        llm_service.GeminiProvider,
        llm_service.OpenRouterProvider,
    ):
        monkeypatch.setattr(provider, "complete", explode, raising=True)
    assert client.post(INIT_ROUTE, headers=auth_headers()).status_code == 200


def test_authenticated_deterministic_smoke_40_checks(
    client, monkeypatch, caplog
):
    """The canonical M16A.1 smoke checklist, over authenticated HTTP.

    Change Map generation legitimately uses the existing deterministic stub.
    Provider methods are replaced with explosions before Review initialization
    to prove the M16A.1 path itself makes zero provider calls.
    """
    checks: list[str] = []

    def check(condition, label):
        assert condition, label
        checks.append(label)

    client.app.dependency_overrides[get_gate_session_repository] = (
        lambda: InMemoryGateSessionRepository()
    )

    activate_project(client, USER_A)
    check(client.get("/phases", headers=auth_headers(USER_A)).status_code == 200,
          "1 owner creates project")
    save_import(client, USER_A)
    check(client.get("/workflow/1", headers=auth_headers(USER_A)).json()["sections"][
        "implementation_import"
    ] is not None, "2 owner saves Implementation Import")
    generated = generate(client, USER_A)
    check(generated.status_code == 200, "3 owner generates Change Map using stub")

    items = generated.json()["items"]
    updates = []
    for item in items:
        decision = {
            "changed_file": "confirmed",
            "behavior_change": "needs_inspection",
            "question_to_understand": "rejected",
        }.get(item["category"], "confirmed")
        updates.append({"item_id": item["item_id"], "student_decision": decision})
    student_items = [
        {"category": "implementation_decision", "student_text": "Kept owner_filter."},
        {"category": "out_of_scope_change", "student_text": "Logging also changed."},
        {"category": "security_sensitive_area", "student_text": "Owner checks changed."},
        {"category": "unresolved_risk", "student_text": "Cache invalidation is unclear.",
         "student_decision": "uncertain"},
        {"category": "unverified_behavior", "student_text": "Wrong-user behavior is untested."},
    ]
    reviewed = client.put("/workflow/1/change-map", json={
        "updates": updates, "student_added_items": student_items,
    }, headers=auth_headers(USER_A))
    check(reviewed.status_code == 200, "4 owner reviews all Change Map items")
    confirmed = client.post(
        "/workflow/1/change-map/confirm", headers=auth_headers(USER_A)
    )
    check(confirmed.status_code == 200, "5 owner confirms Change Map")

    # Seed unrelated sections before Review and capture Project Defense state.
    for section, payload in (
        ("prompt_builder", PROMPT_BUILDER),
        ("evidence", EVIDENCE),
        ("verification", VERIFICATION),
    ):
        assert client.put(
            f"/workflow/1/{section}", json=payload, headers=auth_headers(USER_A)
        ).status_code == 200
    defense_before = client.get("/gate/current", headers=auth_headers(USER_A)).json()

    async def explode(self, prompt, temperature):
        raise AssertionError("Review initialization called a provider")

    for provider in (
        llm_service.StubProvider,
        llm_service.GeminiProvider,
        llm_service.OpenRouterProvider,
    ):
        monkeypatch.setattr(provider, "complete", explode, raising=True)

    caplog.set_level(logging.INFO)
    caplog.clear()
    init = client.post(INIT_ROUTE, headers=auth_headers(USER_A))
    check(init.status_code == 200, "6 linked Review initialization succeeds")
    artifact = init.json()["artifact"]
    current_map = confirmed.json()
    check(
        artifact["source_change_map_confirmed_at"] == current_map["confirmed_at"]
        and artifact["source_change_map_generated_at"] == current_map["generated_at"],
        "7 source binding matches current Change Map",
    )
    categories = [target["change_map_category"] for target in artifact["review_targets"]]
    check(categories == sorted(categories, key=(
        "behavior_change", "implementation_decision", "out_of_scope_change",
        "security_sensitive_area", "unresolved_risk", "unverified_behavior",
    ).index), "8 target ordering is deterministic")
    check(
        [target["review_target_id"] for target in artifact["review_targets"]]
        == [target["review_target_id"] for target in client.get(
            "/workflow/1", headers=auth_headers(USER_A)
        ).json()["sections"]["review_board"]["review_targets"]],
        "9 target ids are deterministic",
    )
    check(set(categories) == {
        "behavior_change", "implementation_decision", "out_of_scope_change",
        "security_sensitive_area", "unresolved_risk", "unverified_behavior",
    }, "10 relevant categories appear")
    linked_item_ids = {target["change_map_item_id"] for target in artifact["review_targets"]}
    excluded = {item["category"]: item["item_id"] for item in reviewed.json()["items"]
                if item["origin"] == "ai_inferred"}
    check(excluded["changed_file"] not in linked_item_ids,
          "11 changed-file category is not a decision target")
    check(excluded["question_to_understand"] not in linked_item_ids,
          "12 question category is not a decision target")
    check(all(target["change_map_student_decision"] != "rejected"
              for target in artifact["review_targets"]),
          "13 rejected Change Map item is absent")
    check(any(target["source_resolution"] == "unresolved"
              for target in artifact["review_targets"]),
          "14 unresolved item remains cautious")
    effective = {
        item["item_id"]: item.get("student_text") or item.get("draft_text")
        for item in reviewed.json()["items"]
    }
    check(all(target["change_text"] == effective[target["change_map_item_id"]]
              for target in artifact["review_targets"]),
          "15 source snapshots match effective Change Map text")
    artifact_text = json.dumps(artifact)
    check(IMPORT_PAYLOAD["content"] not in artifact_text,
          "16 raw import is absent")
    check("source_references" not in artifact_text and "supporting_excerpt" not in artifact_text,
          "17 source excerpts are absent")
    check(all(target["review_decision"] == "pending"
              for target in artifact["review_targets"]),
          "18 Review decisions begin pending")

    first = artifact["review_targets"][0]
    updated = client.put("/workflow/1/review_board", json={
        "target_updates": [{
            "review_target_id": first["review_target_id"],
            "review_decision": "needs_verification",
            "student_rationale": "Run the behavior smoke test.",
        }],
    }, headers=auth_headers(USER_A))
    check(updated.status_code == 200, "19 student update succeeds")
    forged = client.put("/workflow/1/review_board", json={
        "source_change_map_confirmed_at": "forged",
    }, headers=auth_headers(USER_A))
    check(forged.status_code == 422, "20 client cannot rewrite source provenance")
    check(client.post(INIT_ROUTE, headers=auth_headers(USER_A)).status_code == 409,
          "21 existing Review is not overwritten accidentally")
    replaced = client.post(INIT_ROUTE, json={"replace_existing": True},
                           headers=auth_headers(USER_A))
    check(replaced.status_code == 200 and all(
        target["review_decision"] == "pending"
        for target in replaced.json()["artifact"]["review_targets"]
    ), "22 explicit replacement works")

    cmap = client.get("/workflow/1", headers=auth_headers(USER_A)).json()["change_map"]
    map_updates = [{
        "item_id": item["item_id"], "student_decision": item["student_decision"]
    } for item in cmap["items"] if item["origin"] == "ai_inferred"]
    student_replacement = [{
        "category": item["category"],
        "student_text": item["student_text"],
        "student_note": item["student_note"],
        "student_decision": item["student_decision"],
    } for item in cmap["items"] if item["origin"] == "student_added"]
    assert client.put("/workflow/1/change-map", json={
        "updates": map_updates, "student_added_items": student_replacement,
    }, headers=auth_headers(USER_A)).status_code == 200
    stale_read = client.get("/workflow/1", headers=auth_headers(USER_A)).json()["sections"][
        "review_board"
    ]
    check(stale_read["stale"] is True, "23 Change Map edit makes Review stale")
    check(bool(stale_read["review_targets"]), "24 stale Review remains readable")
    check(client.put("/workflow/1/review_board", json={"stale": False},
                     headers=auth_headers(USER_A)).status_code == 422,
          "25 client cannot clear staleness")
    assert client.post("/workflow/1/change-map/confirm",
                       headers=auth_headers(USER_A)).status_code == 200
    check(client.get("/workflow/1", headers=auth_headers(USER_A)).json()["sections"][
        "review_board"
    ]["stale"] is True, "26 Change Map reconfirmation leaves old Review stale")
    rebound = client.post(INIT_ROUTE, json={"replace_existing": True},
                          headers=auth_headers(USER_A))
    check(rebound.status_code == 200 and rebound.json()["artifact"]["stale"] is False,
          "27 explicit reinitialization rebinds")

    target_id = rebound.json()["artifact"]["review_targets"][0]["review_target_id"]
    check(client.post(INIT_ROUTE, headers=auth_headers(USER_B)).status_code == 409,
          "28 another user cannot initialize")
    check(client.get("/workflow/1", headers=auth_headers(USER_B)).status_code == 409,
          "29 another user cannot read")
    check(client.put("/workflow/1/review_board", json={
        "target_updates": [{"review_target_id": target_id, "review_decision": "remove"}],
    }, headers=auth_headers(USER_B)).status_code == 409,
          "30 another user cannot update")
    check(client.get("/workflow/2", headers=auth_headers(USER_A)).json()["sections"][
        "review_board"
    ] is None, "31 another phase remains isolated")

    sections = client.get("/workflow/1", headers=auth_headers(USER_A)).json()["sections"]
    check(sections["prompt_builder"]["generated_prompt"] == PROMPT_BUILDER["generated_prompt"],
          "32 Prompt Builder remains intact")
    check(sections["implementation_import"]["content"] == IMPORT_PAYLOAD["content"],
          "33 Implementation Import remains intact")
    check(client.get("/workflow/1", headers=auth_headers(USER_A)).json()["change_map"][
        "status"
    ] == "confirmed", "34 Change Map remains intact")
    check(sections["evidence"]["summary"] == EVIDENCE["summary"],
          "35 Evidence remains intact")
    check(sections["verification"]["explanation"] == VERIFICATION["explanation"],
          "36 Verification remains intact")
    check(client.get("/gate/current", headers=auth_headers(USER_A)).json() == defense_before,
          "37 Project Defense remains unchanged")
    check(rebound.status_code == 200, "38 no provider call occurs during Review initialization")
    snapshots = [target["change_text"] for target in rebound.json()["artifact"]["review_targets"]]
    check(all(snapshot not in caplog.text for snapshot in snapshots),
          "39 no raw linked text appears in logs")

    fake = client.app.dependency_overrides[get_project_repository]()
    fake._rows.clear()
    check(fake._rows == [], "40 temporary data is cleaned up")
    assert len(checks) == 40
