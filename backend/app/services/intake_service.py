"""Intake engine (Milestone 6).

The spec fixes the intake flow: exactly five mandatory conversational
questions, answered sequentially, question 1 verbatim and unskippable. Answers
are stored on the student's `projects` row (the five intake_* columns —
docs/db/schema.md). Completion requires all five answers and triggers
archetype classification into exactly one of the three archetypes. Until
completion, an already-answered question may be revised (M13E.1) —
classification always runs on the final stored answers.

Classification here is the deterministic fallback: the spec's real
classification is a temperature-0 LLM call (later milestone, via the M7
llm_service + a live provider key). The seam is `classify_archetype` — the future
LLM call replaces `_derive_classification_signals`; the tiebreaker mapping
itself (`template_service.resolve_archetype`) is fixed and never changes.
"""

from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.intake import EntryProfileView
from app.services import project_capability_service, template_service
from app.services.project_repository import ProjectRepository, RepositoryError

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

# M17 keeps adaptive entry beside (not inside) the phase-scoped workflow
# records. Existing readers select only numeric phase keys, so this reserved
# top-level key cannot become a workflow section or affect N/5 progress.
ENTRY_PROFILE_KEY = "_entry_profile"
_ENTRY_PROFILE_WRITE_ATTEMPTS = 3

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


class InvalidEntryProfileError(IntakeError):
    """Adaptive-entry choices are inconsistent or invalid."""


_GUIDANCE_DEPTH = {
    "new_to_code": "more",
    "know_basics": "standard",
    "comfortable": "minimal",
}


def _recommend_start(
    current_situation: str | None, ai_changed_files: str | None
) -> str | None:
    if current_situation == "starting_fresh":
        return "prompt_builder"
    if current_situation == "stuck":
        return "quick_start"
    if current_situation == "already_building":
        if ai_changed_files == "not_yet":
            return "prompt_builder"
        if ai_changed_files in {"yes", "unsure"}:
            return "implementation_import"
    return None


def _profile_view(
    *,
    current_situation: str | None,
    coding_confidence: str | None,
    ai_changed_files: str | None,
    updated_at: str,
) -> dict:
    if current_situation != "already_building":
        ai_changed_files = None
    recommended_start = _recommend_start(current_situation, ai_changed_files)
    completed = bool(current_situation and coding_confidence and recommended_start)
    return {
        "schema_version": "1.0",
        "current_situation": current_situation,
        "coding_confidence": coding_confidence,
        "ai_changed_files": ai_changed_files,
        "completed": completed,
        "recommended_start": recommended_start if completed else None,
        "guidance_depth": _GUIDANCE_DEPTH.get(coding_confidence, "standard"),
        "recovery_emphasis": current_situation == "stuck",
        "updated_at": updated_at,
    }


def entry_profile_from_project(project: dict | None) -> dict | None:
    """Return a validated, server-rederived view; malformed history is absent.

    Re-deriving the recommendation prevents persisted derived fields from ever
    becoming lifecycle authority. The stored student choices remain the only
    inputs.
    """
    artifacts = project.get("workflow_artifacts") if project else None
    raw = artifacts.get(ENTRY_PROFILE_KEY) if isinstance(artifacts, dict) else None
    if not isinstance(raw, dict):
        return None
    try:
        stored = EntryProfileView.model_validate(raw)
    except ValidationError:
        return None
    view = _profile_view(
        current_situation=stored.current_situation,
        coding_confidence=stored.coding_confidence,
        ai_changed_files=stored.ai_changed_files,
        updated_at=stored.updated_at,
    )
    try:
        return EntryProfileView.model_validate(view).model_dump(mode="json")
    except ValidationError:
        return None


async def get_entry_profile(repo: ProjectRepository, user_id: str) -> dict:
    return {"profile": entry_profile_from_project(await repo.get_project(user_id))}


async def update_entry_profile(
    repo: ProjectRepository, user_id: str, updates: dict
) -> dict:
    """Merge student choices and patch only workflow_artifacts.

    This may create the user's existing one-project row before Q1. It never
    writes intake answers, classification, roadmap, status, phase, workflow
    sections, drafts, or downstream records.
    """
    project = await repo.get_project(user_id)
    for _attempt in range(_ENTRY_PROFILE_WRITE_ATTEMPTS):
        current = entry_profile_from_project(project)
        situation = updates.get(
            "current_situation", current.get("current_situation") if current else None
        )
        confidence = updates.get(
            "coding_confidence", current.get("coding_confidence") if current else None
        )
        ai_changed = updates.get(
            "ai_changed_files", current.get("ai_changed_files") if current else None
        )
        if "current_situation" in updates and situation != "already_building":
            ai_changed = None
        if ai_changed is not None and situation != "already_building":
            raise InvalidEntryProfileError(
                "AI change status applies only when you are already building."
            )

        profile = _profile_view(
            current_situation=situation,
            coding_confidence=confidence,
            ai_changed_files=ai_changed,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            stored = EntryProfileView.model_validate(profile).model_dump(mode="json")
        except ValidationError as exc:
            raise InvalidEntryProfileError("Invalid entry choices.") from exc

        existing = project.get("workflow_artifacts") if project else None
        expected = existing if isinstance(existing, dict) else {}
        artifacts = dict(expected)
        artifacts[ENTRY_PROFILE_KEY] = stored
        if project is None:
            await repo.create_project(user_id, {"workflow_artifacts": artifacts})
            return {"profile": stored}

        updated = await repo.update_workflow_artifacts_if_current(
            user_id,
            project["id"],
            expected,
            artifacts,
        )
        if updated is not None:
            return {"profile": stored}
        project = await repo.get_project(user_id)
        if project is None:
            break

    raise RepositoryError("entry profile update conflicted repeatedly")


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
    archetype_id = project.get("archetype_id") if project else None
    archetype_name = None
    if project and archetype_id and project.get("intake_completed_at"):
        capabilities = project_capability_service.derive_project_capabilities(
            str(project.get("intake_purpose") or ""),
            str(project.get("intake_scope") or ""),
            str(project.get("intake_stack") or ""),
        )
        expected_archetype_id = template_service.resolve_archetype(
            capabilities.ai_feature, capabilities.frontend_or_database
        )
        if archetype_id == expected_archetype_id and archetype_id in ARCHETYPE_NAMES:
            archetype_name = project_capability_service.classification_name(
                archetype_id, capabilities, ARCHETYPE_NAMES
            )
    return {
        "started": project is not None,
        "completed": bool(project and project.get("intake_completed_at")),
        "answered_questions": [] if project is None else [
            n for n, col in ANSWER_COLUMNS.items() if project.get(col)
        ],
        "next_question": nxt,
        "archetype_id": archetype_id,
        "archetype_name": archetype_name,
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
    # Before completion, an already-answered question may be revised (M13E.1).
    # First-time answering stays strictly sequential — an unanswered question
    # is only accepted when it is the expected next one, so gaps can never
    # appear. After completion nothing is editable (checked above).
    already_answered = bool(project and project.get(ANSWER_COLUMNS[question_number]))
    if question_number != expected and not already_answered:
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
    capabilities = project_capability_service.derive_project_capabilities(
        project["intake_purpose"], project["intake_scope"], project["intake_stack"]
    )
    archetype_id = template_service.resolve_archetype(
        capabilities.ai_feature, capabilities.frontend_or_database
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
        "archetype_name": project_capability_service.classification_name(
            archetype_id, capabilities, ARCHETYPE_NAMES
        ),
    }


# --- classification ------------------------------------------------------------

def classify_archetype(purpose: str, scope: str, stack: str) -> int:
    """Exactly one of archetypes 1/2/3, never a fourth: the return value comes
    from the spec's fixed tiebreaker, whatever produced the signals."""
    capabilities = project_capability_service.derive_project_capabilities(
        purpose, scope, stack
    )
    return template_service.resolve_archetype(
        capabilities.ai_feature, capabilities.frontend_or_database
    )
