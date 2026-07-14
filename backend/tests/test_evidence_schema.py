"""M16B.3A linked Evidence schema and legacy-compatibility tests."""

import pytest
from pydantic import ValidationError

from app.schemas.workflow import (
    EvidenceArtifact,
    EvidenceFromVerificationRequest,
    EvidenceSaveRequest,
    EvidenceTargetUpdate,
    LinkedEvidenceTarget,
    StoredEvidenceArtifact,
)
from tests.test_workflow_service import EVIDENCE


BINDING = {
    "verification_initialized_at": "2026-07-14T10:00:00+00:00",
    "verification_review_binding_fingerprint": "a" * 64,
    "selected_target_fingerprint": "b" * 64,
}


def linked_target(**overrides):
    value = {
        "evidence_target_id": "ev-0123456789ab",
        "source_verification_target_id": "vt-0123456789ab",
        "source_review_target_id": "rv-0123456789ab",
        "source_change_map_item_id": "cm-source",
        "category": "behavior_change",
        "check_snapshot": "Run the saved behavior and record what happened.",
        "verification_result_snapshot": "pass",
        "verification_result_notes_snapshot": "The behavior matched.",
        "evidence_status": "not_addressed",
        "entries": [],
        "explanation": None,
        "unavailable_reason": None,
    }
    value.update(overrides)
    return value


def test_legacy_evidence_shape_remains_compatible():
    assert EvidenceArtifact.model_validate(EVIDENCE).model_dump(mode="json") == (
        EvidenceArtifact.model_validate(EVIDENCE).model_dump(mode="json")
    )
    stored = StoredEvidenceArtifact.model_validate({**EVIDENCE, "saved_at": "now"})
    assert stored.evidence_targets == []
    assert stored.source_verification_binding is None


def test_linked_binding_is_all_or_nothing_and_ids_are_unique():
    valid = StoredEvidenceArtifact.model_validate({
        "initialized_at": "now",
        "source_verification_binding": BINDING,
        "evidence_targets": [linked_target()],
    })
    assert valid.evidence_targets[0].evidence_status == "not_addressed"
    for invalid in (
        {"initialized_at": "now"},
        {"source_verification_binding": BINDING},
        {"evidence_targets": [linked_target()]},
    ):
        with pytest.raises(ValidationError):
            StoredEvidenceArtifact.model_validate(invalid)
    with pytest.raises(ValidationError, match="duplicate"):
        StoredEvidenceArtifact.model_validate({
            "initialized_at": "now",
            "source_verification_binding": BINDING,
            "evidence_targets": [linked_target(), linked_target()],
        })


def test_evidence_statuses_preserve_recorded_unavailable_and_unaddressed():
    recorded = LinkedEvidenceTarget.model_validate(linked_target(
        evidence_status="evidence_recorded",
        entries=[{"kind": "test_output", "content": "1 passed"}],
        explanation="  This is the observed test output.  ",
    ))
    assert recorded.explanation == "This is the observed test output."
    unavailable = LinkedEvidenceTarget.model_validate(linked_target(
        evidence_status="evidence_unavailable",
        unavailable_reason="  The hosted logs expired.  ",
    ))
    assert unavailable.unavailable_reason == "The hosted logs expired."
    for invalid in (
        linked_target(evidence_status="evidence_recorded"),
        linked_target(evidence_status="evidence_unavailable"),
        linked_target(
            evidence_status="evidence_unavailable",
            unavailable_reason="No screenshot.",
            entries=[{"kind": "note", "content": "contradiction"}],
        ),
        linked_target(
            entries=[{"kind": "note", "content": "not addressed yet"}]
        ),
    ):
        with pytest.raises(ValidationError):
            LinkedEvidenceTarget.model_validate(invalid)


def test_student_update_forbids_server_provenance_and_requires_a_change():
    update = EvidenceTargetUpdate.model_validate({
        "evidence_target_id": "ev-0123456789ab",
        "evidence_status": "evidence_unavailable",
        "unavailable_reason": "  Output was not retained.  ",
    })
    assert update.unavailable_reason == "Output was not retained."
    with pytest.raises(ValidationError, match="must change"):
        EvidenceTargetUpdate.model_validate({
            "evidence_target_id": "ev-0123456789ab"
        })
    for forged in (
        {"source_verification_binding": BINDING},
        {"initialized_at": "forged"},
        {"stale": False},
        {"evidence_record_complete": True},
        {"evidence_targets": []},
        {"target_updates": [{
            "evidence_target_id": "ev-0123456789ab",
            "source_verification_target_id": "vt-ffffffffffff",
        }]},
    ):
        with pytest.raises(ValidationError):
            EvidenceSaveRequest.model_validate(forged)


def test_selection_is_explicit_bounded_unique_and_well_formed():
    request = EvidenceFromVerificationRequest.model_validate({
        "selected_verification_target_ids": ["vt-0123456789ab"]
    })
    assert request.replace_existing is False
    for invalid in (
        {"selected_verification_target_ids": []},
        {"selected_verification_target_ids": ["vt-bad"]},
        {"selected_verification_target_ids": [
            "vt-0123456789ab", "vt-0123456789ab"
        ]},
        {"selected_verification_target_ids": [
            f"vt-{index:012x}" for index in range(21)
        ]},
    ):
        with pytest.raises(ValidationError):
            EvidenceFromVerificationRequest.model_validate(invalid)


def test_evidence_content_validates_urls_hashes_duplicates_controls_and_secrets():
    for invalid_entry in (
        {"kind": "note", "content": "   "},
        {"kind": "repo_url", "content": "ftp://example.com"},
        {"kind": "commit_hash", "content": "not-hex"},
        {"kind": "terminal_output", "content": "bad\x00output"},
        {"kind": "terminal_output", "content": "bad\u0085output"},
        {"kind": "terminal_output", "content": "sb_secret_fake_marker"},
    ):
        with pytest.raises(ValidationError):
            EvidenceArtifact.model_validate({"entries": [invalid_entry]})

    duplicate = linked_target(
        evidence_status="evidence_recorded",
        entries=[
            {"kind": "note", "content": "same"},
            {"kind": "note", "content": "same"},
        ],
    )
    with pytest.raises(ValidationError, match="duplicate"):
        LinkedEvidenceTarget.model_validate(duplicate)

    unicode_entry = "✅" * 8000
    assert len(EvidenceArtifact.model_validate({
        "entries": [{"kind": "test_output", "content": unicode_entry}]
    }).entries[0].content) == 8000
    with pytest.raises(ValidationError):
        EvidenceArtifact.model_validate({
            "entries": [{"kind": "test_output", "content": unicode_entry + "✅"}]
        })
