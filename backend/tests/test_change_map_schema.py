"""Change Map schema tests (M15C.1): strict enums, origin/decision/uncertainty
separation, consistency rules, limits, unknown-field rejection, and the
student-update contract. All secrets below are fake fixtures.
"""

import pytest
from pydantic import ValidationError

from app.schemas.change_map import (
    CHANGE_MAP_MAX_DRAFT_TEXT,
    CHANGE_MAP_MAX_EXCERPT,
    CHANGE_MAP_MAX_ITEMS,
    CHANGE_MAP_MAX_REFERENCES,
    CHANGE_MAP_MAX_STUDENT_ITEMS,
    CHANGE_MAP_MAX_UNCERTAINTY_REASON,
    CHANGE_MAP_SCHEMA_VERSION,
    ChangeMapGenerateRequest,
    ChangeMapItem,
    ChangeMapItemUpdate,
    ChangeMapSourceReference,
    ChangeMapUpdateRequest,
    GeneratedChangeMap,
    GeneratedChangeMapItem,
    StoredChangeMap,
    StudentAddedItemRequest,
)

REF = {
    "source_field": "content",
    "source_kind": "git_diff",
    "file_path": None,
    "supporting_excerpt": "query = query.eq(\"user_id\", user.id)",
}

GEN_ITEM = {
    "category": "behavior_change",
    "draft_text": "Tasks now appear to be filtered by owner.",
    "ai_uncertainty": "supported",
    "uncertainty_reason": None,
    "source_references": [REF],
}


def stored_item(**overrides):
    base = {
        "item_id": "cm-000000000001",
        "origin": "ai_inferred",
        "category": "behavior_change",
        "draft_text": "Tasks now appear to be filtered by owner.",
        "ai_uncertainty": "supported",
        "uncertainty_reason": None,
        "source_references": [REF],
        "student_decision": "pending_review",
        "student_text": None,
        "student_note": None,
    }
    base.update(overrides)
    return base


def stored_map(**overrides):
    base = {
        "schema_version": CHANGE_MAP_SCHEMA_VERSION,
        "status": "draft",
        "source_import_saved_at": "2026-07-13T00:00:00+00:00",
        "generated_at": "2026-07-13T00:01:00+00:00",
        "confirmed_at": None,
        "source_redacted": False,
        "source_truncated": False,
        "items": [stored_item()],
    }
    base.update(overrides)
    return base


# --- enums --------------------------------------------------------------------


@pytest.mark.parametrize("category", [
    "changed_file", "behavior_change", "implementation_decision",
    "out_of_scope_change", "security_sensitive_area", "unresolved_risk",
    "unverified_behavior", "question_to_understand",
])
def test_every_category_is_accepted(category):
    item = GeneratedChangeMapItem.model_validate({**GEN_ITEM, "category": category})
    assert item.category == category


def test_unknown_category_rejected():
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate({**GEN_ITEM, "category": "vulnerability"})


@pytest.mark.parametrize("uncertainty", ["supported", "ambiguous", "needs_inspection"])
def test_every_uncertainty_state_is_accepted(uncertainty):
    item = GeneratedChangeMapItem.model_validate({**GEN_ITEM, "ai_uncertainty": uncertainty})
    assert item.ai_uncertainty == uncertainty


def test_numeric_confidence_is_not_a_thing():
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate({**GEN_ITEM, "ai_uncertainty": "87%"})
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate({**GEN_ITEM, "confidence": 0.87})


@pytest.mark.parametrize("decision", [
    "pending_review", "confirmed", "edited", "rejected", "uncertain", "needs_inspection",
])
def test_every_student_decision_is_accepted_on_ai_items(decision):
    text = "My own wording." if decision == "edited" else None
    item = ChangeMapItem.model_validate(
        stored_item(student_decision=decision, student_text=text)
    )
    assert item.student_decision == decision


@pytest.mark.parametrize("origin", ["ai_inferred", "student_added"])
def test_every_origin_is_accepted(origin):
    if origin == "ai_inferred":
        item = ChangeMapItem.model_validate(stored_item())
    else:
        item = ChangeMapItem.model_validate(stored_item(
            item_id="sa-000000000001", origin="student_added", draft_text=None,
            ai_uncertainty=None, source_references=[],
            student_decision="confirmed", student_text="I also renamed the config module.",
        ))
    assert item.origin == origin


# --- model output contract ------------------------------------------------------


def test_model_cannot_set_server_owned_fields():
    for extra in ("item_id", "origin", "student_decision", "student_text",
                  "generated_at", "confirmed_at", "status"):
        with pytest.raises(ValidationError):
            GeneratedChangeMapItem.model_validate({**GEN_ITEM, extra: "x"})


def test_generated_item_requires_at_least_one_reference():
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate({**GEN_ITEM, "source_references": []})


def test_generated_map_rejects_empty_and_oversized_item_lists():
    with pytest.raises(ValidationError):
        GeneratedChangeMap.model_validate({"items": []})
    too_many = [
        {**GEN_ITEM, "draft_text": f"Item {i} appears changed."}
        for i in range(CHANGE_MAP_MAX_ITEMS + 1)
    ]
    with pytest.raises(ValidationError):
        GeneratedChangeMap.model_validate({"items": too_many})


def test_field_length_limits_enforced():
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate(
            {**GEN_ITEM, "draft_text": "x" * (CHANGE_MAP_MAX_DRAFT_TEXT + 1)})
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate(
            {**GEN_ITEM, "uncertainty_reason": "x" * (CHANGE_MAP_MAX_UNCERTAINTY_REASON + 1)})
    with pytest.raises(ValidationError):
        ChangeMapSourceReference.model_validate(
            {**REF, "supporting_excerpt": "x" * (CHANGE_MAP_MAX_EXCERPT + 1)})
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate(
            {**GEN_ITEM, "source_references": [REF] * (CHANGE_MAP_MAX_REFERENCES + 1)})


def test_reference_needs_excerpt_unless_changed_file_entry():
    with pytest.raises(ValidationError):
        ChangeMapSourceReference.model_validate(
            {"source_field": "content", "source_kind": "git_diff",
             "file_path": None, "supporting_excerpt": None})
    ref = ChangeMapSourceReference.model_validate(
        {"source_field": "changed_files", "source_kind": "changed_files",
         "file_path": "app/models.py", "supporting_excerpt": None})
    assert ref.file_path == "app/models.py"


def test_secret_marker_in_generated_text_is_rejected():
    with pytest.raises(ValidationError):
        GeneratedChangeMapItem.model_validate(
            {**GEN_ITEM, "draft_text": "Uses key sb_secret_fakefake123 now."})


# --- origin / decision consistency ---------------------------------------------


def test_ai_item_requires_draft_text_uncertainty_and_references():
    for missing in (
        {"draft_text": None},
        {"ai_uncertainty": None},
        {"source_references": []},
    ):
        with pytest.raises(ValidationError):
            ChangeMapItem.model_validate(stored_item(**missing))


def test_student_added_item_carries_no_ai_fields():
    base = stored_item(
        item_id="sa-1", origin="student_added", draft_text=None,
        ai_uncertainty=None, source_references=[],
        student_decision="confirmed", student_text="I refactored the login form.",
    )
    assert ChangeMapItem.model_validate(base).origin == "student_added"
    for bad in (
        {"draft_text": "AI wording"},
        {"ai_uncertainty": "supported"},
        {"uncertainty_reason": "reason"},
        {"source_references": [REF]},
    ):
        with pytest.raises(ValidationError):
            ChangeMapItem.model_validate({**base, **bad})


def test_student_added_item_requires_text_and_honest_decision():
    base = stored_item(
        item_id="sa-1", origin="student_added", draft_text=None,
        ai_uncertainty=None, source_references=[], student_decision="confirmed",
        student_text="I refactored the login form.",
    )
    with pytest.raises(ValidationError):
        ChangeMapItem.model_validate({**base, "student_text": None})
    for decision in ("pending_review", "edited", "rejected"):
        with pytest.raises(ValidationError):
            ChangeMapItem.model_validate({**base, "student_decision": decision})
    for decision in ("confirmed", "uncertain", "needs_inspection"):
        assert ChangeMapItem.model_validate(
            {**base, "student_decision": decision}).student_decision == decision


def test_edited_item_requires_student_text():
    with pytest.raises(ValidationError):
        ChangeMapItem.model_validate(stored_item(student_decision="edited"))
    item = ChangeMapItem.model_validate(
        stored_item(student_decision="edited",
                    student_text="Session validation was added to the middleware."))
    assert item.student_text.startswith("Session validation")


# --- stored map integrity --------------------------------------------------------


def test_stored_map_round_trips():
    m = StoredChangeMap.model_validate(stored_map())
    assert m.status == "draft"
    assert m.items[0].student_decision == "pending_review"


def test_stored_map_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        StoredChangeMap.model_validate(stored_map(items=[stored_item(), stored_item()]))


def test_confirmed_map_needs_timestamp_and_no_pending_items():
    with pytest.raises(ValidationError):
        StoredChangeMap.model_validate(stored_map(status="confirmed"))
    with pytest.raises(ValidationError):
        StoredChangeMap.model_validate(
            stored_map(status="confirmed", confirmed_at="2026-07-13T01:00:00+00:00"))
    ok = StoredChangeMap.model_validate(stored_map(
        status="confirmed", confirmed_at="2026-07-13T01:00:00+00:00",
        items=[stored_item(student_decision="uncertain")],
    ))
    assert ok.status == "confirmed"


def test_draft_map_cannot_carry_confirmed_at():
    with pytest.raises(ValidationError):
        StoredChangeMap.model_validate(stored_map(confirmed_at="2026-07-13T01:00:00+00:00"))


def test_unknown_fields_rejected_everywhere():
    with pytest.raises(ValidationError):
        StoredChangeMap.model_validate(stored_map(surprise=True))
    with pytest.raises(ValidationError):
        ChangeMapItem.model_validate(stored_item(surprise=True))
    with pytest.raises(ValidationError):
        ChangeMapSourceReference.model_validate({**REF, "line_number": 12})


# --- student update contract -----------------------------------------------------


def test_update_request_accepts_decisions_and_added_items():
    req = ChangeMapUpdateRequest.model_validate({
        "updates": [
            {"item_id": "cm-1", "student_decision": "confirmed"},
            {"item_id": "cm-2", "student_decision": "edited",
             "student_text": "My corrected wording.", "student_note": "Checked the diff."},
            {"item_id": "cm-3", "student_decision": "rejected"},
            {"item_id": "cm-4", "student_decision": "uncertain"},
            {"item_id": "cm-5", "student_decision": "needs_inspection"},
        ],
        "student_added_items": [
            {"category": "implementation_decision",
             "student_text": "I chose to keep the old route alongside the new one."},
        ],
    })
    assert len(req.updates) == 5
    assert req.student_added_items[0].student_decision == "confirmed"  # default


def test_update_cannot_touch_server_owned_fields():
    for extra in ("draft_text", "ai_uncertainty", "uncertainty_reason",
                  "source_references", "origin", "generated_at",
                  "source_import_saved_at", "status", "confirmed_at",
                  "source_redacted", "source_truncated"):
        with pytest.raises(ValidationError):
            ChangeMapItemUpdate.model_validate(
                {"item_id": "cm-1", "student_decision": "confirmed", extra: "x"})
        with pytest.raises(ValidationError):
            ChangeMapUpdateRequest.model_validate({"updates": [], extra: "x"})


def test_update_text_rules():
    # edited requires text; non-edited decisions must not smuggle text in.
    with pytest.raises(ValidationError):
        ChangeMapItemUpdate.model_validate({"item_id": "cm-1", "student_decision": "edited"})
    with pytest.raises(ValidationError):
        ChangeMapItemUpdate.model_validate(
            {"item_id": "cm-1", "student_decision": "confirmed", "student_text": "sneaky"})


def test_student_added_request_rules():
    with pytest.raises(ValidationError):
        StudentAddedItemRequest.model_validate(
            {"category": "behavior_change", "student_text": ""})
    with pytest.raises(ValidationError):
        StudentAddedItemRequest.model_validate(
            {"category": "behavior_change", "student_text": "x",
             "student_decision": "pending_review"})
    with pytest.raises(ValidationError):
        StudentAddedItemRequest.model_validate(
            {"category": "behavior_change", "student_text": "x", "origin": "ai_inferred"})
    too_many = [{"category": "behavior_change", "student_text": f"item {i}"}
                for i in range(CHANGE_MAP_MAX_STUDENT_ITEMS + 1)]
    with pytest.raises(ValidationError):
        ChangeMapUpdateRequest.model_validate({"student_added_items": too_many})


def test_student_text_secret_guard():
    with pytest.raises(ValidationError):
        ChangeMapItemUpdate.model_validate(
            {"item_id": "cm-1", "student_decision": "edited",
             "student_text": "the key is sb_secret_fakefake123"})


def test_generate_request_shape():
    assert ChangeMapGenerateRequest.model_validate({}).replace_existing is False
    assert ChangeMapGenerateRequest.model_validate(
        {"replace_existing": True}).replace_existing is True
    with pytest.raises(ValidationError):
        ChangeMapGenerateRequest.model_validate({"force": True})
