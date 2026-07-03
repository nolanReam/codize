"""Functional unlock service tests — the hidden consecutive-score rule,
idempotent grants, ownership, safe client views, and the gate PASS/FAIL
integration, against the in-memory fakes."""

import asyncio

import pytest

from app.services.unlock_service import (
    QUALIFYING_SCORE,
    evaluate_unlocks,
    list_unlocks,
    qualifying_phases,
)
from tests.fakes import (
    InMemoryGateSessionRepository,
    InMemoryProjectRepository,
    InMemoryUnlockRepository,
    RaisingUnlockRepository,
)
from tests.test_gate_service import (
    FAIL_VERDICT,
    OTHER_USER,
    PASS_VERDICT,
    USER,
    make_repos,
    run_full_gate,
)


def run(coro):
    return asyncio.run(coro)


def make_project(project_id="proj-1"):
    return {
        "id": project_id,
        "roadmap": {
            "phases": [
                {"phase": n, "functional_unlock": f"Reward for phase {n}"}
                for n in range(1, 8)
            ]
        },
    }


def seed_passed_gates(gates, project_id, phase_scores, user=USER):
    for phase, score in phase_scores.items():
        run(gates.create_session(user, {
            "project_id": project_id, "phase_id": phase,
            "passed": True, "score": score,
        }))


# --- the hidden rule -------------------------------------------------------------

def test_qualifying_phases_requires_two_consecutive_at_threshold():
    assert qualifying_phases({}) == set()
    assert qualifying_phases({1: 10}) == set()                # single gate never qualifies
    assert qualifying_phases({1: 8, 2: 7}) == {2}             # score exactly 7 qualifies
    assert qualifying_phases({1: 8, 2: 6}) == set()           # second below threshold
    assert qualifying_phases({1: 6, 2: 8}) == set()           # first below threshold
    assert qualifying_phases({1: 8, 3: 9}) == set()           # not consecutive
    assert qualifying_phases({1: 8, 2: 7, 3: 9}) == {2, 3}    # each qualifying pair
    assert qualifying_phases({1: 6, 2: 8, 3: 9, 4: 5, 5: 7, 6: 9}) == {3, 6}


def test_no_unlock_from_failed_gates_even_with_high_scores():
    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    project = make_project()
    # a failed session's score never counts, whatever it is
    run(gates.create_session(USER, {"project_id": project["id"], "phase_id": 1,
                                    "passed": True, "score": 9}))
    run(gates.create_session(USER, {"project_id": project["id"], "phase_id": 2,
                                    "passed": False, "score": 9, "failed_at": "2026-07-03T00:00:00+00:00"}))
    assert run(evaluate_unlocks(gates, unlocks, USER, project)) == []
    assert run(unlocks.list_unlocks(USER, project["id"])) == []


def test_unlock_granted_after_two_consecutive_qualifying_passes():
    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    project = make_project()
    seed_passed_gates(gates, project["id"], {1: 8})
    assert run(evaluate_unlocks(gates, unlocks, USER, project)) == []  # one gate is not enough

    seed_passed_gates(gates, project["id"], {2: 7})
    granted = run(evaluate_unlocks(gates, unlocks, USER, project))
    assert len(granted) == 1
    view = granted[0]
    assert view["phase"] == 2
    assert view["unlock_key"] == "phase-2-functional-unlock"
    assert view["project_id"] == project["id"]
    assert view["description"] == "Reward for phase 2"
    rows = run(unlocks.list_unlocks(USER, project["id"]))
    assert [r["phase_number"] for r in rows] == [2]
    assert rows[0]["user_id"] == USER


def test_evaluation_is_idempotent_and_never_duplicates_rows():
    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    project = make_project()
    seed_passed_gates(gates, project["id"], {1: 9, 2: 9})
    assert len(run(evaluate_unlocks(gates, unlocks, USER, project))) == 1
    for _ in range(3):
        assert run(evaluate_unlocks(gates, unlocks, USER, project)) == []
    assert len(run(unlocks.list_unlocks(USER, project["id"]))) == 1


def test_duplicate_insert_race_is_ignored_not_reported_as_new():
    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    project = make_project()
    seed_passed_gates(gates, project["id"], {1: 9, 2: 9})
    # simulate a concurrent writer having inserted the same key already:
    # the repo's unique-constraint behavior returns None, so nothing is "new"
    run(unlocks.create_unlock(USER, {"project_id": project["id"],
                                     "phase_number": 2,
                                     "unlock_key": "phase-2-functional-unlock"}))
    row = run(unlocks.create_unlock(USER, {"project_id": project["id"],
                                           "phase_number": 2,
                                           "unlock_key": "phase-2-functional-unlock"}))
    assert row is None
    assert len(run(unlocks.list_unlocks(USER, project["id"]))) == 1


def test_missed_grant_self_heals_on_a_later_evaluation():
    gates = InMemoryGateSessionRepository()
    project = make_project()
    seed_passed_gates(gates, project["id"], {1: 8, 2: 8})
    with pytest.raises(Exception):
        run(evaluate_unlocks(gates, RaisingUnlockRepository(), USER, project))
    # next PASS re-evaluates from full history and backfills phase 2's unlock
    seed_passed_gates(gates, project["id"], {3: 9})
    unlocks = InMemoryUnlockRepository()
    granted = run(evaluate_unlocks(gates, unlocks, USER, project))
    assert {g["phase"] for g in granted} == {2, 3}


# --- ownership -------------------------------------------------------------------

def test_unlocks_are_scoped_to_their_owner():
    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    project = make_project()
    seed_passed_gates(gates, project["id"], {1: 9, 2: 9})
    run(evaluate_unlocks(gates, unlocks, USER, project))
    # the other user sees nothing, even for the same project id
    assert run(unlocks.list_unlocks(OTHER_USER, project["id"])) == []
    # and the other user's own gate history grants them nothing
    assert run(evaluate_unlocks(gates, unlocks, OTHER_USER, project)) == []


# --- client-facing views ---------------------------------------------------------

def test_views_carry_only_safe_fields_and_no_score_or_threshold():
    gates, unlocks = InMemoryGateSessionRepository(), InMemoryUnlockRepository()
    project = make_project()
    seed_passed_gates(gates, project["id"], {1: 9, 2: 9})
    granted = run(evaluate_unlocks(gates, unlocks, USER, project))
    listed = run(list_unlocks(_project_repo_with(project), unlocks, USER))
    for view in granted + listed["unlocks"]:
        assert set(view) == {"id", "unlock_key", "project_id", "phase",
                             "description", "unlocked_at"}
        text = str(view)
        assert "score" not in text and "threshold" not in text
        assert str(QUALIFYING_SCORE) not in view["unlock_key"]


def _project_repo_with(project):
    class _Repo:
        async def get_project(self, user_id):
            return project
    return _Repo()


def test_list_unlocks_with_no_project_is_empty_not_an_error():
    class _Empty:
        async def get_project(self, user_id):
            return None
    result = run(list_unlocks(_Empty(), InMemoryUnlockRepository(), USER))
    assert result == {"unlocks": []}


# --- gate flow integration -------------------------------------------------------

def test_gate_pass_flow_grants_unlock_on_second_qualifying_pass():
    repo, gates, _ = make_repos()
    unlocks = InMemoryUnlockRepository()
    high = '{"verdict": "PASS", "reason": "Strong.", "score": 8}'
    _, result, _ = run_full_gate(repo, gates, verdict=high, unlocks=unlocks)
    assert result["new_unlocks"] == []  # first qualifying pass alone: nothing
    _, result, _ = run_full_gate(repo, gates, verdict=high, unlocks=unlocks)
    assert [u["phase"] for u in result["new_unlocks"]] == [2]
    assert "score" not in str(result["new_unlocks"])


def test_gate_pass_below_threshold_grants_nothing():
    repo, gates, _ = make_repos()
    unlocks = InMemoryUnlockRepository()
    low = '{"verdict": "PASS", "reason": "Just enough.", "score": 6}'
    high = '{"verdict": "PASS", "reason": "Strong.", "score": 9}'
    for verdict in (high, low, high):  # 9, 6, 9 — never two consecutive >= 7
        _, result, _ = run_full_gate(repo, gates, verdict=verdict, unlocks=unlocks)
        assert result["new_unlocks"] == []
    project = run(repo.get_project(USER))
    assert run(unlocks.list_unlocks(USER, project["id"])) == []


def test_gate_fail_flow_never_evaluates_unlocks():
    repo, gates, _ = make_repos()
    # a raising unlock repo proves the FAIL path never touches unlock storage
    _, result, _ = run_full_gate(repo, gates, verdict=FAIL_VERDICT,
                                 unlocks=RaisingUnlockRepository())
    assert result["verdict"] == "FAIL"
    assert "new_unlocks" not in result


def test_unlock_storage_error_does_not_break_a_pass():
    repo, gates, _ = make_repos()
    _, result, _ = run_full_gate(repo, gates, verdict=PASS_VERDICT,
                                 unlocks=RaisingUnlockRepository())
    assert result["verdict"] == "PASS"
    assert result["current_phase"] == 2  # the pass itself fully applied
    assert result["new_unlocks"] == []
