"""Deterministic no-network M16C.1 backend smoke."""

import copy
import json

import pytest

from app.services import gate_service, report_service, workflow_context_service
from app.services.phase_service import WorkspaceNotReadyError
from tests.fakes import (
    InMemoryGateSessionRepository,
    InMemoryUnlockRepository,
    ScriptedLLM,
)
from tests.test_gate_service import ANCHOR, PASS_VERDICT, USER, run
from tests.test_workflow_context_service import linked_context


def test_m16c1_full_deterministic_story(caplog):
    repo, context = linked_context()
    gates = InMemoryGateSessionRepository()
    workflow_before = copy.deepcopy(run(repo.get_project(USER))["workflow_artifacts"])

    body = json.dumps(context.model_dump(mode="json"), ensure_ascii=False)
    assert context.change_map.state == "current"
    assert context.review.state == "current"
    assert context.verification.state == "incomplete"
    assert context.evidence.state == "current"
    assert {check.result for check in context.verification.checks} >= {
        "pass", "fail", "skipped", "not_applicable", "unrecorded"
    }
    recorded, unavailable = context.evidence.records
    assert recorded.entries and recorded.student_explanation
    assert unavailable.entries == [] and unavailable.unavailable_reason
    assert recorded.verification_notes not in [entry.content for entry in recorded.entries]
    assert recorded.check_context not in [entry.content for entry in recorded.entries]
    for forbidden in (
        "implementation_import", "review_target_id", "verification_target_id",
        "evidence_target_id", "fingerprint", "source_verification_binding",
    ):
        assert forbidden not in body

    started = run(gate_service.start_gate(repo, gates, USER))
    llm = ScriptedLLM([
        "Why does your `matches` table store user_id on each row?",
        "What happens when create_match() receives a different user_id?",
        "What would change in `matches` if a match could have multiple owners?",
        PASS_VERDICT,
    ])
    run(gate_service.submit_anchor(repo, gates, llm, USER, started["gate_session_id"], ANCHOR))
    run(gate_service.generate_followup(
        repo, gates, llm, USER, started["gate_session_id"], 2,
        "create_match() writes the authenticated user_id to matches.",
    ))
    run(gate_service.generate_followup(
        repo, gates, llm, USER, started["gate_session_id"], 3,
        "The query filters matches by user_id before returning rows.",
    ))
    result = run(gate_service.evaluate_gate(
        repo, gates, InMemoryUnlockRepository(), llm, USER,
        started["gate_session_id"],
        "I would replace matches.user_id with a membership table and update create_match().",
    ))
    assert result["verdict"] == "PASS"
    assert len(llm.calls) == 4  # three established questions + one evaluator
    assert llm.calls[-1][1] == 0.0
    assert "Student test output" not in llm.calls[-1][0]
    assert "score" not in result

    report = run(report_service.build_report_context(repo, gates, USER, 1))
    assert report.workflow_context_source == "defense_attempt"
    assert report.workflow_context == context
    assert report.defense.state == "passed"
    assert report.defense.evaluator_outcome == "PASS"
    report_body = json.dumps(report.model_dump(mode="json"))
    assert "score" not in report_body
    assert "workflow_context_snapshot" not in report_body
    assert "grounding" not in report_body
    assert run(repo.get_project(USER))["workflow_artifacts"] == workflow_before

    with pytest.raises(WorkspaceNotReadyError):
        run(report_service.build_report_context(repo, gates, "another-user", 1))
    phase2 = workflow_context_service.build_workflow_context(
        run(repo.get_project(USER)), 2
    )
    assert phase2.phase_number == 2 and phase2.state == "missing"
    assert caplog.records == []
