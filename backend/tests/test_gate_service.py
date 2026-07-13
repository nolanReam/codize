"""Interrogation Gate service tests — eligibility, cooldown, anchor rules,
turn sequencing, strict evaluation parsing, phase advancement, and score
hiding, against the in-memory fakes and a scripted LLM.

Model *behavior* (textbook answers failing, injection resistance, weakest-
criterion probing) is covered by the live adversarial record in
docs/prebuild/adversarial_tests.md; these tests pin the deterministic runtime
rules around those calls.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.services import gate_service, roadmap_service
from app.services.gate_service import (
    ANCHOR_PROMPT,
    AnchorInvalidError,
    GateAlreadyPassedError,
    GateCooldownError,
    GateGenerationError,
    GateInProgressError,
    GateNotReadyError,
    GateOutOfOrderError,
    GateSessionNotFoundError,
    clean_gate_question,
    evaluate_gate,
    generate_followup,
    get_current_gate,
    parse_evaluation,
    sanitize_gate_question,
    start_gate,
    submit_anchor,
)
from app.services.llm_service import LLMError, LLMService, StubProvider
from tests.fakes import (
    InMemoryGateSessionRepository,
    InMemoryProjectRepository,
    InMemoryUnlockRepository,
    ScriptedLLM,
)

USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_USER = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

INTAKE_FIELDS = {
    "intake_purpose": "Help my volleyball league track scores so organizers stop using paper.",
    "intake_scope": "A REST backend exposing match stats through HTTP endpoints.",
    "intake_stack": "Python and FastAPI",
    "intake_self_assessment": "Sometimes, depends",
    "intake_timeline": "About six weeks",
}

ANCHOR = "I built a `matches` table with a `user_id` column and a create_match() handler."

PASS_VERDICT = '{"verdict": "PASS", "reason": "All three conditions satisfied.", "score": 8}'
FAIL_VERDICT = '{"verdict": "FAIL", "reason": "No implementation specificity.", "score": 3}'


def run(coro):
    return asyncio.run(coro)


def seed_active_project(repo, user=USER, archetype_id=2):
    fields = {**INTAKE_FIELDS,
              "intake_completed_at": "2026-07-02T00:00:00+00:00",
              "archetype_id": archetype_id}
    run(repo.create_project(user, fields))
    run(roadmap_service.generate_roadmap(repo, LLMService([StubProvider()]), user))
    return run(repo.get_project(user))


def make_repos(user=USER):
    repo = InMemoryProjectRepository()
    gates = InMemoryGateSessionRepository()
    project = seed_active_project(repo, user)
    return repo, gates, project


def run_full_gate(repo, gates, user=USER, verdict=PASS_VERDICT, unlocks=None):
    """Drive one complete gate: anchor → q1/a1 → q2/a2 → q3/a3 → evaluation."""
    started = run(start_gate(repo, gates, user))
    sid = started["gate_session_id"]
    llm = ScriptedLLM(["Q1: why user_id?", "Q2: and the edge case?",
                       "Q3: what if matches were shared?", verdict])
    run(submit_anchor(repo, gates, llm, user, sid, ANCHOR))
    run(generate_followup(repo, gates, llm, user, sid, 2, "Because ownership lives on the row."))
    run(generate_followup(repo, gates, llm, user, sid, 3, "WITH CHECK still blocks writes."))
    result = run(evaluate_gate(repo, gates, unlocks or InMemoryUnlockRepository(), llm, user, sid,
                               "My matches table would need a join table; create_match() changes."))
    return sid, result, llm


# --- eligibility -----------------------------------------------------------------

def test_cannot_start_gate_without_active_project():
    repo, gates = InMemoryProjectRepository(), InMemoryGateSessionRepository()
    with pytest.raises(GateNotReadyError):
        run(start_gate(repo, gates, USER))
    # intake done but no roadmap/status
    run(repo.create_project(USER, {**INTAKE_FIELDS,
                                   "intake_completed_at": "2026-07-02T00:00:00+00:00",
                                   "archetype_id": 2}))
    with pytest.raises(GateNotReadyError):
        run(start_gate(repo, gates, USER))
    with pytest.raises(GateNotReadyError):
        run(get_current_gate(repo, gates, USER))


def test_start_gate_creates_session_with_anchor_prompt():
    repo, gates, project = make_repos()
    started = run(start_gate(repo, gates, USER))
    assert started["phase"] == 1
    assert started["anchor_prompt"] == ANCHOR_PROMPT
    session = run(gates.get_session(USER, started["gate_session_id"]))
    assert session["project_id"] == project["id"]
    assert session["phase_id"] == 1
    assert session["anchor_statement"] is None


def test_start_refused_while_a_session_is_in_progress():
    repo, gates, _ = make_repos()
    run(start_gate(repo, gates, USER))
    with pytest.raises(GateInProgressError):
        run(start_gate(repo, gates, USER))


# --- anchor rules ----------------------------------------------------------------

def test_turns_refused_before_anchor():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["should never be called"])
    for turn in (2, 3):
        with pytest.raises(GateOutOfOrderError):
            run(generate_followup(repo, gates, llm, USER, sid, turn, "answer"))
    with pytest.raises(GateOutOfOrderError):
        run(evaluate_gate(repo, gates, InMemoryUnlockRepository(), llm, USER, sid, "answer"))
    assert llm.calls == []  # no LLM call happens before the anchor exists


def test_generic_anchor_rejected_without_llm_call():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["should never be called"])
    for bad in ("   ", "I built the auth system and it works"):
        with pytest.raises(AnchorInvalidError):
            run(submit_anchor(repo, gates, llm, USER, sid, bad))
    assert llm.calls == []
    assert run(gates.get_session(USER, sid))["anchor_statement"] is None


def test_llm_rejected_weak_anchor_is_422_and_stores_nothing():
    # "users table" is a weak match (element type, no code-shaped identifier) —
    # the model's re-validation stays authoritative for these.
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["ANCHOR_REJECTED: Name a concrete element from your implementation."])
    with pytest.raises(AnchorInvalidError, match="concrete element"):
        run(submit_anchor(repo, gates, llm, USER, sid, "I set up the users table for my league"))
    session = run(gates.get_session(USER, sid))
    assert session["anchor_statement"] is None and session["turns"] == []


def test_model_rejection_of_strong_anchor_is_retryable_never_a_422():
    # M13E.2 pilot fix: the tester's anchor named `likes_score` and the model
    # still replied ANCHOR_REJECTED. A strong (code-shaped) anchor is validated
    # server-side; a model rejection is a generation failure (502, retryable),
    # never "your anchor is invalid".
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    tester_anchor = (
        "i built a variable that stores likes and a function to update them "
        "using some advanced python stuff. the variable is called likes_score"
    )
    llm = ScriptedLLM([
        "ANCHOR_REJECTED: You must name at least one concrete element.",
        "Why did you make likes_score a variable instead of a database column?",
    ])
    with pytest.raises(GateGenerationError):
        run(submit_anchor(repo, gates, llm, USER, sid, tester_anchor))
    session = run(gates.get_session(USER, sid))
    assert session["anchor_statement"] is None and session["turns"] == []
    # The prompt told the model the anchor was pre-validated.
    assert "already been validated server-side" in llm.calls[0][0]
    # Retry succeeds with a clean question.
    out = run(submit_anchor(repo, gates, llm, USER, sid, tester_anchor))
    assert out["question"].startswith("Why did you make likes_score")


@pytest.mark.parametrize("anchor", [
    # Realistic student phrasing from the pilot (M13E.2) — all must pass the
    # deterministic check AND count as strong (no model re-validation).
    "i built a variable that stores likes and a function to update them using "
    "some advanced python stuff. the variable is called likes_score",
    "variable called likes_score",
    "variable named likes_score",
    "the variable is called likes_score",
    "`likes_score`",
    "function called update_likes_score",
    "function called update_likes_score()",
    "database field called likes_score",
    "field named likes_score",
    "tasks.user_id",
    "app/models.py",
    "routes/tasks.py",
    "a variable called score",
])
def test_realistic_student_anchors_are_accepted_and_strong(anchor):
    assert gate_service.anchor_names_concrete_element(anchor)
    assert gate_service.anchor_has_strong_element(anchor)


def test_weak_anchor_still_goes_through_model_revalidation():
    # An element type with no code-shaped name is concrete enough to reach the
    # model, but not strong — the re-validation tail must stay in the prompt.
    anchor = "I set up the users table for my league"
    assert gate_service.anchor_names_concrete_element(anchor)
    assert not gate_service.anchor_has_strong_element(anchor)
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["Why did you choose a separate users table?"])
    run(submit_anchor(repo, gates, llm, USER, sid, anchor))
    assert "Apply the Step 1 validation rules" in llm.calls[0][0]


def test_anchor_help_message_shows_concrete_examples():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["should never be called"])
    with pytest.raises(AnchorInvalidError) as err:
        run(submit_anchor(repo, gates, llm, USER, sid, "I built the auth system and it works"))
    # The improved copy names exact examples a student can copy the shape of.
    assert "likes_score" in str(err.value)
    assert "app/models.py" in str(err.value)
    assert llm.calls == []


def test_anchor_stored_with_session_and_turn1_uses_targets_and_anchor():
    repo, gates, project = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["Why did you put user_id on matches?"])
    out = run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    assert out == {"gate_session_id": sid, "turn": 1,
                   "question": "Why did you put user_id on matches?"}

    prompt, temperature = llm.calls[0]
    assert temperature == 0.3
    phase1 = project["roadmap"]["phases"][0]
    for target in phase1["explanation_gate_targets"]:
        assert target in prompt
    assert ANCHOR in prompt
    assert INTAKE_FIELDS["intake_purpose"] in prompt
    assert INTAKE_FIELDS["intake_stack"] in prompt

    session = run(gates.get_session(USER, sid))
    assert session["anchor_statement"] == ANCHOR
    [stored] = session["turns"]
    assert stored["turn"] == 1
    assert stored["question"] == "Why did you put user_id on matches?"
    assert stored["answer"] is None
    # M14B: grounding metadata is stored with the turn (backend-internal —
    # the client transcript view whitelists turn/question/answer only).
    assert "user_id" in stored["grounding"]["grounding_terms"]


# --- turn sequencing -------------------------------------------------------------

def test_turn2_and_turn3_prompts_carry_the_transcript():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["Q1?", "Q2?", "Q3?"])
    run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    run(generate_followup(repo, gates, llm, USER, sid, 2, "A1 about my matches table"))
    run(generate_followup(repo, gates, llm, USER, sid, 3, "A2 about WITH CHECK"))

    t2_prompt, t2_temp = llm.calls[1]
    assert t2_temp == 0.3
    assert "weakest" in t2_prompt  # gate_turn_2.md probes the weakest criterion
    assert ANCHOR in t2_prompt and "Q1?" in t2_prompt and "A1 about my matches table" in t2_prompt

    t3_prompt, t3_temp = llm.calls[2]
    assert t3_temp == 0.3
    assert "hypothetical" in t3_prompt  # gate_turn_3.md generates the fresh hypothetical
    for fragment in (ANCHOR, "Q1?", "A1 about my matches table", "Q2?", "A2 about WITH CHECK"):
        assert fragment in t3_prompt

    turns = run(gates.get_session(USER, sid))["turns"]
    assert [t["turn"] for t in turns] == [1, 2, 3]
    assert turns[0]["answer"] == "A1 about my matches table"
    assert turns[1]["answer"] == "A2 about WITH CHECK"
    assert turns[2]["answer"] is None


def test_out_of_order_turns_are_refused():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["Q1?", "Q2?"])
    run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    with pytest.raises(GateOutOfOrderError):  # turn3 before turn2
        run(generate_followup(repo, gates, llm, USER, sid, 3, "answer"))
    with pytest.raises(GateOutOfOrderError):  # anchor resubmission
        run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    with pytest.raises(GateOutOfOrderError):  # evaluate before turn 3
        run(evaluate_gate(repo, gates, InMemoryUnlockRepository(), llm, USER, sid, "answer"))
    run(generate_followup(repo, gates, llm, USER, sid, 2, "answer"))
    with pytest.raises(GateOutOfOrderError):  # turn2 twice
        run(generate_followup(repo, gates, llm, USER, sid, 2, "answer"))


def test_llm_failure_mid_turn_stores_nothing_and_is_retryable():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["Q1?", LLMError("gemini down"), "Q2 retry?"])
    run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    with pytest.raises(GateGenerationError):
        run(generate_followup(repo, gates, llm, USER, sid, 2, "my answer"))
    turns = run(gates.get_session(USER, sid))["turns"]
    assert len(turns) == 1 and turns[0]["answer"] is None  # unchanged
    out = run(generate_followup(repo, gates, llm, USER, sid, 2, "my answer"))
    assert out["question"] == "Q2 retry?"


# --- evaluation ------------------------------------------------------------------

def test_evaluation_uses_temperature_zero_and_full_transcript():
    repo, gates, _ = make_repos()
    sid, result, llm = run_full_gate(repo, gates)
    eval_prompt, eval_temp = llm.calls[3]
    assert eval_temp == 0.0
    assert "Structural Identification" in eval_prompt
    assert ANCHOR in eval_prompt
    assert "My matches table would need a join table" in eval_prompt


def test_pass_advances_current_phase_and_updates_history():
    repo, gates, _ = make_repos()
    sid, result, _ = run_full_gate(repo, gates, verdict=PASS_VERDICT)
    assert result["verdict"] == "PASS"
    assert result["current_phase"] == 2
    assert "score" not in result

    project = run(repo.get_project(USER))
    assert project["current_phase"] == 2
    assert "Phase 1" in project["gate_history_summary"]
    assert "first attempt" in project["gate_history_summary"]

    session = run(gates.get_session(USER, sid))
    assert session["passed"] is True
    assert session["passed_at"] is not None and session["failed_at"] is None
    assert session["score"] == 8  # stored for M10, never returned
    assert session["reason"] == "All three conditions satisfied."


def test_fail_does_not_advance_and_sets_cooldown():
    repo, gates, _ = make_repos()
    sid, result, _ = run_full_gate(repo, gates, verdict=FAIL_VERDICT)
    assert result["verdict"] == "FAIL"
    assert result["current_phase"] == 1
    assert result["cooldown_seconds"] == 1800
    assert "score" not in result

    project = run(repo.get_project(USER))
    assert project["current_phase"] == 1
    assert project.get("gate_history_summary") is None

    session = run(gates.get_session(USER, sid))
    assert session["passed"] is False
    assert session["failed_at"] is not None and session["passed_at"] is None

    with pytest.raises(GateCooldownError) as exc:  # immediate retry blocked
        run(start_gate(repo, gates, USER))
    assert 0 < exc.value.retry_after_seconds <= 1800


def test_expired_cooldown_allows_retry_and_pass_counts_attempts():
    repo, gates, _ = make_repos()
    sid, _, _ = run_full_gate(repo, gates, verdict=FAIL_VERDICT)
    expired = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    run(gates.update_session(USER, sid, {"failed_at": expired}))

    _, result, _ = run_full_gate(repo, gates, verdict=PASS_VERDICT)
    assert result["verdict"] == "PASS"
    project = run(repo.get_project(USER))
    assert project["current_phase"] == 2
    assert "attempt 2" in project["gate_history_summary"]


def test_final_phase_pass_does_not_advance_past_the_end():
    repo, gates, project = make_repos()
    total = len(project["roadmap"]["phases"])
    run(repo.update_project(USER, project["id"], {"current_phase": total}))
    _, result, _ = run_full_gate(repo, gates, verdict=PASS_VERDICT)
    assert result["verdict"] == "PASS"
    assert result["current_phase"] == total
    assert run(repo.get_project(USER))["current_phase"] == total
    # the final phase's gate now reports passed
    view = run(get_current_gate(repo, gates, USER))
    assert view["state"] == "passed"
    with pytest.raises(GateAlreadyPassedError):
        run(start_gate(repo, gates, USER))


def test_malformed_evaluator_output_is_rejected_and_stores_nothing():
    repo, gates, _ = make_repos()
    started = run(start_gate(repo, gates, USER))
    sid = started["gate_session_id"]
    llm = ScriptedLLM(["Q1?", "Q2?", "Q3?", "The student did great! PASS I think."])
    run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    run(generate_followup(repo, gates, llm, USER, sid, 2, "a1"))
    run(generate_followup(repo, gates, llm, USER, sid, 3, "a2"))
    with pytest.raises(GateGenerationError):
        run(evaluate_gate(repo, gates, InMemoryUnlockRepository(), llm, USER, sid, "a3"))
    session = run(gates.get_session(USER, sid))
    assert session["passed"] is None and session["score"] is None
    assert session["turns"][2]["answer"] is None  # retryable


@pytest.mark.parametrize("raw", [
    "not json at all",
    '{"verdict": "MAYBE", "reason": "hmm", "score": 5}',
    '{"verdict": "PASS", "reason": "", "score": 5}',
    '{"verdict": "PASS", "score": 5}',
    '{"verdict": "PASS", "reason": "ok", "score": 11}',
    '{"verdict": "PASS", "reason": "ok", "score": -1}',
    '{"verdict": "PASS", "reason": "ok", "score": 7.5}',
    '{"verdict": "PASS", "reason": "ok", "score": true}',
    '["PASS", "ok", 7]',
])
def test_parse_evaluation_rejects_malformed(raw):
    with pytest.raises(GateGenerationError):
        parse_evaluation(raw)


def test_parse_evaluation_accepts_strict_and_fenced_json():
    assert parse_evaluation(PASS_VERDICT)["verdict"] == "PASS"
    fenced = f"```json\n{FAIL_VERDICT}\n```"
    parsed = parse_evaluation(fenced)
    assert parsed == {"verdict": "FAIL", "reason": "No implementation specificity.", "score": 3}


# --- question cleanliness (M13C.2B) ----------------------------------------------

CLEAN_QUESTIONS = [
    "Why did you put user_id on the matches table?",
    "Explain how your current implementation handles user ownership.",
    "Walk me through what happens when two organizers call create_match() at once.",
    "You said sessions live in your `user_sessions` table. Walk me through why you "
    "stored them there rather than in a JWT, and what that means for your app.",
    # Legitimate turn-2 acknowledgement phrasing from gate_turn_2.md — must survive.
    "Good — you covered the happy path. Now explain what happens in the edge case "
    "where two writers hit the same row.",
    # A question that legitimately references the anchor and ends with "?".
    "The `create_match` handler you named — what breaks if two requests race?",
]


@pytest.mark.parametrize("q", CLEAN_QUESTIONS)
def test_clean_questions_pass_through_unchanged(q):
    assert sanitize_gate_question(q) == q
    assert clean_gate_question(q) == q


@pytest.mark.parametrize("raw,expected", [
    # The exact leak seen in the M13C.2 smoke: validity note + inline hand-off.
    (
        "The student's reply is a valid anchor. Here is the Turn 1 question: "
        "Why did you put user_id on the matches table?",
        "Why did you put user_id on the matches table?",
    ),
    # Hand-off with no space after the colon still recovers the question.
    (
        "Here is the Turn 1 question:Why did you put user_id on the matches table?",
        "Why did you put user_id on the matches table?",
    ),
    # "valid anchor" style leakage as a leading sentence.
    (
        "Valid anchor detected. What would break if create_match() ran twice?",
        "What would break if create_match() ran twice?",
    ),
    # Rubric / evaluator language must not reach the student.
    (
        "According to the rubric, specificity is weakest. Tell me exactly how your "
        "matches table enforces ownership.",
        "Tell me exactly how your matches table enforces ownership.",
    ),
    # Internal step/instruction fragments.
    (
        "Step 2 — the Turn 1 question. Explain why you stored user_id on the row.",
        "Explain why you stored user_id on the row.",
    ),
    (
        "I will now ask the question. Why does the policy come before the frontend?",
        "Why does the policy come before the frontend?",
    ),
    # Code-fence / quote wrapping is unwrapped.
    (
        '"Why did you put user_id on the matches table?"',
        "Why did you put user_id on the matches table?",
    ),
    (
        "```\nWhy did you put user_id on the matches table?\n```",
        "Why did you put user_id on the matches table?",
    ),
    # M13E.2 — the exact leak pattern from the pilot screenshot: reasoning
    # commentary, an "I need to formulate" plan, and a quoted hand-off.
    (
        "Therefore, it is a valid anchor. Now I need to formulate the Turn 1 "
        'question... Let\'s craft the question: "You mentioned building a '
        '`likes_score` variable. Can you explain why you chose that?"',
        "You mentioned building a `likes_score` variable. Can you explain why "
        "you chose that?",
    ),
    # Same family, sentence-by-sentence (no inline hand-off colon quote).
    (
        "Therefore, it is a valid anchor. Now, I need to formulate the Turn 1 "
        "question. Why does update_likes_score() write to likes_score directly?",
        "Why does update_likes_score() write to likes_score directly?",
    ),
    # Markdown section labels are dropped whole.
    (
        "**Question Formulation**\nWhat happens to likes_score if two users "
        "click like at the same time?",
        "What happens to likes_score if two users click like at the same time?",
    ),
    (
        "### Turn 1 Question\nWalk me through what update_likes_score() does "
        "step by step.",
        "Walk me through what update_likes_score() does step by step.",
    ),
])
def test_meta_preamble_is_stripped(raw, expected):
    assert sanitize_gate_question(raw) == expected
    assert clean_gate_question(raw) == expected


@pytest.mark.parametrize("raw", [
    "",
    "   ",
    "The student must demonstrate ownership understanding.",
    "According to the evaluator criteria, this should test specificity.",
    "Here is a question that satisfies the rubric requirements.",
    # M13E.2 hard-leak backstop: rubric/internal vocabulary embedded INSIDE a
    # question-shaped output is rejected (retryable), never shown.
    "Given the Gate Targets, how does your likes_score variable handle a tie?",
    "Since this is a valid anchor, what breaks if likes_score goes negative?",
    "To probe Specificity: which exact function updates likes_score?",
])
def test_all_meta_output_is_rejected_and_retryable(raw):
    with pytest.raises(GateGenerationError):
        clean_gate_question(raw)


def test_leaked_turn1_question_is_cleaned_before_storage():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM([
        "The student's reply is a valid anchor. Here is the Turn 1 question: "
        "Why did you put user_id on the matches table?"
    ])
    out = run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    assert out["question"] == "Why did you put user_id on the matches table?"
    assert "valid anchor" not in out["question"].lower()
    stored = run(gates.get_session(USER, sid))["turns"][0]["question"]
    assert stored == "Why did you put user_id on the matches table?"


def test_leaked_followup_question_is_cleaned_before_storage():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM([
        "Why did you put user_id on matches?",
        "According to the rubric, specificity is weakest. Tell me exactly what "
        "happens when create_match() is called without a user_id.",
    ])
    run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    out = run(generate_followup(repo, gates, llm, USER, sid, 2, "Because ownership lives on the row."))
    assert out["question"].startswith("Tell me exactly what happens")
    assert "rubric" not in out["question"].lower()


def test_all_meta_turn1_output_stores_nothing_and_is_retryable():
    repo, gates, _ = make_repos()
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM([
        "The student must demonstrate ownership understanding of the schema.",
        "Why did you put user_id on the matches table?",
    ])
    with pytest.raises(GateGenerationError):
        run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    session = run(gates.get_session(USER, sid))
    assert session["anchor_statement"] is None and session["turns"] == []
    # Retry with a clean question succeeds and stores it.
    out = run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    assert out["question"] == "Why did you put user_id on the matches table?"


def test_sanitizer_does_not_touch_the_evaluator_verdict():
    # The evaluator output is JSON parsed by parse_evaluation, never routed
    # through the question sanitizer — a PASS/FAIL still round-trips intact.
    repo, gates, _ = make_repos()
    _, result, _ = run_full_gate(repo, gates, verdict=PASS_VERDICT)
    assert result["verdict"] == "PASS"
    assert result["reason"] == "All three conditions satisfied."


# --- ownership -------------------------------------------------------------------

def test_wrong_user_cannot_access_anothers_gate_session():
    repo, gates, _ = make_repos(USER)
    seed_active_project(repo, OTHER_USER)
    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["should never be reached"])
    with pytest.raises(GateSessionNotFoundError):
        run(submit_anchor(repo, gates, llm, OTHER_USER, sid, ANCHOR))
    with pytest.raises(GateSessionNotFoundError):
        run(generate_followup(repo, gates, llm, OTHER_USER, sid, 2, "a"))
    with pytest.raises(GateSessionNotFoundError):
        run(evaluate_gate(repo, gates, InMemoryUnlockRepository(), llm, OTHER_USER, sid, "a"))
    assert llm.calls == []


# --- current gate view -----------------------------------------------------------

def test_get_current_gate_states_never_include_score():
    repo, gates, _ = make_repos()
    view = run(get_current_gate(repo, gates, USER))
    assert view["state"] == "not_started" and view["anchor_prompt"] == ANCHOR_PROMPT

    sid = run(start_gate(repo, gates, USER))["gate_session_id"]
    llm = ScriptedLLM(["Q1?"])
    view = run(get_current_gate(repo, gates, USER))
    assert view["state"] == "in_progress" and view["next_action"] == "turn1"

    run(submit_anchor(repo, gates, llm, USER, sid, ANCHOR))
    view = run(get_current_gate(repo, gates, USER))
    assert view["next_action"] == "turn2"
    assert view["anchor_statement"] == ANCHOR
    assert view["turns"][0]["question"] == "Q1?"
    assert "score" not in str(view)

    llm.responses.extend(["Q2?", "Q3?", FAIL_VERDICT])
    run(generate_followup(repo, gates, llm, USER, sid, 2, "a1"))
    run(generate_followup(repo, gates, llm, USER, sid, 3, "a2"))
    run(evaluate_gate(repo, gates, InMemoryUnlockRepository(), llm, USER, sid, "a3"))
    view = run(get_current_gate(repo, gates, USER))
    assert view["state"] == "cooldown"
    assert 0 < view["cooldown_seconds_remaining"] <= 1800
    assert "score" not in view and "3" not in str(view.get("reason"))
