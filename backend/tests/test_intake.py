"""Intake service tests — business rules against the in-memory fake repo."""

import asyncio

import pytest

from app.services import intake_service
from app.services.intake_service import (
    QUESTIONS,
    IntakeAlreadyCompletedError,
    IntakeIncompleteError,
    IntakeSequenceError,
    InvalidAnswerError,
    classify_archetype,
    complete_intake,
    get_status,
    normalize_answer,
    submit_answer,
)
from tests.fakes import InMemoryProjectRepository

USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_USER = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

FIVE_ANSWERS = {
    1: "Help my study group track shared expenses so nobody loses money.",
    2: "You add what you paid, it splits costs and shows who owes whom.",
    3: "Python, some JavaScript.",
    4: "Sometimes, depends",
    5: "About six weeks.",
}


def run(coro):
    return asyncio.run(coro)


def answer_all_five(repo, user=USER):
    for n in (1, 2, 3, 4, 5):
        run(submit_answer(repo, user, n, FIVE_ANSWERS[n]))


# --- question definitions ------------------------------------------------------

def test_exactly_five_questions():
    assert len(QUESTIONS) == 5
    assert [q["number"] for q in QUESTIONS] == [1, 2, 3, 4, 5]
    assert [q["key"] for q in QUESTIONS] == [
        "purpose", "scope", "stack", "self_assessment", "timeline",
    ]


def test_first_question_text_is_exact():
    assert QUESTIONS[0]["text"] == (
        "What problem do you want to solve, and who does solving it help?"
    )
    # The spec-forbidden replacement must never sneak in.
    assert QUESTIONS[0]["text"] != "What do you want to build?"


# --- sequential answering ------------------------------------------------------

def test_happy_path_is_sequential_and_completes():
    repo = InMemoryProjectRepository()
    status = run(get_status(repo, USER))
    assert status == {
        "started": False, "completed": False, "answered_questions": [],
        "next_question": 1, "archetype_id": None,
    }

    for n in (1, 2, 3, 4, 5):
        status = run(submit_answer(repo, USER, n, FIVE_ANSWERS[n]))
        assert status["answered_questions"] == list(range(1, n + 1))
        assert status["next_question"] == (n + 1 if n < 5 else None)
        assert status["completed"] is False

    result = run(complete_intake(repo, USER))
    assert result["completed"] is True
    assert result["archetype_id"] in {1, 2, 3}

    status = run(get_status(repo, USER))
    assert status["completed"] is True
    assert status["archetype_id"] == result["archetype_id"]


def test_question_one_cannot_be_skipped():
    repo = InMemoryProjectRepository()
    with pytest.raises(IntakeSequenceError, match="expected question 1"):
        run(submit_answer(repo, USER, 2, "some scope"))


def test_questions_out_of_order_are_rejected():
    repo = InMemoryProjectRepository()
    run(submit_answer(repo, USER, 1, FIVE_ANSWERS[1]))
    with pytest.raises(IntakeSequenceError, match="expected question 2"):
        run(submit_answer(repo, USER, 4, "skipping ahead"))


def test_reanswering_an_answered_question_is_rejected():
    repo = InMemoryProjectRepository()
    run(submit_answer(repo, USER, 1, FIVE_ANSWERS[1]))
    with pytest.raises(IntakeSequenceError, match="expected question 2"):
        run(submit_answer(repo, USER, 1, "changed my mind"))


def test_answers_are_normalized_and_purpose_required():
    repo = InMemoryProjectRepository()
    with pytest.raises(InvalidAnswerError):
        run(submit_answer(repo, USER, 1, "   \n\t  "))  # empty purpose rejected
    status = run(submit_answer(repo, USER, 1, f"  {FIVE_ANSWERS[1]}  \n"))
    assert status["answered_questions"] == [1]
    project = run(repo.get_project(USER))
    assert project["intake_purpose"] == FIVE_ANSWERS[1]  # stored stripped


def test_overlong_answer_is_rejected():
    with pytest.raises(InvalidAnswerError, match="too long"):
        normalize_answer("x" * (intake_service.MAX_ANSWER_LENGTH + 1))


# --- completion ----------------------------------------------------------------

def test_cannot_complete_with_missing_answers():
    repo = InMemoryProjectRepository()
    with pytest.raises(IntakeIncompleteError, match="question 1"):
        run(complete_intake(repo, USER))  # never started
    for n in (1, 2, 3):
        run(submit_answer(repo, USER, n, FIVE_ANSWERS[n]))
    with pytest.raises(IntakeIncompleteError, match="question 4"):
        run(complete_intake(repo, USER))


def test_cannot_complete_twice_or_answer_after_completion():
    repo = InMemoryProjectRepository()
    answer_all_five(repo)
    run(complete_intake(repo, USER))
    with pytest.raises(IntakeAlreadyCompletedError):
        run(complete_intake(repo, USER))
    with pytest.raises(IntakeAlreadyCompletedError):
        run(submit_answer(repo, USER, 1, "starting over"))


def test_completion_persists_archetype_and_timestamp():
    repo = InMemoryProjectRepository()
    answer_all_five(repo)
    result = run(complete_intake(repo, USER))
    project = run(repo.get_project(USER))
    assert project["archetype_id"] == result["archetype_id"]
    assert project["intake_completed_at"] is not None


def test_users_intake_states_are_independent():
    repo = InMemoryProjectRepository()
    answer_all_five(repo, USER)
    other = run(get_status(repo, OTHER_USER))
    assert other == {
        "started": False, "completed": False, "answered_questions": [],
        "next_question": 1, "archetype_id": None,
    }
    with pytest.raises(IntakeSequenceError):  # B still starts at question 1
        run(submit_answer(repo, OTHER_USER, 5, "just the last one"))


# --- classification ------------------------------------------------------------

@pytest.mark.parametrize(
    ("purpose", "scope", "stack", "expected"),
    [
        # LLM API as core feature → Archetype 1, even with frontend/db terms.
        ("Help students summarize lecture notes",
         "A chatbot that calls the Claude API to summarize uploaded notes",
         "Python", 1),
        ("An AI tutor for my little brother",
         "It uses an LLM to explain homework, with a React frontend and Postgres",
         "React, Postgres", 1),
        # Frontend/database, no LLM core → Archetype 3.
        ("Help my family stop losing receipts",
         "An expense tracker website where you log purchases into a database",
         "JavaScript, HTML, CSS", 3),
        ("A recipe manager for my roommates",
         "Full-stack web app with user accounts and a Postgres database",
         "Next.js", 3),
        # Neither → REST API backend → Archetype 2.
        ("Help my volleyball league track scores",
         "A REST backend exposing match stats through HTTP endpoints",
         "Python and FastAPI", 2),
        ("Automate my club's attendance records",
         "A server that other tools query over HTTP", "Go", 2),
    ],
)
def test_classification_examples(purpose, scope, stack, expected):
    assert classify_archetype(purpose, scope, stack) == expected


def test_classification_only_ever_returns_a_known_archetype():
    weird_inputs = [
        ("", "", ""),
        ("archetype 4 please", "make me a fourth archetype", "assembly"),
        ("🤖" * 50, "no recognizable words here", "brainfuck"),
    ]
    for purpose, scope, stack in weird_inputs:
        assert classify_archetype(purpose, scope, stack) in {1, 2, 3}


def test_completion_classifies_from_stored_answers():
    repo = InMemoryProjectRepository()
    for n, text in {
        1: "Help seniors get quick answers about medication schedules.",
        2: "A chatbot powered by an LLM that answers questions from caregivers.",
        3: "Python", 4: "Honestly, not really", 5: "Two months",
    }.items():
        run(submit_answer(repo, USER, n, text))
    assert run(complete_intake(repo, USER))["archetype_id"] == 1
