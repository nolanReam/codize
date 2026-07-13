"""M16A.1 linked Review schema compatibility and decision rules."""

import pytest
from pydantic import ValidationError

from app.schemas.workflow import (
    ReviewBoardArtifact,
    ReviewBoardSaveRequest,
    ReviewTarget,
    ReviewTargetUpdate,
    StoredReviewBoardArtifact,
)
from tests.test_workflow_service import REVIEW_BOARD


def target(**overrides):
    data = {
        "review_target_id": "rv-0123456789ab",
        "change_map_item_id": "cm-0123456789ab",
        "change_map_category": "implementation_decision",
        "change_map_origin": "ai_inferred",
        "change_map_student_decision": "confirmed",
        "change_text": "The route now filters task reads by owner.",
        "source_resolution": "confirmed",
        "review_decision": "pending",
        "student_rationale": None,
        "student_revision": None,
    }
    data.update(overrides)
    return data


def test_legacy_review_artifact_and_current_frontend_payload_still_validate():
    legacy = ReviewBoardArtifact.model_validate(REVIEW_BOARD)
    assert legacy.model_dump(mode="json") == REVIEW_BOARD
    stored = StoredReviewBoardArtifact.model_validate({**REVIEW_BOARD, "saved_at": "now"})
    assert stored.review_targets == []
    assert stored.source_change_map_confirmed_at is None


@pytest.mark.parametrize(
    ("decision", "extra"),
    [
        ("pending", {}),
        ("keep", {}),
        ("revise", {"student_revision": "Use an ownership-filtered query."}),
        ("remove", {}),
        ("needs_verification", {}),
        ("uncertain", {}),
    ],
)
def test_all_review_decisions_validate(decision, extra):
    assert ReviewTarget.model_validate(
        target(review_decision=decision, **extra)
    ).review_decision == decision


def test_revise_requires_rationale_or_proposed_revision():
    with pytest.raises(ValidationError, match="rationale or proposed revision"):
        ReviewTarget.model_validate(target(review_decision="revise"))
    with pytest.raises(ValidationError, match="rationale or proposed revision"):
        ReviewTargetUpdate.model_validate({
            "review_target_id": "rv-0123456789ab",
            "review_decision": "revise",
        })
    update = ReviewTargetUpdate.model_validate({
        "review_target_id": "rv-0123456789ab",
        "review_decision": "revise",
        "student_rationale": "  The fallback is too broad.  ",
    })
    assert update.student_rationale == "The fallback is too broad."


def test_unknown_decision_and_malformed_target_id_are_rejected():
    with pytest.raises(ValidationError):
        ReviewTarget.model_validate(target(review_decision="approved"))
    with pytest.raises(ValidationError):
        ReviewTarget.model_validate(target(review_target_id="client-choice"))


def test_linked_review_requires_complete_binding_and_unique_targets():
    with pytest.raises(ValidationError, match="both Change Map timestamps"):
        StoredReviewBoardArtifact.model_validate({
            "source_change_map_confirmed_at": "2026-07-13T10:00:00Z",
        })
    with pytest.raises(ValidationError, match="duplicate review target ids"):
        StoredReviewBoardArtifact.model_validate({
            "source_change_map_confirmed_at": "2026-07-13T10:00:00Z",
            "source_change_map_generated_at": "2026-07-13T09:00:00Z",
            "review_targets": [target(), target(change_map_item_id="cm-other")],
        })


@pytest.mark.parametrize(
    "field",
    [
        "source_change_map_confirmed_at",
        "source_change_map_generated_at",
        "review_targets",
        "stale",
        "initialized_from_change_map",
    ],
)
def test_student_save_contract_forbids_server_owned_link_fields(field):
    with pytest.raises(ValidationError):
        ReviewBoardSaveRequest.model_validate({field: False if field == "stale" else "forged"})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("change_map_item_id", "cm-forged"),
        ("change_map_category", "behavior_change"),
        ("change_map_origin", "student_added"),
        ("change_map_student_decision", "confirmed"),
        ("change_text", "Forged source snapshot"),
        ("source_resolution", "confirmed"),
    ],
)
def test_target_updates_forbid_every_server_owned_source_field(field, value):
    with pytest.raises(ValidationError):
        ReviewBoardSaveRequest.model_validate({
            "target_updates": [{
                "review_target_id": "rv-0123456789ab",
                "review_decision": "keep",
                field: value,
            }],
        })
