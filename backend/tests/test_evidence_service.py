"""M16B.3A deterministic Verification -> Evidence service tests."""

import copy
import inspect
import json

import pytest

from app.schemas.workflow import EvidenceFromVerificationRequest
from app.services import evidence_service, verification_service
from app.services.defense_context_service import (
    build_defense_context,
    render_defense_context,
    summarize_defense_context,
)
from app.services.evidence_service import (
    EvidenceAlreadyExistsError,
    EvidenceStaleError,
    EvidenceVerificationNotLinkedError,
    EvidenceVerificationStaleError,
    InvalidEvidenceSelectionError,
)
from app.services.phase_service import PhaseNotFoundError, WorkspaceNotReadyError
from app.services.workflow_service import InvalidArtifactError, save_section
from tests.fakes import InMemoryProjectRepository
from tests.test_phase_service import OTHER_USER, USER, run, seed_active_project
from tests.test_review_service import initialized
from tests.test_verification_service import create, seed_completed_review
from tests.test_workflow_service import EVIDENCE, PROMPT_BUILDER, VERIFICATION


RESULTS = ("pass", "fail", "skipped", "not_applicable", None, "pass")


def prepared_verification(*, results=RESULTS, phase=1):
    categories = tuple(verification_service.SUGGESTION_TEMPLATES)
    repo, _ = seed_completed_review(needs_categories=categories)
    artifact = create(repo, phase=phase)
    updates = []
    for target, result in zip(artifact["verification_targets"], results):
        if result is None:
            continue
        update = {
            "verification_target_id": target["verification_target_id"],
            "result": result,
            "result_notes": f"Observed {result} for {target['category']}.",
        }
        if target["category"] == "behavior_change":
            update["student_check"] = "Run the student-edited behavior check."
        updates.append(update)
    if updates:
        artifact = run(save_section(
            repo, USER, phase, "verification", {"target_updates": updates}
        ))["artifact"]
    return repo, artifact


def request(*ids, replace=False):
    return EvidenceFromVerificationRequest(
        selected_verification_target_ids=list(ids),
        replace_existing=replace,
    )


def create_evidence(repo, *ids, replace=False, phase=1):
    return run(evidence_service.create_from_verification(
        repo, USER, phase, request(*ids, replace=replace)
    ))["artifact"]


def test_existing_handoff_helper_preserves_every_outcome_linkage_and_order():
    repo, artifact = prepared_verification()
    stored = verification_service.get_stored_verification(
        run(repo.get_project(USER)), 1
    )
    handoff = verification_service.evidence_handoff_targets(stored)
    assert [target.verification_target_id for target in handoff] == [
        target["verification_target_id"] for target in artifact["verification_targets"]
    ]
    assert [target.result for target in handoff[:5]] == [
        "pass", "fail", "skipped", "not_applicable", None
    ]
    assert handoff[0].check_wording == "Run the student-edited behavior check."
    assert handoff[1].result_notes == "Observed fail for implementation_decision."
    assert handoff[0].review_target_id
    assert handoff[0].change_map_item_id

    zero_repo, _ = seed_completed_review(needs_categories=())
    create(zero_repo)
    zero = verification_service.get_stored_verification(
        run(zero_repo.get_project(USER)), 1
    )
    assert verification_service.evidence_handoff_targets(zero) == []


def test_preview_states_missing_manual_zero_current_incomplete_and_stale():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    before = copy.deepcopy(run(repo.get_project(USER))["workflow_artifacts"])
    missing = run(evidence_service.handoff_preview(repo, USER, 1))
    assert missing["verification_state"] == "verification_required"
    assert missing["targets"] == []
    assert run(repo.get_project(USER))["workflow_artifacts"] == before

    run(save_section(repo, USER, 1, "verification", VERIFICATION))
    manual = run(evidence_service.handoff_preview(repo, USER, 1))
    assert manual["mode"] == "manual_verification"
    assert manual["eligible_count"] == 0

    linked_repo, artifact = prepared_verification()
    preview = run(evidence_service.handoff_preview(linked_repo, USER, 1))
    assert preview["verification_state"] == "current"
    assert [target["result"] for target in preview["targets"][:5]] == [
        "pass", "fail", "skipped", "not_applicable", "unrecorded"
    ]
    assert preview["eligible_count"] == 3
    assert [target["performed"] for target in preview["targets"][:5]] == [
        True, True, False, False, False
    ]
    assert preview["targets"][0]["check"] == "Run the student-edited behavior check."
    assert "review_target_id" not in json.dumps(preview)
    assert "change_map_item_id" not in json.dumps(preview)
    assert "fingerprint" not in json.dumps(preview)

    zero_repo, _ = seed_completed_review(needs_categories=())
    create(zero_repo)
    zero = run(evidence_service.handoff_preview(zero_repo, USER, 1))
    assert zero["verification_state"] == "current"
    assert zero["targets"] == [] and zero["eligible_count"] == 0

    review = run(linked_repo.get_project(USER))["workflow_artifacts"]["1"]["review_board"]
    run(save_section(linked_repo, USER, 1, "review_board", {
        "target_updates": [{
            "review_target_id": target["review_target_id"],
            "review_decision": "keep",
        } for target in review["review_targets"]]
    }))
    stale = run(evidence_service.handoff_preview(linked_repo, USER, 1))
    assert stale["verification_state"] == "stale"
    assert stale["eligible_count"] == 0
    assert all(target["eligibility"] == "ineligible" for target in stale["targets"])
    assert artifact["verification_targets"]  # old linked context remains readable


def test_pass_and_fail_initialize_empty_records_in_server_order_only():
    repo, verification = prepared_verification()
    pass_id = verification["verification_targets"][0]["verification_target_id"]
    fail_id = verification["verification_targets"][1]["verification_target_id"]
    before = copy.deepcopy(run(repo.get_project(USER)))
    artifact = create_evidence(repo, fail_id, pass_id)
    after = run(repo.get_project(USER))

    assert artifact["initialized_from_verification"] is True
    assert artifact["stale"] is False
    assert artifact["evidence_record_complete"] is False
    targets = artifact["evidence_targets"]
    assert [target["source_verification_target_id"] for target in targets] == [
        pass_id, fail_id
    ]
    assert [target["verification_result_snapshot"] for target in targets] == [
        "pass", "fail"
    ]
    assert all(target["evidence_status"] == "not_addressed" for target in targets)
    assert all(target["entries"] == [] for target in targets)
    assert artifact["entries"] == [] and artifact["summary"] is None
    serialized = json.dumps(artifact)
    assert "source_review_target_id" not in serialized
    assert "source_change_map_item_id" not in serialized
    assert "source_verification_binding" not in serialized
    changed = {key for key in after if before[key] != after[key]}
    assert changed == {"workflow_artifacts"}
    for sibling in ("prompt_builder", "review_board", "verification", "change_map", "implementation_import"):
        assert after["workflow_artifacts"]["1"].get(sibling) == before[
            "workflow_artifacts"
        ]["1"].get(sibling)


@pytest.mark.parametrize("index", [2, 3, 4])
def test_skipped_not_applicable_and_unrecorded_cannot_be_selected(index):
    repo, verification = prepared_verification()
    target_id = verification["verification_targets"][index]["verification_target_id"]
    with pytest.raises(InvalidEvidenceSelectionError, match="only performed"):
        create_evidence(repo, target_id)
    assert "evidence" not in run(repo.get_project(USER))["workflow_artifacts"]["1"]


def test_unknown_manual_stale_and_existing_work_fail_safely_with_explicit_replacement():
    repo, verification = prepared_verification()
    pass_id = verification["verification_targets"][0]["verification_target_id"]
    with pytest.raises(InvalidEvidenceSelectionError, match="does not match"):
        create_evidence(repo, "vt-000000000000")

    manual_repo = InMemoryProjectRepository()
    seed_active_project(manual_repo)
    run(save_section(manual_repo, USER, 1, "verification", VERIFICATION))
    with pytest.raises(EvidenceVerificationNotLinkedError):
        create_evidence(manual_repo, pass_id)

    run(save_section(repo, USER, 1, "evidence", EVIDENCE))
    with pytest.raises(EvidenceAlreadyExistsError):
        create_evidence(repo, pass_id)
    replaced = create_evidence(repo, pass_id, replace=True)
    assert replaced["entries"] == []
    assert replaced["evidence_targets"][0]["evidence_status"] == "not_addressed"
    with pytest.raises(EvidenceAlreadyExistsError):
        create_evidence(repo, pass_id)

    review = run(repo.get_project(USER))["workflow_artifacts"]["1"]["review_board"]
    run(save_section(repo, USER, 1, "review_board", {
        "target_updates": [{
            "review_target_id": target["review_target_id"],
            "review_decision": "keep",
        } for target in review["review_targets"]]
    }))
    with pytest.raises(EvidenceVerificationStaleError):
        create_evidence(repo, pass_id, replace=True)
    assert evidence_service.evidence_view(run(repo.get_project(USER)), 1)["stale"] is True


def test_student_evidence_and_unavailable_updates_preserve_provenance_and_verification():
    repo, verification = prepared_verification()
    selected = [
        verification["verification_targets"][0]["verification_target_id"],
        verification["verification_targets"][1]["verification_target_id"],
    ]
    before_verification = copy.deepcopy(
        run(repo.get_project(USER))["workflow_artifacts"]["1"]["verification"]
    )
    created = create_evidence(repo, *selected)
    first, second = created["evidence_targets"]
    stored_before = evidence_service.get_stored_evidence(run(repo.get_project(USER)), 1)

    updated = run(save_section(repo, USER, 1, "evidence", {
        "target_updates": [
            {
                "evidence_target_id": first["evidence_target_id"],
                "evidence_status": "evidence_recorded",
                "entries": [{
                    "kind": "test_output",
                    "content": "2 passed in 0.10s",
                }],
                "explanation": "The selected check produced this output.",
            },
            {
                "evidence_target_id": second["evidence_target_id"],
                "evidence_status": "evidence_unavailable",
                "entries": [],
                "explanation": None,
                "unavailable_reason": "The temporary terminal session was closed.",
            },
        ]
    }))["artifact"]

    assert updated["evidence_record_complete"] is True
    assert updated["evidence_targets"][0]["evidence_status"] == "evidence_recorded"
    assert updated["evidence_targets"][1]["evidence_status"] == "evidence_unavailable"
    assert updated["evidence_targets"][1]["entries"] == []
    assert run(repo.get_project(USER))["workflow_artifacts"]["1"]["verification"] == before_verification
    stored_after = evidence_service.get_stored_evidence(run(repo.get_project(USER)), 1)
    assert stored_after.source_verification_binding == stored_before.source_verification_binding
    for before, after in zip(stored_before.evidence_targets, stored_after.evidence_targets):
        for field in (
            "evidence_target_id",
            "source_verification_target_id",
            "source_review_target_id",
            "source_change_map_item_id",
            "category",
            "check_snapshot",
            "verification_result_snapshot",
            "verification_result_notes_snapshot",
        ):
            assert getattr(after, field) == getattr(before, field)


def test_invalid_linked_updates_do_not_erase_or_forge_state():
    repo, verification = prepared_verification()
    selected = verification["verification_targets"][0]["verification_target_id"]
    artifact = create_evidence(repo, selected)
    evidence_id = artifact["evidence_targets"][0]["evidence_target_id"]
    before = copy.deepcopy(run(repo.get_project(USER))["workflow_artifacts"])
    invalid_payloads = (
        {"target_updates": [{
            "evidence_target_id": evidence_id,
            "evidence_status": "evidence_unavailable",
        }]},
        {"target_updates": [{
            "evidence_target_id": evidence_id,
            "evidence_status": "evidence_recorded",
            "entries": [],
        }]},
        {"target_updates": [{
            "evidence_target_id": "ev-000000000000",
            "evidence_status": "evidence_unavailable",
            "unavailable_reason": "No retained output.",
        }]},
        {"target_updates": [
            {"evidence_target_id": evidence_id, "explanation": "one"},
            {"evidence_target_id": evidence_id, "explanation": "two"},
        ]},
        {"source_verification_binding": {}, "stale": False},
    )
    for payload in invalid_payloads:
        with pytest.raises((InvalidArtifactError, EvidenceStaleError)):
            run(save_section(repo, USER, 1, "evidence", payload))
        assert run(repo.get_project(USER))["workflow_artifacts"] == before


def test_selected_context_changes_stale_but_unselected_and_siblings_do_not():
    repo, verification = prepared_verification()
    selected = verification["verification_targets"][0]["verification_target_id"]
    unselected = verification["verification_targets"][1]["verification_target_id"]
    artifact = create_evidence(repo, selected)
    evidence_id = artifact["evidence_targets"][0]["evidence_target_id"]

    run(save_section(repo, USER, 1, "prompt_builder", PROMPT_BUILDER))
    assert evidence_service.evidence_view(run(repo.get_project(USER)), 1)["stale"] is False
    run(save_section(repo, USER, 1, "verification", {"target_updates": [{
        "verification_target_id": unselected,
        "result_notes": "Changed only an unselected result note.",
    }]}))
    assert evidence_service.evidence_view(run(repo.get_project(USER)), 1)["stale"] is False

    run(save_section(repo, USER, 1, "verification", {"target_updates": [{
        "verification_target_id": selected,
        "student_check": "A changed selected check.",
    }]}))
    stale = evidence_service.evidence_view(run(repo.get_project(USER)), 1)
    assert stale["stale"] is True
    assert stale["evidence_targets"][0]["evidence_target_id"] == evidence_id
    with pytest.raises(EvidenceStaleError):
        run(save_section(repo, USER, 1, "evidence", {"target_updates": [{
            "evidence_target_id": evidence_id,
            "evidence_status": "evidence_unavailable",
            "unavailable_reason": "Would otherwise be valid.",
        }]}))


@pytest.mark.parametrize("field,value", [
    ("student_check", "Changed selected check."),
    ("result", "fail"),
    ("result_notes", "Changed selected result notes."),
])
def test_each_selected_verification_change_stales_evidence(field, value):
    repo, verification = prepared_verification()
    selected = verification["verification_targets"][0]["verification_target_id"]
    create_evidence(repo, selected)
    run(save_section(repo, USER, 1, "verification", {"target_updates": [{
        "verification_target_id": selected,
        field: value,
    }]}))
    assert evidence_service.evidence_view(run(repo.get_project(USER)), 1)["stale"] is True


def test_verification_rebuild_stales_and_explicit_evidence_rebuild_rebinds():
    repo, verification = prepared_verification()
    selected = verification["verification_targets"][0]["verification_target_id"]
    create_evidence(repo, selected)
    create(repo, replace=True)
    assert evidence_service.evidence_view(run(repo.get_project(USER)), 1)["stale"] is True
    current = verification_service.verification_view(run(repo.get_project(USER)), 1)
    current_id = current["verification_targets"][0]["verification_target_id"]
    run(save_section(repo, USER, 1, "verification", {"target_updates": [{
        "verification_target_id": current_id,
        "result": "pass",
    }]}))
    rebuilt = create_evidence(repo, current_id, replace=True)
    assert rebuilt["stale"] is False
    assert rebuilt["evidence_targets"][0]["evidence_status"] == "not_addressed"


def test_manual_evidence_read_put_completion_and_downstream_compatibility_remain():
    repo = InMemoryProjectRepository()
    seed_active_project(repo)
    saved = run(save_section(repo, USER, 1, "evidence", EVIDENCE))["artifact"]
    assert saved["entries"] == EVIDENCE["entries"]
    assert saved["summary"] == EVIDENCE["summary"]
    assert "initialized_from_verification" not in saved
    replaced = run(save_section(repo, USER, 1, "evidence", {
        "entries": [{"kind": "note", "content": "Manual replacement."}],
        "summary": "Still manual.",
    }))["artifact"]
    assert replaced["entries"] == [{"kind": "note", "content": "Manual replacement."}]

    rendered = render_defense_context(run(build_defense_context(repo, USER, 1)))
    assert "Manual replacement." in rendered
    assert "Still manual." in rendered


def test_linked_target_evidence_enters_defense_only_through_m16c_curated_context():
    repo, verification = prepared_verification()
    selected = verification["verification_targets"][0]["verification_target_id"]
    artifact = create_evidence(repo, selected)
    evidence_id = artifact["evidence_targets"][0]["evidence_target_id"]
    run(save_section(repo, USER, 1, "evidence", {"target_updates": [{
        "evidence_target_id": evidence_id,
        "evidence_status": "evidence_recorded",
        "entries": [{"kind": "test_output", "content": "M16C-only nested output"}],
        "explanation": "M16C-only nested explanation",
    }]}))
    pack = run(build_defense_context(repo, USER, 1))
    rendered = render_defense_context(pack)
    assert "M16C-only nested output" in rendered
    assert "M16C-only nested explanation" in rendered
    assert "source_verification_binding" not in rendered
    assert "source_review_target_id" not in rendered
    assert "source_change_map_item_id" not in rendered
    evidence_source = next(
        source for source in pack.source_manifest
        if source.source_id == "workflow.evidence"
    )
    assert evidence_source.present is True
    summary = summarize_defense_context(pack).model_dump(mode="json")
    assert any(
        source["source_id"] == "workflow.evidence"
        for source in summary["included_sources"]
    )


def test_ownership_phase_isolation_and_no_provider_or_downstream_dependency():
    repo, verification = prepared_verification()
    selected = verification["verification_targets"][0]["verification_target_id"]
    with pytest.raises(WorkspaceNotReadyError):
        run(evidence_service.handoff_preview(repo, OTHER_USER, 1))
    with pytest.raises(PhaseNotFoundError):
        run(evidence_service.handoff_preview(repo, USER, 99))
    create_evidence(repo, selected)
    assert evidence_service.evidence_view(run(repo.get_project(USER)), 2) is None

    source = inspect.getsource(evidence_service)
    assert "llm_service" not in source
    assert "Gemini" not in source
    assert "OpenRouter" not in source
    assert "gate_service" not in source
    assert "evaluation_service" not in source
    assert "defense_context_service" not in source
