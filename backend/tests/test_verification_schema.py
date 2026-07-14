"""M16B.1 linked Verification schema and legacy-compatibility tests."""

import pytest
from pydantic import ValidationError

from app.schemas.workflow import (
    LinkedVerificationTarget,
    StoredVerificationArtifact,
    VerificationArtifact,
    VerificationReviewBinding,
    VerificationSaveRequest,
    VerificationTargetUpdate,
)
from tests.test_workflow_service import VERIFICATION


BINDING = {
    "source_change_map_generated_at": "2026-07-13T01:00:00+00:00",
    "source_change_map_confirmed_at": "2026-07-13T01:30:00+00:00",
    "review_saved_at": "2026-07-13T02:00:00+00:00",
    "review_target_fingerprint": "a" * 64,
}


def linked_target(**overrides):
    value = {
        "verification_target_id": "vt-0123456789ab",
        "review_target_id": "rv-0123456789ab",
        "change_map_item_id": "cm-source",
        "category": "behavior_change",
        "source_text": "Tasks are filtered to the signed-in owner.",
        "source_rationale": "I need to test the owner boundary.",
        "suggested_check": "Perform the reviewed behavior and record what happened.",
        "student_check": None,
        "result": None,
        "result_notes": None,
    }
    value.update(overrides)
    return value


def test_legacy_verification_contract_is_byte_compatible():
    legacy = VerificationArtifact.model_validate(VERIFICATION)
    assert legacy.model_dump(mode="json") == VerificationArtifact.model_validate(
        VERIFICATION
    ).model_dump(mode="json")
    stored = StoredVerificationArtifact.model_validate({**VERIFICATION, "saved_at": "now"})
    assert stored.verification_targets == []
    assert stored.source_review_binding is None


def test_linked_target_starts_unperformed_and_uses_existing_result_values_only():
    target = LinkedVerificationTarget.model_validate(linked_target())
    assert target.result is None
    for result in ("pass", "fail", "skipped", "not_applicable"):
        assert LinkedVerificationTarget.model_validate(
            linked_target(result=result)
        ).result == result
    for invalid in ("pending", "verified", "approved"):
        with pytest.raises(ValidationError):
            LinkedVerificationTarget.model_validate(linked_target(result=invalid))


def test_linked_binding_allows_intentional_zero_targets_without_completion_claim():
    artifact = StoredVerificationArtifact.model_validate({
        "checks": [],
        "initialized_at": "2026-07-13T02:01:00+00:00",
        "source_review_binding": BINDING,
        "verification_targets": [],
    })
    assert artifact.verification_targets == []
    assert artifact.checks == []


@pytest.mark.parametrize(
    "value",
    [
        {"initialized_at": "now"},
        {"source_review_binding": BINDING},
        {"verification_targets": [linked_target()]},
    ],
)
def test_linked_binding_is_all_or_nothing(value):
    with pytest.raises(ValidationError):
        StoredVerificationArtifact.model_validate(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("review_target_id", "rv-ffffffffffff"),
        ("change_map_item_id", "cm-forged"),
        ("category", "unresolved_risk"),
        ("source_text", "Forged source"),
        ("source_rationale", "Forged rationale"),
        ("suggested_check", "Forged suggestion"),
        ("source_review_binding", BINDING),
        ("initialized_at", "now"),
        ("stale", False),
    ],
)
def test_save_request_forbids_server_owned_fields(field, value):
    body = {"target_updates": [{
        "verification_target_id": "vt-0123456789ab",
        "student_check": "Use the proposed check.",
    }]}
    if field in {"source_review_binding", "initialized_at", "stale"}:
        body[field] = value
    else:
        body["target_updates"][0][field] = value
    with pytest.raises(ValidationError):
        VerificationSaveRequest.model_validate(body)


def test_student_update_is_partial_normalized_and_requires_a_change():
    update = VerificationTargetUpdate.model_validate({
        "verification_target_id": "vt-0123456789ab",
        "student_check": "  Try the normal flow.  ",
        "result_notes": "  observed the response  ",
    })
    assert update.student_check == "Try the normal flow."
    assert update.result_notes == "observed the response"
    with pytest.raises(ValidationError, match="must change"):
        VerificationTargetUpdate.model_validate({
            "verification_target_id": "vt-0123456789ab"
        })


def test_duplicate_linked_identity_is_rejected():
    base = {
        "initialized_at": "now",
        "source_review_binding": VerificationReviewBinding.model_validate(BINDING),
    }
    for changed in (
        {"verification_target_id": "vt-0123456789ab", "review_target_id": "rv-bbbbbbbbbbbb", "change_map_item_id": "cm-two"},
        {"verification_target_id": "vt-bbbbbbbbbbbb", "review_target_id": "rv-0123456789ab", "change_map_item_id": "cm-two"},
        {"verification_target_id": "vt-bbbbbbbbbbbb", "review_target_id": "rv-bbbbbbbbbbbb", "change_map_item_id": "cm-source"},
    ):
        with pytest.raises(ValidationError, match="duplicate"):
            StoredVerificationArtifact.model_validate({
                **base,
                "verification_targets": [linked_target(), linked_target(**changed)],
            })
