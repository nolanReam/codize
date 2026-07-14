"""M16B.1 deterministic Review -> Verification service tests."""

import copy
import inspect
import json

import pytest

from app.services import review_service, verification_service, workflow_service
from app.services.defense_context_service import build_defense_context, render_defense_context
from app.services.phase_service import PhaseNotFoundError, WorkspaceNotReadyError
from app.services.verification_service import (
    InvalidVerificationUpdateError,
    VerificationAlreadyExistsError,
    VerificationReviewIncompleteError,
    VerificationReviewMissingError,
    VerificationReviewNotLinkedError,
    VerificationReviewStaleError,
    VerificationSourceConflictError,
)
from app.services.workflow_service import InvalidArtifactError, save_section
from tests.fakes import InMemoryProjectRepository
from tests.test_phase_service import OTHER_USER, USER, run
from tests.test_review_service import IMPORT, initialized, seed_map
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, REVIEW_BOARD, VERIFICATION


def complete_review(repo, *, needs_categories=("behavior_change",), phase=1):
    project = run(repo.get_project(USER))
    existing = review_service.get_stored_review(project, phase)
    artifact = (
        review_service.review_board_view(project, phase)
        if existing is not None and review_service.initialized_from_change_map(existing)
        else initialized(repo, phase=phase)
    )
    updates = []
    for target in artifact["review_targets"]:
        needs = target["change_map_category"] in needs_categories
        updates.append({
            "review_target_id": target["review_target_id"],
            "review_decision": "needs_verification" if needs else "keep",
            "student_rationale": (
                f"I need to test {target['change_map_category']}." if needs else None
            ),
        })
    return run(save_section(repo, USER, phase, "review_board", {
        "target_updates": updates,
    }))["artifact"]


def seed_completed_review(*, needs_categories=("behavior_change",), items=None):
    repo, _ = seed_map(items=items)
    review = complete_review(repo, needs_categories=needs_categories)
    return repo, review


def create(repo, *, phase=1, replace=False, user=USER):
    return run(verification_service.create_from_review(
        repo, user, phase, replace_existing=replace
    ))["artifact"]


def stored(repo, phase=1):
    return verification_service.get_stored_verification(
        run(repo.get_project(USER)), phase
    )


def test_current_completed_review_initializes_grounded_deterministic_targets():
    categories = tuple(verification_service.SUGGESTION_TEMPLATES)
    repo, review = seed_completed_review(needs_categories=categories)
    first = create(repo)
    second = create(repo, replace=True)

    assert first["initialized_from_review"] is True
    assert first["stale"] is False
    assert [target["category"] for target in first["verification_targets"]] == list(categories)
    assert [
        {key: target[key] for key in (
            "verification_target_id", "review_target_id", "change_map_item_id",
            "category", "source_text", "source_rationale", "suggested_check",
        )}
        for target in first["verification_targets"]
    ] == [
        {key: target[key] for key in (
            "verification_target_id", "review_target_id", "change_map_item_id",
            "category", "source_text", "source_rationale", "suggested_check",
        )}
        for target in second["verification_targets"]
    ]

    by_review = {target["review_target_id"]: target for target in review["review_targets"]}
    for target in first["verification_targets"]:
        source = by_review[target["review_target_id"]]
        assert target["change_map_item_id"] == source["change_map_item_id"]
        assert target["source_text"] == source["change_text"]
        assert target["source_rationale"] == source["student_rationale"]
        assert target["source_text"] in target["suggested_check"]
        assert target["verification_target_id"].startswith("vt-")
        assert target["result"] is None
        assert target["student_check"] is None
        assert target["result_notes"] is None


@pytest.mark.parametrize(
    "category,required_phrase",
    [
        ("behavior_change", "note what you expected"),
        ("implementation_decision", "user-facing or system behavior"),
        ("out_of_scope_change", "intended project scope"),
        ("security_sensitive_area", "intended or authorized case"),
        ("unresolved_risk", "whether it occurs"),
        ("unverified_behavior", "what actually happened"),
    ],
)
def test_category_templates_are_bounded_actionable_and_honest(category, required_phrase):
    repo, _ = seed_completed_review(needs_categories=(category,))
    target = create(repo)["verification_targets"][0]
    suggestion = target["suggested_check"]
    assert required_phrase in suggestion
    assert len(suggestion) <= 1400
    lower = suggestion.lower()
    without_source = lower.replace(target["source_text"].lower(), "")
    assert "is verified" not in without_source
    assert "guaranteed" not in lower
    assert "successfully" not in lower
    assert "browser automation" not in lower
    if category == "security_sensitive_area":
        assert "vulnerability exists" not in lower
        assert "exploit" not in lower


@pytest.mark.parametrize("excluded", ["pending", "keep", "revise", "remove", "uncertain"])
def test_only_needs_verification_decisions_are_included(excluded):
    repo, _ = seed_map()
    artifact = initialized(repo)
    updates = []
    for index, target in enumerate(artifact["review_targets"]):
        decision = "needs_verification" if index == 0 else excluded
        update = {
            "review_target_id": target["review_target_id"],
            "review_decision": decision,
        }
        if decision == "revise":
            update["student_revision"] = "Use a narrower implementation."
        updates.append(update)
    run(save_section(repo, USER, 1, "review_board", {"target_updates": updates}))
    review = review_service.get_stored_review(run(repo.get_project(USER)), 1)
    derived = verification_service.derive_verification_targets(review)
    assert len(derived) == 1
    assert derived[0].review_target_id == artifact["review_targets"][0]["review_target_id"]
    if excluded == "pending":
        with pytest.raises(VerificationReviewIncompleteError):
            create(repo)


def test_zero_needs_targets_creates_empty_unperformed_artifact():
    repo, _ = seed_completed_review(needs_categories=())
    artifact = create(repo)
    assert artifact["verification_targets"] == []
    assert artifact["checks"] == []
    assert artifact["explanation"] is None
    assert artifact["initialized_from_review"] is True
    assert artifact["stale"] is False


def test_source_binding_uses_review_metadata_and_identity_not_raw_text():
    repo, review = seed_completed_review()
    artifact = create(repo)
    binding = artifact["source_review_binding"]
    assert binding["source_change_map_generated_at"] == review["source_change_map_generated_at"]
    assert binding["source_change_map_confirmed_at"] == review["source_change_map_confirmed_at"]
    assert binding["review_saved_at"] == review["saved_at"]
    assert len(binding["review_target_fingerprint"]) == 64
    serialized_binding = json.dumps(binding)
    assert all(target["change_text"] not in serialized_binding for target in review["review_targets"])


def test_raw_import_change_map_excerpts_and_complete_review_are_not_copied():
    repo, review = seed_completed_review()
    artifact = create(repo)
    serialized = json.dumps(artifact)
    assert IMPORT["content"] not in serialized
    assert "source_references" not in serialized
    assert "supporting_excerpt" not in serialized
    assert "review_targets" not in serialized
    for source in review["review_targets"]:
        if source["review_decision"] != "needs_verification":
            assert source["change_text"] not in serialized


def test_missing_manual_incomplete_stale_corrupt_review_fail_safely():
    repo, _ = seed_map()
    with pytest.raises(VerificationReviewMissingError, match="Complete Review"):
        create(repo)

    run(save_section(repo, USER, 1, "review_board", REVIEW_BOARD))
    with pytest.raises(VerificationReviewNotLinkedError, match="current Change Map"):
        create(repo)

    initialized(repo, replace=True)
    with pytest.raises(VerificationReviewIncompleteError, match="Finish and save"):
        create(repo)

    complete_review(repo)
    run(save_section(repo, USER, 1, "implementation_import", {
        **IMPORT, "student_summary": "New import makes the source map stale."
    }))
    with pytest.raises(VerificationReviewStaleError, match="Rebuild Review"):
        create(repo)

    project = run(repo.get_project(USER))
    artifacts = copy.deepcopy(project["workflow_artifacts"])
    artifacts["1"]["review_board"] = {"review_targets": "corrupt"}
    run(repo.update_project(USER, project["id"], {"workflow_artifacts": artifacts}))
    with pytest.raises(VerificationReviewMissingError, match="Complete Review"):
        create(repo)


def test_existing_manual_and_linked_verification_require_explicit_replacement():
    repo, _ = seed_completed_review()
    run(save_section(repo, USER, 1, "verification", VERIFICATION))
    with pytest.raises(VerificationAlreadyExistsError, match="already exists"):
        create(repo)
    replaced = create(repo, replace=True)
    assert replaced["checks"] == []
    assert all(target["result"] is None for target in replaced["verification_targets"])
    with pytest.raises(VerificationAlreadyExistsError, match="already exists"):
        create(repo)
    assert create(repo, replace=True)["stale"] is False


def test_initialization_preserves_siblings_and_touches_only_workflow_artifacts():
    repo, _ = seed_completed_review()
    for section, payload in (
        ("prompt_builder", PROMPT_BUILDER),
        ("evidence", EVIDENCE),
    ):
        run(save_section(repo, USER, 1, section, payload))
    before = copy.deepcopy(run(repo.get_project(USER)))
    create(repo)
    after = run(repo.get_project(USER))
    changed = {key for key in after if before[key] != after[key]}
    assert changed == {"workflow_artifacts"}
    for key in ("prompt_builder", "evidence", "review_board", "change_map", "implementation_import"):
        assert after["workflow_artifacts"]["1"][key] == before["workflow_artifacts"]["1"][key]


def test_legacy_save_and_linked_student_updates_preserve_server_fields():
    repo, _ = seed_completed_review()
    before = create(repo)
    target = before["verification_targets"][0]

    saved = run(save_section(repo, USER, 1, "verification", {
        **VERIFICATION,
        "target_updates": [{
            "verification_target_id": target["verification_target_id"],
            "student_check": "Run the normal and restricted cases.",
            "result": "fail",
            "result_notes": "The restricted case was allowed.",
        }],
    }))["artifact"]
    assert saved["checks"] == verification_service.VerificationArtifact.model_validate(
        VERIFICATION
    ).model_dump(mode="json")["checks"]
    updated = saved["verification_targets"][0]
    assert updated["student_check"] == "Run the normal and restricted cases."
    assert updated["result"] == "fail"
    assert updated["result_notes"] == "The restricted case was allowed."
    for key in ("source_review_binding", "initialized_at"):
        assert saved[key] == before[key]
    for key in (
        "verification_target_id", "review_target_id", "change_map_item_id",
        "category", "source_text", "source_rationale", "suggested_check",
    ):
        assert updated[key] == target[key]


def test_target_only_update_preserves_existing_legacy_fields_on_linked_artifact():
    repo, _ = seed_completed_review()
    created = create(repo)
    target_id = created["verification_targets"][0]["verification_target_id"]
    manual = run(save_section(repo, USER, 1, "verification", VERIFICATION))["artifact"]

    updated = run(save_section(repo, USER, 1, "verification", {
        "target_updates": [{
            "verification_target_id": target_id,
            "result": "fail",
            "result_notes": "The observed behavior did not match.",
        }],
    }))["artifact"]

    assert updated["checks"] == manual["checks"]
    assert updated["explanation"] == manual["explanation"]
    assert updated["verification_targets"][0]["result"] == "fail"

    # Explicit legacy fields retain the old full-section replacement contract.
    cleared = run(save_section(repo, USER, 1, "verification", {
        "checks": [],
    }))["artifact"]
    assert cleared["checks"] == []
    assert cleared["explanation"] is None
    assert cleared["verification_targets"][0]["result"] == "fail"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_review_binding", {}),
        ("initialized_at", "forged"),
        ("verification_targets", []),
        ("stale", False),
        ("initialized_from_review", True),
    ],
)
def test_generic_put_rejects_top_level_provenance_forgery(field, value):
    repo, _ = seed_completed_review()
    create(repo)
    with pytest.raises(InvalidArtifactError):
        run(save_section(repo, USER, 1, "verification", {field: value}))


def test_unknown_duplicate_and_manual_target_updates_are_rejected():
    repo, _ = seed_completed_review()
    artifact = create(repo)
    target_id = artifact["verification_targets"][0]["verification_target_id"]
    with pytest.raises(InvalidArtifactError, match="does not match"):
        run(save_section(repo, USER, 1, "verification", {
            "target_updates": [{
                "verification_target_id": "vt-000000000000",
                "result": "pass",
            }]
        }))
    with pytest.raises(InvalidArtifactError, match="same target"):
        run(save_section(repo, USER, 1, "verification", {
            "target_updates": [
                {"verification_target_id": target_id, "result": "pass"},
                {"verification_target_id": target_id, "result": "fail"},
            ]
        }))

    repo2, _ = seed_map()
    run(save_section(repo2, USER, 1, "verification", VERIFICATION))
    with pytest.raises(InvalidArtifactError, match="initialized from Review"):
        run(save_section(repo2, USER, 1, "verification", {
            "target_updates": [{
                "verification_target_id": target_id,
                "result": "pass",
            }]
        }))


def test_staleness_detects_review_changes_rebuilds_source_changes_and_identity_changes():
    repo, _ = seed_completed_review()
    artifact = create(repo)
    assert artifact["stale"] is False

    review = review_service.get_stored_review(run(repo.get_project(USER)), 1)
    target = review.review_targets[0]
    run(save_section(repo, USER, 1, "review_board", {
        "target_updates": [{
            "review_target_id": target.review_target_id,
            "review_decision": "keep",
        }]
    }))
    assert verification_service.verification_view(run(repo.get_project(USER)), 1)["stale"] is True

    # Explicit replacement rebinds only to the current complete Review.
    rebound = create(repo, replace=True)
    assert rebound["stale"] is False

    initialized(repo, replace=True)  # Review rebuild resets decisions to pending.
    assert verification_service.verification_view(run(repo.get_project(USER)), 1)["stale"] is True

    complete_review(repo)
    rebound = create(repo, replace=True)
    assert rebound["stale"] is False
    run(save_section(repo, USER, 1, "implementation_import", {
        **IMPORT, "student_summary": "Changed source binding."
    }))
    assert verification_service.verification_view(run(repo.get_project(USER)), 1)["stale"] is True


def test_stale_verification_remains_readable_and_client_cannot_clear_it():
    repo, _ = seed_completed_review()
    created = create(repo)
    target_id = created["verification_targets"][0]["verification_target_id"]
    review = review_service.get_stored_review(run(repo.get_project(USER)), 1)
    run(save_section(repo, USER, 1, "review_board", {
        "target_updates": [{
            "review_target_id": review.review_targets[0].review_target_id,
            "review_decision": "keep",
        }]
    }))
    view = verification_service.verification_view(run(repo.get_project(USER)), 1)
    assert view["stale"] is True
    assert view["verification_targets"][0]["verification_target_id"] == target_id
    with pytest.raises(InvalidArtifactError):
        run(save_section(repo, USER, 1, "verification", {"stale": False}))


@pytest.mark.parametrize("mutation", ["missing", "corrupt", "removed", "identity"])
def test_missing_corrupt_removed_or_reidentified_review_source_makes_verification_stale(mutation):
    repo, _ = seed_completed_review()
    artifact = create(repo)
    project = run(repo.get_project(USER))
    artifacts = copy.deepcopy(project["workflow_artifacts"])
    review = artifacts["1"]["review_board"]
    if mutation == "missing":
        del artifacts["1"]["review_board"]
    elif mutation == "corrupt":
        artifacts["1"]["review_board"] = {"review_targets": "corrupt"}
    elif mutation == "removed":
        review["review_targets"] = review["review_targets"][1:]
        review["saved_at"] = "2026-07-13T09:00:00+00:00"
    else:
        review["review_targets"][0]["review_target_id"] = "rv-ffffffffffff"
        review["saved_at"] = "2026-07-13T09:00:00+00:00"
    run(repo.update_project(USER, project["id"], {"workflow_artifacts": artifacts}))
    view = verification_service.verification_view(run(repo.get_project(USER)), 1)
    assert view["stale"] is True
    assert view["verification_targets"] == artifact["verification_targets"]


def test_helpers_preserve_result_honesty_and_future_evidence_shape_without_creating_evidence():
    repo, _ = seed_completed_review(needs_categories=(
        "behavior_change", "implementation_decision", "unresolved_risk"
    ))
    artifact = create(repo)
    updates = [
        {"verification_target_id": artifact["verification_targets"][0]["verification_target_id"], "result": "pass"},
        {"verification_target_id": artifact["verification_targets"][1]["verification_target_id"], "result": "fail", "result_notes": "Mismatch"},
        {"verification_target_id": artifact["verification_targets"][2]["verification_target_id"], "result": "skipped"},
    ]
    run(save_section(repo, USER, 1, "verification", {"target_updates": updates}))
    verification = stored(repo)
    assert [target.result for target in verification_service.completed_targets(verification)] == ["pass", "fail"]
    assert [target.result for target in verification_service.failed_targets(verification)] == ["fail"]
    assert verification_service.pending_targets(verification) == []
    assert [target.result for target in verification_service.unresolved_targets(verification)] == ["fail", "skipped"]
    handoff = verification_service.evidence_handoff_targets(verification)
    assert handoff[1].review_target_id == verification.verification_targets[1].review_target_id
    assert handoff[1].result == "fail"
    assert handoff[1].result_notes == "Mismatch"
    project = run(repo.get_project(USER))
    assert project["workflow_artifacts"]["1"].get("evidence") is None


def test_linked_source_and_suggestions_do_not_enter_defense_context():
    repo, _ = seed_completed_review()
    artifact = create(repo)
    rendered = render_defense_context(run(build_defense_context(repo, USER, 1)))
    target = artifact["verification_targets"][0]
    assert target["source_text"] not in rendered
    assert target["source_rationale"] not in rendered
    assert target["suggested_check"] not in rendered
    assert target["verification_target_id"] not in rendered


def test_collision_is_detected_without_persisting(monkeypatch):
    repo, _ = seed_completed_review(needs_categories=(
        "behavior_change", "implementation_decision"
    ))
    monkeypatch.setattr(
        verification_service, "_verification_target_id", lambda _source: "vt-000000000000"
    )
    before = copy.deepcopy(run(repo.get_project(USER))["workflow_artifacts"])
    with pytest.raises(VerificationSourceConflictError):
        create(repo)
    assert run(repo.get_project(USER))["workflow_artifacts"] == before


def test_ownership_phase_isolation_and_workspace_errors():
    repo, _ = seed_completed_review()
    with pytest.raises(WorkspaceNotReadyError):
        create(repo, user=OTHER_USER)
    with pytest.raises(PhaseNotFoundError):
        create(repo, phase=99)
    mine = create(repo)
    assert mine["verification_targets"]
    assert verification_service.verification_view(run(repo.get_project(USER)), 2) is None


def test_no_provider_prompt_execution_evidence_or_defense_imports():
    source = inspect.getsource(verification_service)
    assert "llm_service" not in source
    assert "Gemini" not in source
    assert "OpenRouter" not in source
    assert "StubProvider" not in source
    assert "prompt" not in {
        name.lower() for name in vars(verification_service)
    }
    assert "defense_context" not in source
    assert "gate_service" not in source
