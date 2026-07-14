"""M16C.1 Defense Report context and attempt-snapshot tests."""

import inspect
import json

import pytest

from app.services import gate_service, report_service
from app.services.llm_service import LLMService, StubProvider
from app.services.phase_service import PhaseNotFoundError, WorkspaceNotReadyError
from app.services.workflow_service import save_section
from tests.fakes import (
    InMemoryGateSessionRepository,
    InMemoryProjectRepository,
    ScriptedLLM,
)
from tests.test_gate_service import ANCHOR, USER, make_repos, run


def test_report_without_attempt_uses_current_curated_context_without_provider():
    repo, gates, _ = make_repos()
    run(save_section(repo, USER, 1, "evidence", {
        "entries": [{"kind": "note", "content": "Student-provided manual Evidence."}],
        "summary": "The student says this supports the observed behavior.",
    }))
    project_before = run(repo.get_project(USER))
    report = run(report_service.build_report_context(repo, gates, USER, 1))
    assert run(repo.get_project(USER)) == project_before
    assert report.workflow_context_source == "current_workflow"
    assert report.workflow_context.evidence.state == "manual"
    assert report.defense.state == "not_started"
    assert report.defense.turns == []
    assert "evaluator's outcome" in report.truth_notice
    assert "not independent proof" in report.truth_notice
    assert "llm_service" not in inspect.getsource(report_service)


def test_active_attempt_uses_stable_server_snapshot_after_workflow_changes():
    repo, gates, _ = make_repos()
    started = run(gate_service.start_gate(repo, gates, USER))
    llm = ScriptedLLM(["Why does your `matches` table keep user_id on each row?"])
    run(gate_service.submit_anchor(repo, gates, llm, USER, started["gate_session_id"], ANCHOR))
    before = run(report_service.build_report_context(repo, gates, USER, 1))
    assert before.workflow_context_source == "defense_attempt"
    assert before.workflow_context.evidence.state == "missing"

    run(save_section(repo, USER, 1, "evidence", {
        "entries": [{"kind": "note", "content": "Added only after Defense began."}],
        "summary": "Later mutable work.",
    }))
    after = run(report_service.build_report_context(repo, gates, USER, 1))
    assert after.workflow_context == before.workflow_context
    assert "Added only after" not in json.dumps(after.model_dump(mode="json"))
    followup_llm = ScriptedLLM([
        "What would change in your `matches` table if one match had multiple owners?"
    ])
    run(gate_service.generate_followup(
        repo,
        gates,
        followup_llm,
        USER,
        started["gate_session_id"],
        2,
        "The user_id field currently identifies the one owner.",
    ))
    assert "Added only after Defense began" not in followup_llm.calls[0][0]
    assert len(followup_llm.calls) == 1
    session = run(gates.get_session(USER, started["gate_session_id"]))
    assert "workflow_context_snapshot" in session["turns"][0]
    assert "workflow_context_snapshot" not in json.dumps(
        run(gate_service.get_current_gate(repo, gates, USER))
    )


def test_report_preserves_defense_transcript_and_outcome_but_never_hidden_score():
    repo, gates, _ = make_repos()
    sid = run(gate_service.start_gate(repo, gates, USER))["gate_session_id"]
    context = report_service.workflow_context_service.build_workflow_context(
        run(repo.get_project(USER)), 1
    )
    run(gates.update_session(USER, sid, {
        "anchor_statement": ANCHOR,
        "turns": [
            {
                "turn": 1,
                "question": "Why this table?",
                "answer": "Because ownership is per row.",
                "workflow_context_snapshot": context.model_dump(mode="json"),
            },
            {"turn": 2, "question": "What fails?", "answer": "The query."},
            {"turn": 3, "question": "What if shared?", "answer": "Add membership."},
        ],
        "passed": False,
        "reason": "Implementation ripple was not explained.",
        "score": 3,
    }))
    report = run(report_service.build_report_context(repo, gates, USER, 1))
    body = report.model_dump(mode="json")
    assert body["defense"]["state"] == "failed"
    assert body["defense"]["evaluator_outcome"] == "FAIL"
    assert len(body["defense"]["turns"]) == 3
    serialized = json.dumps(body)
    assert '"score"' not in serialized
    assert "workflow_context_snapshot" not in serialized
    assert "grounding" not in serialized


def test_legacy_attempt_without_snapshot_uses_documented_current_fallback():
    repo, gates, project = make_repos()
    run(gates.create_session(USER, {
        "project_id": project["id"],
        "phase_id": 1,
        "turns": [{"turn": 1, "question": "Legacy?", "answer": None}],
    }))
    report = run(report_service.build_report_context(repo, gates, USER, 1))
    assert report.workflow_context_source == "current_workflow"
    assert report.defense.state == "in_progress"


def test_malformed_snapshot_metadata_uses_current_workflow_fallback():
    repo, gates, project = make_repos()
    current = report_service.workflow_context_service.build_workflow_context(project, 1)
    snapshot = current.model_dump(mode="json")
    snapshot["schema_version"] = "999"
    run(gates.create_session(USER, {
        "project_id": project["id"],
        "phase_id": 1,
        "turns": [{
            "turn": 1,
            "question": "Legacy question?",
            "answer": None,
            "workflow_context_snapshot": snapshot,
        }],
    }))
    report = run(report_service.build_report_context(repo, gates, USER, 1))
    assert report.workflow_context_source == "current_workflow"
    assert report.workflow_context == current


def test_report_redacts_and_bounds_hostile_historical_transcript_values():
    repo, gates, project = make_repos()
    fake_secret = "sb_secret_FAKEVALUE12345678"
    fake_bearer = "Bearer abcdefghijklmnopqrstuvwxyz"
    run(gates.create_session(USER, {
        "project_id": project["id"],
        "phase_id": 1,
        "turns": [
            {
                "turn": 1,
                "question": fake_secret + " " + ("q" * 5_000),
                "answer": fake_bearer + " " + ("a" * 9_000),
            },
            {
                "turn": 2,
                "question": "unsafe\x00question",
                "answer": "unsafe\x00answer",
            },
        ],
        "passed": False,
        "reason": "AIza12345678901234567890" + " " + ("r" * 3_000),
    }))
    report = run(report_service.build_report_context(repo, gates, USER, 1))
    body = json.dumps(report.model_dump(mode="json"))
    assert fake_secret not in body
    assert fake_bearer not in body
    assert "AIza12345678901234567890" not in body
    assert body.count("[REDACTED_SECRET]") == 3
    assert body.count("[TRUNCATED]") == 3
    assert len(report.defense.turns) == 1
    assert len(report.defense.turns[0].question) <= report_service.MAX_REPORT_QUESTION_CHARS
    assert len(report.defense.turns[0].answer) <= report_service.MAX_REPORT_ANSWER_CHARS
    assert len(report.defense.evaluator_reason) <= report_service.MAX_REPORT_REASON_CHARS


def test_report_owner_and_phase_isolation():
    repo, gates, _ = make_repos()
    with pytest.raises(WorkspaceNotReadyError):
        run(report_service.build_report_context(repo, gates, "other-user", 1))
    with pytest.raises(PhaseNotFoundError):
        run(report_service.build_report_context(repo, gates, USER, 99))
    phase2 = run(report_service.build_report_context(repo, gates, USER, 2))
    assert phase2.phase_number == 2
    assert phase2.workflow_context.phase_number == 2
    assert phase2.defense.state == "not_started"
