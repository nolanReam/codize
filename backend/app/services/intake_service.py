"""Intake engine (Milestone 6).

The spec fixes the intake flow: exactly five mandatory conversational
questions, answered sequentially, question 1 verbatim and unskippable. Answers
are stored on the student's `projects` row (the five intake_* columns —
docs/db/schema.md). Completion requires all five answers and triggers
archetype classification into exactly one of the three archetypes.

Classification here is the deterministic fallback: the spec's real
classification is a temperature-0 LLM call (later milestone, via the M7
llm_service + a live provider key). The seam is `classify_archetype` — the future
LLM call replaces `_derive_classification_signals`; the tiebreaker mapping
itself (`template_service.resolve_archetype`) is fixed and never changes.
"""

import re
from datetime import datetime, timezone

from app.services import template_service
from app.services.project_repository import ProjectRepository

# The five mandatory questions, verbatim from the master spec. Question 1 is
# the Yeager purpose framing — never "What do you want to build?". Exactly
# five; do not add a sixth.
QUESTIONS: tuple[dict, ...] = (
    {
        "number": 1,
        "key": "purpose",
        "text": "What problem do you want to solve, and who does solving it help?",
    },
    {
        "number": 2,
        "key": "scope",
        "text": "Describe what the app does in plain language, like you're explaining it to a friend.",
    },
    {
        "number": 3,
        "key": "stack",
        "text": "What languages or frameworks are you most comfortable with?",
    },
    {
        "number": 4,
        "key": "self_assessment",
        "text": "On a scale of honest to honest: how well do you understand the code AI generates for you right now?",
        "options": ["I can usually explain it", "Sometimes, depends", "Honestly, not really"],
    },
    {
        "number": 5,
        "key": "timeline",
        "text": "What's your rough deadline for having something working?",
    },
)

# Question number → projects column (schema fixed in M2).
ANSWER_COLUMNS = {
    1: "intake_purpose",
    2: "intake_scope",
    3: "intake_stack",
    4: "intake_self_assessment",
    5: "intake_timeline",
}

# Question number → the question's stable key (purpose, scope, …). Lets the
# status response return answers keyed the way the frontend reads them.
ANSWER_KEYS = {q["number"]: q["key"] for q in QUESTIONS}

MAX_ANSWER_LENGTH = 4000

ARCHETYPE_NAMES = {aid: name for aid, name in template_service.EXPECTED_TEMPLATES.values()}


class IntakeError(Exception):
    """Base for controlled intake errors; messages are safe client strings."""


class InvalidAnswerError(IntakeError):
    """Answer fails boundary validation (empty, too long)."""


class IntakeSequenceError(IntakeError):
    """Answer arrived out of the mandatory 1→5 order."""


class IntakeIncompleteError(IntakeError):
    """Completion requested before all five answers exist."""


class IntakeAlreadyCompletedError(IntakeError):
    """Intake for this project is already completed."""


def get_questions() -> list[dict]:
    return [dict(q) for q in QUESTIONS]


def normalize_answer(raw: str) -> str:
    answer = raw.strip()
    if not answer:
        raise InvalidAnswerError("Answer cannot be empty.")
    if len(answer) > MAX_ANSWER_LENGTH:
        raise InvalidAnswerError(f"Answer is too long (max {MAX_ANSWER_LENGTH} characters).")
    return answer


def next_question_number(project: dict | None) -> int | None:
    """First unanswered question, or None when all five are answered.
    Sequential submission means answers can never have gaps."""
    if project is None:
        return 1
    for number, column in ANSWER_COLUMNS.items():
        if not project.get(column):
            return number
    return None


def _build_status(project: dict | None) -> dict:
    nxt = next_question_number(project)
    # The student's own stored answers, keyed by question key (purpose, scope,
    # …). Owner-scoped data the frontend echoes back in the intake transcript
    # and the cockpit "mission" — never scores, prompts, or derived state.
    answers = (
        None
        if project is None
        else {ANSWER_KEYS[n]: project.get(col) for n, col in ANSWER_COLUMNS.items()}
    )
    return {
        "started": project is not None,
        "completed": bool(project and project.get("intake_completed_at")),
        "answered_questions": [] if project is None else [
            n for n, col in ANSWER_COLUMNS.items() if project.get(col)
        ],
        "next_question": nxt,
        "archetype_id": project.get("archetype_id") if project else None,
        "answers": answers,
    }


async def get_status(repo: ProjectRepository, user_id: str) -> dict:
    return _build_status(await repo.get_project(user_id))


async def submit_answer(repo: ProjectRepository, user_id: str, question_number: int, raw_answer: str) -> dict:
    answer = normalize_answer(raw_answer)
    project = await repo.get_project(user_id)
    if project and project.get("intake_completed_at"):
        raise IntakeAlreadyCompletedError("Intake is already completed.")
    expected = next_question_number(project)
    if expected is None:
        raise IntakeSequenceError("All five intake questions are already answered.")
    if question_number != expected:
        raise IntakeSequenceError(
            f"Questions are answered in order; expected question {expected}."
        )
    if project is None:
        project = await repo.create_project(user_id, {ANSWER_COLUMNS[1]: answer})
    else:
        project = await repo.update_project(
            user_id, project["id"], {ANSWER_COLUMNS[question_number]: answer}
        )
    return _build_status(project)


async def complete_intake(repo: ProjectRepository, user_id: str) -> dict:
    project = await repo.get_project(user_id)
    if project and project.get("intake_completed_at"):
        raise IntakeAlreadyCompletedError("Intake is already completed.")
    missing = next_question_number(project)
    if missing is not None:
        raise IntakeIncompleteError(
            f"Intake is not complete: question {missing} is unanswered."
        )
    archetype_id = classify_archetype(
        project["intake_purpose"], project["intake_scope"], project["intake_stack"]
    )
    await repo.update_project(
        user_id,
        project["id"],
        {
            "archetype_id": archetype_id,
            "intake_completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {
        "completed": True,
        "archetype_id": archetype_id,
        "archetype_name": ARCHETYPE_NAMES[archetype_id],
    }


# --- classification ------------------------------------------------------------

_LLM_CORE_TERMS = (
    "llm", "llms", "language model", "gpt", "chatgpt", "claude", "openai",
    "anthropic", "gemini", "chatbot", "ai",
)
_FRONTEND_DB_TERMS = (
    "frontend", "front-end", "front end", "react", "next.js", "nextjs", "vue",
    "svelte", "angular", "html", "css", "website", "web app", "webapp", "ui",
    "dashboard", "database", "db", "postgres", "postgresql", "mysql", "sqlite",
    "mongodb", "supabase", "full-stack", "full stack", "fullstack",
)


def _mentions_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(t)}\b", text) for t in terms)


def _derive_classification_signals(text: str) -> tuple[bool, bool]:
    """Deterministic keyword fallback for the two tiebreaker booleans. The
    temperature-0 LLM classification call replaces exactly this function."""
    lowered = text.lower()
    return _mentions_any(lowered, _LLM_CORE_TERMS), _mentions_any(lowered, _FRONTEND_DB_TERMS)


def classify_archetype(purpose: str, scope: str, stack: str) -> int:
    """Exactly one of archetypes 1/2/3, never a fourth: the return value comes
    from the spec's fixed tiebreaker, whatever produced the signals."""
    llm_core, frontend_or_db = _derive_classification_signals(f"{purpose} {scope} {stack}")
    return template_service.resolve_archetype(llm_core, frontend_or_db)
