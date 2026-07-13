"""M16A.1 deterministic Change Map -> Review service tests."""

import copy
import inspect

import pytest

from app.schemas.change_map import StoredChangeMap
from app.schemas.workflow import StoredReviewBoardArtifact
from app.services import review_service, workflow_service
from app.services.phase_service import PhaseNotFoundError, WorkspaceNotReadyError
from app.services.review_service import (
    InvalidReviewUpdateError,
    ReviewAlreadyExistsError,
    ReviewChangeMapDraftError,
    ReviewChangeMapMissingError,
    ReviewChangeMapStaleError,
    create_from_change_map,
    derive_review_targets,
    get_stored_review,
    needs_verification_targets,
    pending_review_targets,
    review_complete,
    review_is_stale,
    reviewed_target_count,
)
from app.services.defense_context_service import (
    build_defense_context,
    render_defense_context,
)
from app.services.workflow_service import InvalidArtifactError, save_section
from tests.fakes import InMemoryProjectRepository
from tests.test_phase_service import OTHER_USER, USER, run, seed_active_project
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, VERIFICATION

IMPORT = {
    "source_kind": "git_diff",
    "content": "+def owner_filter(task, user_id):\n+    return task.user_id == user_id",
    "changed_files": ["app/tasks.py"],
    "student_summary": "Ownership checks and behavior were changed.",
}


def ai_item(
    item_id,
    category,
    decision="confirmed",
    text=None,
    student_text=None,
):
    return {
        "item_id": item_id,
        "origin": "ai_inferred",
        "category": category,
        "draft_text": text or f"Snapshot for {category}.",
        "ai_uncertainty": "supported",
        "uncertainty_reason": None,
        "source_references": [{
            "source_field": "changed_files",
            "source_kind": "git_diff",
            "file_path": "app/tasks.py",
            "supporting_excerpt": None,
        }],
        "student_decision": decision,
        "student_text": student_text,
        "student_note": None,
    }


def student_item(item_id, category, decision="confirmed", text=None):
    return {
        "item_id": item_id,
        "origin": "student_added",
        "category": category,
        "draft_text": None,
        "ai_uncertainty": None,
        "uncertainty_reason": None,
        "source_references": [],
        "student_decision": decision,
        "student_text": text or f"Student snapshot for {category}.",
        "student_note": None,
    }


def default_items():
    # Deliberately shuffled: derivation must use category priority, then map order.
    return [
        ai_item("cm-risk", "unresolved_risk", "uncertain"),
        ai_item("cm-file", "changed_file"),
        ai_item("cm-impl", "implementation_decision"),
        ai_item("cm-behavior", "behavior_change"),
        ai_item("cm-safety", "security_sensitive_area", "needs_inspection"),
        ai_item("cm-scope", "out_of_scope_change", "rejected"),
        ai_item("cm-unverified", "unverified_behavior"),
        ai_item("cm-question", "question_to_understand"),
        student_item("sa-scope", "out_of_scope_change"),
    ]


def seed_map(repo=None, *, phase=1, items=None, status="confirmed", user=USER):
    repo = repo or InMemoryProjectRepository()
    if run(repo.get_project(user)) is None:
        seed_active_project(repo, user=user)
    run(save_section(repo, user, phase, "implementation_import", IMPORT))
    project = run(repo.get_project(user))
    saved_at = project["workflow_artifacts"][str(phase)]["implementation_import"]["saved_at"]
    data = {
        "schema_version": "1.0",
        "status": status,
        "source_import_saved_at": saved_at,
        "generated_at": f"2026-07-13T0{phase}:00:00+00:00",
        "confirmed_at": (
            f"2026-07-13T0{phase}:30:00+00:00" if status == "confirmed" else None
        ),
        "source_redacted": False,
        "source_truncated": False,
        "items": default_items() if items is None else items,
    }
    stored = StoredChangeMap.model_validate(data)
    project = run(repo.get_project(user))
    run(workflow_service.store_change_map(
        repo, user, project, phase, stored.model_dump(mode="json")
    ))
    return repo, stored


def initialized(repo, *, phase=1, replace=False, user=USER):
    return run(create_from_change_map(
        repo, user, phase, replace_existing=replace
    ))["artifact"]


def test_category_filtering_order_ids_snapshots_and_source_states_are_deterministic():
    _, change_map = seed_map()
    first = derive_review_targets(change_map)
    second = derive_review_targets(change_map)
    assert [target.model_dump() for target in first] == [
        target.model_dump() for target in second
    ]
    assert [target.change_map_category for target in first] == [
        "behavior_change",
        "implementation_decision",
        "out_of_scope_change",
        "security_sensitive_area",
        "unresolved_risk",
        "unverified_behavior",
    ]
    assert all(target.review_target_id.startswith("rv-") for target in first)
    assert all(target.review_decision == "pending" for target in first)
    assert "cm-file" not in {target.change_map_item_id for target in first}
    assert "cm-question" not in {target.change_map_item_id for target in first}
    assert "cm-scope" not in {target.change_map_item_id for target in first}
    scope = next(target for target in first if target.change_map_item_id == "sa-scope")
    assert scope.change_map_origin == "student_added"
    assert scope.change_map_student_decision == "confirmed"
    assert scope.change_text == "Student snapshot for out_of_scope_change."
    unresolved = {
        target.change_map_item_id: target for target in first
        if target.source_resolution == "unresolved"
    }
    assert set(unresolved) == {"cm-risk", "cm-safety"}
    assert unresolved["cm-risk"].change_map_student_decision == "uncertain"
    assert unresolved["cm-safety"].change_map_student_decision == "needs_inspection"


def test_initialization_stores_only_bounded_binding_and_preserves_other_sections():
    repo, change_map = seed_map()
    for section, payload in (
        ("prompt_builder", PROMPT_BUILDER),
        ("evidence", EVIDENCE),
        ("verification", VERIFICATION),
    ):
        run(save_section(repo, USER, 1, section, payload))
    before = run(repo.get_project(USER))["workflow_artifacts"]["1"]

    artifact = initialized(repo)
    assert artifact["initialized_from_change_map"] is True
    assert artifact["stale"] is False
    assert artifact["source_change_map_confirmed_at"] == change_map.confirmed_at
    assert artifact["source_change_map_generated_at"] == change_map.generated_at
    assert artifact["review_targets"]
    serialized = repr(artifact)
    assert IMPORT["content"] not in serialized
    assert "source_references" not in serialized
    assert "supporting_excerpt" not in serialized

    after = run(repo.get_project(USER))["workflow_artifacts"]["1"]
    assert after["prompt_builder"] == before["prompt_builder"]
    assert after["implementation_import"] == before["implementation_import"]
    assert after["change_map"] == before["change_map"]
    assert after["evidence"] == before["evidence"]
    assert after["verification"] == before["verification"]


def test_initialization_requires_map_confirmation_and_current_import_binding():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    with pytest.raises(ReviewChangeMapMissingError, match="Create and review"):
        initialized(repo)

    repo, _ = seed_map(status="draft", items=[ai_item(
        "cm-pending", "behavior_change", "pending_review"
    )])
    with pytest.raises(ReviewChangeMapDraftError, match="Confirm the reviewed"):
        initialized(repo)

    repo, _ = seed_map()
    run(save_section(repo, USER, 1, "implementation_import", {
        **IMPORT, "student_summary": "A newer import version.",
    }))
    with pytest.raises(ReviewChangeMapStaleError, match="Regenerate and review"):
        initialized(repo)


def test_existing_manual_empty_and_linked_review_all_need_explicit_replacement():
    for manual in ({}, {"accepted": "I kept the route."}):
        repo, _ = seed_map()
        run(save_section(repo, USER, 1, "review_board", manual))
        with pytest.raises(ReviewAlreadyExistsError, match="already exists"):
            initialized(repo)
        assert initialized(repo, replace=True)["review_targets"]

    repo, _ = seed_map()
    initialized(repo)
    with pytest.raises(ReviewAlreadyExistsError, match="already exists"):
        initialized(repo)


def test_explicit_replacement_resets_target_decisions_without_version_history():
    repo, _ = seed_map()
    first = initialized(repo)
    target = first["review_targets"][0]
    run(save_section(repo, USER, 1, "review_board", {
        "accepted": "Manual note",
        "target_updates": [{
            "review_target_id": target["review_target_id"],
            "review_decision": "keep",
        }],
    }))
    replaced = initialized(repo, replace=True)
    assert all(target["review_decision"] == "pending" for target in replaced["review_targets"])
    assert replaced["accepted"] is None
    phase_map = run(repo.get_project(USER))["workflow_artifacts"]["1"]
    assert isinstance(phase_map["review_board"], dict)
    assert "review_history" not in phase_map


@pytest.mark.parametrize(
    ("decision", "fields"),
    [
        ("pending", {}),
        ("keep", {}),
        ("revise", {"student_revision": "Use a narrower filter."}),
        ("remove", {}),
        ("needs_verification", {"student_rationale": "Run a wrong-user test."}),
        ("uncertain", {}),
    ],
)
def test_student_can_update_each_review_decision(decision, fields):
    repo, _ = seed_map()
    artifact = initialized(repo)
    target = artifact["review_targets"][0]
    saved = run(save_section(repo, USER, 1, "review_board", {
        "target_updates": [{
            "review_target_id": target["review_target_id"],
            "review_decision": decision,
            **fields,
        }],
    }))["artifact"]
    updated = next(
        item for item in saved["review_targets"]
        if item["review_target_id"] == target["review_target_id"]
    )
    assert updated["review_decision"] == decision


def test_review_update_preserves_every_server_owned_field():
    repo, _ = seed_map()
    before = initialized(repo)
    target = before["review_targets"][0]
    saved = run(save_section(repo, USER, 1, "review_board", {
        "files_changed": ["student-note.py"],
        "target_updates": [{
            "review_target_id": target["review_target_id"],
            "review_decision": "needs_verification",
            "student_rationale": "I still need to test this behavior.",
        }],
    }))["artifact"]
    assert saved["files_changed"] == ["student-note.py"]
    for key in ("source_change_map_confirmed_at", "source_change_map_generated_at"):
        assert saved[key] == before[key]
    before_sources = [{
        key: item[key] for key in (
            "review_target_id",
            "change_map_item_id",
            "change_map_category",
            "change_map_origin",
            "change_map_student_decision",
            "change_text",
            "source_resolution",
        )
    } for item in before["review_targets"]]
    saved_sources = [{key: item[key] for key in source} for item, source in zip(
        saved["review_targets"], before_sources
    )]
    assert saved_sources == before_sources


def test_invalid_target_updates_and_forged_provenance_are_rejected():
    repo, _ = seed_map()
    initialized(repo)
    with pytest.raises(InvalidArtifactError, match="does not match"):
        run(save_section(repo, USER, 1, "review_board", {
            "target_updates": [{
                "review_target_id": "rv-000000000000",
                "review_decision": "keep",
            }],
        }))
    for field, value in (
        ("source_change_map_confirmed_at", "forged"),
        ("source_change_map_generated_at", "forged"),
        ("review_targets", []),
        ("stale", False),
        ("initialized_from_change_map", True),
    ):
        with pytest.raises(InvalidArtifactError):
            run(save_section(repo, USER, 1, "review_board", {field: value}))


def test_manual_review_save_and_read_remain_byte_compatible():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    payload = {"accepted": "The existing Review path remains available."}
    saved = run(save_section(repo, USER, 1, "review_board", payload))["artifact"]
    read = run(workflow_service.get_phase_artifacts(repo, USER, 1))["sections"]["review_board"]
    assert saved == read
    assert read["accepted"] == payload["accepted"]
    assert "initialized_from_change_map" not in read
    assert "stale" not in read
    assert "review_targets" not in read


def test_review_staleness_is_computed_and_cannot_be_cleared():
    repo, change_map = seed_map()
    initialized(repo)
    project = run(repo.get_project(USER))
    review = get_stored_review(project, 1)
    assert review_is_stale(project, 1, review) is False

    draft = change_map.model_dump(mode="json")
    draft["status"] = "draft"
    draft["confirmed_at"] = None
    run(workflow_service.store_change_map(repo, USER, project, 1, draft))
    project = run(repo.get_project(USER))
    assert review_is_stale(project, 1, get_stored_review(project, 1)) is True
    assert review_service.review_board_view(project, 1)["stale"] is True

    reconfirmed = copy.deepcopy(draft)
    reconfirmed["status"] = "confirmed"
    reconfirmed["confirmed_at"] = "2026-07-13T11:00:00+00:00"
    project = run(repo.get_project(USER))
    run(workflow_service.store_change_map(repo, USER, project, 1, reconfirmed))
    project = run(repo.get_project(USER))
    assert review_service.review_board_view(project, 1)["stale"] is True

    regenerated = copy.deepcopy(reconfirmed)
    regenerated["generated_at"] = "2026-07-13T12:00:00+00:00"
    project = run(repo.get_project(USER))
    run(workflow_service.store_change_map(repo, USER, project, 1, regenerated))
    project = run(repo.get_project(USER))
    assert review_service.review_board_view(project, 1)["stale"] is True

    rebound = initialized(repo, replace=True)
    assert rebound["stale"] is False
    assert rebound["source_change_map_generated_at"] == regenerated["generated_at"]


def test_progress_and_m16b_handoff_helpers_are_review_specific_and_typed():
    repo, _ = seed_map()
    initialized(repo)
    review = get_stored_review(run(repo.get_project(USER)), 1)
    assert reviewed_target_count(review) == 0
    assert len(pending_review_targets(review)) == len(review.review_targets)
    assert review_complete(review) is False

    updates = []
    for index, target in enumerate(review.review_targets):
        updates.append({
            "review_target_id": target.review_target_id,
            "review_decision": "needs_verification" if index == 0 else "keep",
            "student_rationale": "Test the owner boundary." if index == 0 else None,
        })
    saved = run(save_section(repo, USER, 1, "review_board", {
        "target_updates": updates,
    }))["artifact"]
    review = get_stored_review(run(repo.get_project(USER)), 1)
    assert reviewed_target_count(review) == len(review.review_targets)
    assert pending_review_targets(review) == []
    assert review_complete(review) is True
    handoff = needs_verification_targets(review)
    assert len(handoff) == 1
    assert handoff[0].review_target_id == review.review_targets[0].review_target_id
    assert handoff[0].change_map_item_id == review.review_targets[0].change_map_item_id
    assert handoff[0].reviewed_text == review.review_targets[0].change_text
    assert handoff[0].student_rationale == "Test the owner boundary."


def test_owner_and_phase_isolation_and_workspace_errors():
    repo, _ = seed_map()
    with pytest.raises(WorkspaceNotReadyError):
        initialized(repo, user=OTHER_USER)
    with pytest.raises(PhaseNotFoundError):
        initialized(repo, phase=99)

    _, _ = seed_map(repo, phase=2, items=[ai_item(
        "cm-phase-two", "implementation_decision"
    )])
    phase1 = initialized(repo, phase=1)
    phase2 = initialized(repo, phase=2)
    assert phase1["source_change_map_generated_at"] != phase2["source_change_map_generated_at"]
    assert phase1["review_targets"][0]["change_map_item_id"] != "cm-phase-two"
    assert phase2["review_targets"][0]["change_map_item_id"] == "cm-phase-two"


def test_review_integration_imports_no_llm_and_accepts_no_provider():
    source = inspect.getsource(review_service)
    assert "llm_service" not in source
    assert not any("llm" in name.lower() for name in vars(review_service))
    assert "implementation_import" not in source


def test_linked_targets_do_not_enter_the_unchanged_defense_context():
    repo, _ = seed_map()
    artifact = initialized(repo)
    rendered = render_defense_context(run(build_defense_context(repo, USER, 1)))
    assert "review_targets" not in rendered
    assert "source_change_map_confirmed_at" not in rendered
    for target in artifact["review_targets"]:
        assert target["review_target_id"] not in rendered
        assert target["change_text"] not in rendered
