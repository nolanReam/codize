"""Intake service tests — business rules against the in-memory fake repo."""

import asyncio
import copy

import pytest

from app.services import intake_service
from app.services.intake_service import (
    ENTRY_PROFILE_KEY,
    QUESTIONS,
    IntakeAlreadyCompletedError,
    IntakeIncompleteError,
    IntakeSequenceError,
    InvalidAnswerError,
    classify_archetype,
    complete_intake,
    entry_profile_from_project,
    get_entry_profile,
    get_status,
    normalize_answer,
    submit_answer,
    update_entry_profile,
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


# --- adaptive entry profile (M17) --------------------------------------------

@pytest.mark.parametrize(
    ("situation", "ai_changed", "recommended", "recovery"),
    [
        ("starting_fresh", None, "prompt_builder", False),
        ("already_building", "not_yet", "prompt_builder", False),
        ("already_building", "yes", "implementation_import", False),
        ("already_building", "unsure", "implementation_import", False),
        ("stuck", None, "quick_start", True),
    ],
)
def test_entry_recommendation_is_deterministic(
    situation, ai_changed, recommended, recovery
):
    repo = InMemoryProjectRepository()
    updates = {
        "current_situation": situation,
        "coding_confidence": "know_basics",
    }
    if ai_changed is not None:
        updates["ai_changed_files"] = ai_changed
    profile = run(update_entry_profile(repo, USER, updates))["profile"]
    assert profile["completed"] is True
    assert profile["recommended_start"] == recommended
    assert profile["recovery_emphasis"] is recovery


@pytest.mark.parametrize(
    ("confidence", "depth"),
    [
        ("new_to_code", "more"),
        ("know_basics", "standard"),
        ("comfortable", "minimal"),
    ],
)
def test_coding_confidence_changes_guidance_not_features(confidence, depth):
    repo = InMemoryProjectRepository()
    profile = run(
        update_entry_profile(
            repo,
            USER,
            {"current_situation": "starting_fresh", "coding_confidence": confidence},
        )
    )["profile"]
    assert profile["guidance_depth"] == depth
    assert profile["recommended_start"] == "prompt_builder"


def test_partial_entry_profile_resumes_without_a_default_situation():
    repo = InMemoryProjectRepository()
    profile = run(
        update_entry_profile(repo, USER, {"coding_confidence": "new_to_code"})
    )["profile"]
    assert profile["current_situation"] is None
    assert profile["completed"] is False
    assert profile["recommended_start"] is None
    assert run(get_entry_profile(repo, USER))["profile"] == profile


def test_irrelevant_ai_change_choice_is_rejected_and_situation_change_clears_it():
    repo = InMemoryProjectRepository()
    with pytest.raises(intake_service.InvalidEntryProfileError):
        run(update_entry_profile(repo, USER, {"ai_changed_files": "yes"}))
    run(
        update_entry_profile(
            repo,
            USER,
            {
                "current_situation": "already_building",
                "coding_confidence": "know_basics",
                "ai_changed_files": "yes",
            },
        )
    )
    changed = run(
        update_entry_profile(repo, USER, {"current_situation": "starting_fresh"})
    )["profile"]
    assert changed["ai_changed_files"] is None
    assert changed["recommended_start"] == "prompt_builder"


def test_entry_profile_uses_reserved_json_key_and_preserves_workflow_and_lifecycle():
    repo = InMemoryProjectRepository()
    project = run(
        repo.create_project(
            USER,
            {
                "status": "active",
                "roadmap": {"phases": []},
                "workflow_artifacts": {
                    "1": {"prompt_builder": {"generated_prompt": "saved"}}
                },
            },
        )
    )
    before = dict(project)
    run(update_entry_profile(repo, USER, {"coding_confidence": "comfortable"}))
    after = run(repo.get_project(USER))
    assert after["workflow_artifacts"]["1"] == before["workflow_artifacts"]["1"]
    assert after["workflow_artifacts"][ENTRY_PROFILE_KEY]["guidance_depth"] == "minimal"
    for key in (
        "status",
        "roadmap",
        "current_phase",
        "task_progress",
        "gate_history_summary",
        "intake_purpose",
        "intake_completed_at",
        "archetype_id",
    ):
        assert after[key] == before[key]


def test_entry_profile_retries_without_losing_a_concurrent_workflow_write():
    class ConcurrentWorkflowRepository(InMemoryProjectRepository):
        injected = False

        async def update_workflow_artifacts_if_current(
            self, user_id, project_id, expected, replacement
        ):
            if not self.injected:
                self.injected = True
                current = await self.get_project(user_id)
                artifacts = copy.deepcopy(current["workflow_artifacts"])
                artifacts["1"]["implementation_import"] = {
                    "source_kind": "manual_summary",
                    "student_summary": "Concurrent saved change",
                    "saved_at": "2026-07-15T16:00:00Z",
                }
                await self.update_project(
                    user_id, project_id, {"workflow_artifacts": artifacts}
                )
            return await super().update_workflow_artifacts_if_current(
                user_id, project_id, expected, replacement
            )

    repo = ConcurrentWorkflowRepository()
    run(
        repo.create_project(
            USER,
            {
                "workflow_artifacts": {
                    "1": {"prompt_builder": {"generated_prompt": "saved"}}
                }
            },
        )
    )
    run(update_entry_profile(repo, USER, {"coding_confidence": "comfortable"}))
    artifacts = run(repo.get_project(USER))["workflow_artifacts"]
    assert artifacts["1"]["prompt_builder"]["generated_prompt"] == "saved"
    assert artifacts["1"]["implementation_import"]["student_summary"] == (
        "Concurrent saved change"
    )
    assert artifacts[ENTRY_PROFILE_KEY]["guidance_depth"] == "minimal"


def test_entry_profile_creation_reuses_the_one_project_intake_architecture():
    repo = InMemoryProjectRepository()
    run(update_entry_profile(repo, USER, {"current_situation": "starting_fresh"}))
    status = run(get_status(repo, USER))
    assert status["started"] is True
    assert status["next_question"] == 1
    assert len(repo._rows) == 1
    run(submit_answer(repo, USER, 1, FIVE_ANSWERS[1]))
    assert len(repo._rows) == 1


def test_malformed_historical_entry_profile_is_ignored_safely():
    repo = InMemoryProjectRepository()
    project = run(
        repo.create_project(
            USER,
            {"workflow_artifacts": {ENTRY_PROFILE_KEY: {"recommended_start": "report"}}},
        )
    )
    assert entry_profile_from_project(project) is None
    assert run(get_entry_profile(repo, USER)) == {"profile": None}


def test_entry_profile_update_does_not_call_a_provider(monkeypatch):
    repo = InMemoryProjectRepository()
    monkeypatch.setattr(
        "app.services.llm_service.get_llm_service",
        lambda: (_ for _ in ()).throw(AssertionError("provider must not be called")),
    )
    profile = run(
        update_entry_profile(
            repo,
            USER,
            {"current_situation": "stuck", "coding_confidence": "new_to_code"},
        )
    )["profile"]
    assert profile["recommended_start"] == "quick_start"


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
        "next_question": 1, "archetype_id": None, "answers": None,
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


def test_status_echoes_stored_answers_by_key():
    repo = InMemoryProjectRepository()
    run(submit_answer(repo, USER, 1, FIVE_ANSWERS[1]))
    run(submit_answer(repo, USER, 2, FIVE_ANSWERS[2]))
    status = run(get_status(repo, USER))
    assert status["answers"]["purpose"] == FIVE_ANSWERS[1]
    assert status["answers"]["scope"] == FIVE_ANSWERS[2]
    # Unanswered questions surface as null, not missing keys.
    assert status["answers"]["stack"] is None
    assert set(status["answers"]) == {
        "purpose", "scope", "stack", "self_assessment", "timeline",
    }


def test_question_one_cannot_be_skipped():
    repo = InMemoryProjectRepository()
    with pytest.raises(IntakeSequenceError, match="expected question 1"):
        run(submit_answer(repo, USER, 2, "some scope"))


def test_questions_out_of_order_are_rejected():
    repo = InMemoryProjectRepository()
    run(submit_answer(repo, USER, 1, FIVE_ANSWERS[1]))
    with pytest.raises(IntakeSequenceError, match="expected question 2"):
        run(submit_answer(repo, USER, 4, "skipping ahead"))


def test_reanswering_before_completion_updates_the_answer():
    repo = InMemoryProjectRepository()
    run(submit_answer(repo, USER, 1, FIVE_ANSWERS[1]))
    run(submit_answer(repo, USER, 2, FIVE_ANSWERS[2]))
    status = run(submit_answer(repo, USER, 1, "Actually: help my team split chores fairly."))
    # An edit never advances or rewinds the sequence.
    assert status["answered_questions"] == [1, 2]
    assert status["next_question"] == 3
    assert status["answers"]["purpose"] == "Actually: help my team split chores fairly."
    assert status["answers"]["scope"] == FIVE_ANSWERS[2]


def test_editing_never_allows_skipping_ahead():
    repo = InMemoryProjectRepository()
    run(submit_answer(repo, USER, 1, FIVE_ANSWERS[1]))
    # Question 3 is unanswered — editing rules don't open it early.
    with pytest.raises(IntakeSequenceError, match="expected question 2"):
        run(submit_answer(repo, USER, 3, "skipping ahead"))


def test_all_five_answered_can_still_be_edited_until_completion():
    repo = InMemoryProjectRepository()
    answer_all_five(repo)
    status = run(submit_answer(repo, USER, 5, "Before my hackathon demo in March."))
    assert status["answered_questions"] == [1, 2, 3, 4, 5]
    assert status["next_question"] is None
    assert status["completed"] is False
    assert status["answers"]["timeline"] == "Before my hackathon demo in March."


def test_completion_classifies_from_edited_answers():
    repo = InMemoryProjectRepository()
    answer_all_five(repo)  # neutral answers → no LLM-core terms
    run(submit_answer(repo, USER, 2, "A chatbot that calls an LLM to answer questions."))
    assert run(complete_intake(repo, USER))["archetype_id"] == 1


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
        "next_question": 1, "archetype_id": None, "answers": None,
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


@pytest.mark.parametrize(
    "meta_language",
    [
        "I use ChatGPT to help write this project.",
        "Codex changed several connected functions and I got confused.",
        "I do not always understand the code Claude generates for me.",
        "Cursor changed multiple files while I was coding.",
    ],
)
def test_ai_tool_usage_language_is_not_an_ai_product_feature(meta_language):
    assert classify_archetype(
        "Help students track homework. " + meta_language,
        "A browser-based assignment tracker using local storage. No AI features. No backend. No database.",
        "Plain HTML, CSS, and JavaScript",
    ) == 3


def test_product_focused_ai_feature_language_still_selects_ai_archetype():
    assert classify_archetype(
        "Help students understand notes",
        "The application calls an LLM to summarize uploaded notes and provides an AI assistant.",
        "HTML and Python",
    ) == 1


def test_explicit_no_ai_feature_wins_over_meta_tool_language_deterministically():
    assert classify_archetype(
        "I use AI to help build a homework tracker.",
        "No AI features. It stores assignments in browser local storage.",
        "HTML, CSS, JavaScript; I use Claude while coding.",
    ) == 3


def test_explicit_exclusion_wins_when_intake_language_conflicts():
    assert classify_archetype(
        "Help readers organize article notes.",
        "No AI features. An earlier idea said the app calls an LLM, but that is excluded now. "
        "The current app saves notes in browser local storage with no backend and no database.",
        "HTML, CSS, and JavaScript",
    ) == 3


def test_plain_local_browser_app_does_not_need_the_studyflow_name():
    assert classify_archetype(
        "Help volunteers keep a personal shift checklist.",
        "A browser app that adds, filters, completes, and deletes shifts using local storage. "
        "No accounts, no backend, no database, and no AI features.",
        "Plain HTML, CSS, JavaScript",
    ) == 3


def test_studyflow_completion_has_an_accurate_student_visible_label():
    repo = InMemoryProjectRepository()
    answers = {
        1: "Help students keep homework and due dates organized.",
        2: (
            "A browser-based homework tracker where students add assignments with a title, "
            "subject, and due date; mark them complete; filter and delete them; and preserve "
            "them through browser local storage. No accounts. No backend. No database. "
            "No AI features. No notifications. No calendar integration."
        ),
        3: "Plain HTML, CSS, JavaScript",
        4: "Honestly, not really",
        5: "Two weeks",
    }
    for number, answer in answers.items():
        run(submit_answer(repo, USER, number, answer))
    result = run(complete_intake(repo, USER))
    assert result == {
        "completed": True,
        "archetype_id": 3,
        "archetype_name": "Browser App",
    }
