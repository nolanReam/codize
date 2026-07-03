"""Interrogation Gate engine (Milestone 9).

The gate is the core product mechanic: a mandatory 3-turn conversational
interrogation about the student's actual implementation, evaluated by a
separate temperature-0 LLM call against the spec's three-condition rubric
(all three required; generic textbook answers auto-fail).

Flow (spec Section 3, pinned by the milestone instructions):

  start   → eligibility + 30-minute-cooldown check, create the session
  turn1   → collect + validate the anchor statement, generate the Turn 1
            question (gate_turn_1.md, temp 0.3)
  turn2   → store the Turn 1 answer, probe the weakest of accuracy /
            specificity / completeness (gate_turn_2.md, temp 0.3)
  turn3   → store the Turn 2 answer, generate the fresh hypothetical
            (gate_turn_3.md, temp 0.3)
  evaluate→ store the Turn 3 answer, judge it (gate_evaluation.md, temp 0):
            PASS advances projects.current_phase (never past the final phase)
            and appends to gate_history_summary; FAIL sets failed_at, which
            derives the 30-minute cooldown. Both are stored on the session.

Anchor defense in depth: a deterministic server-side check rejects anchors
with no concrete implementation element, then the Turn 1 model re-validates
and may reply `ANCHOR_REJECTED: <what's missing>` (live-verified in
docs/prebuild/adversarial_tests.md). The model never invents an anchor.

Each turn's answer and the next question are written in ONE session update,
so an LLM failure (502) leaves the session in its previous state and the call
can simply be retried. The evaluator's parse is strict and fail-closed: a
malformed verdict stores nothing.

The `score` column is written here but never returned to the client — unlock
thresholds (M10) must stay unobservable (schema revokes the column from
client roles; this module keeps it out of every response body).
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services import llm_service, phase_service
from app.services.llm_service import LLMService
from app.services.project_repository import GateSessionRepository, ProjectRepository

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Fixed by prompts/README.md — gate turns at 0.3, evaluation at 0.
TURN_TEMPERATURE = 0.3
EVAL_TEMPERATURE = 0.0

COOLDOWN = timedelta(minutes=30)  # spec: no immediate retry after a failed gate

# Spec-verbatim anchor request (Section 3, Turn 1).
ANCHOR_PROMPT = (
    "Before we start — in one sentence, describe the specific structure you "
    "built for this phase. Name at least one variable, function, or database field."
)

_ANCHOR_REJECTED = "ANCHOR_REJECTED:"
_ANCHOR_HELP = (
    "Your anchor must name at least one specific variable, function, or "
    "database field from your implementation."
)
_NO_HISTORY = "No previous gates completed."

# A valid anchor names a concrete implementation element. These patterns are
# deliberately permissive (the Turn 1 model re-validates); they exist to stop
# obviously generic anchors ("I built the auth system and it works") without
# an LLM call.
_CONCRETE_PATTERNS = (
    re.compile(r"`[^`]+`"),                       # backticked code
    re.compile(r"\b\w+_\w+\b"),                   # snake_case identifier
    re.compile(r"\b[a-z]+[A-Z][A-Za-z]*\b"),      # camelCase identifier
    re.compile(r"\b\w+\s*\("),                    # function call
    re.compile(r"\b\w+\.\w+\b"),                  # dotted name / filename
    re.compile(r"['\"]\w+['\"]"),                 # quoted identifier
    re.compile(
        r"\b\w+\s+(?:table|column|field|function|variable|endpoint|route|"
        r"model|class|policy|trigger|index)\b", re.IGNORECASE,
    ),
)


class GateError(Exception):
    """Base for controlled gate errors; messages are safe client strings."""


class GateNotReadyError(GateError):
    """Project not eligible: no active project/roadmap/current phase."""


class GateAlreadyPassedError(GateError):
    """The current phase's gate has already been passed."""


class GateInProgressError(GateError):
    """An unfinished session exists — resume it via GET /gate/current."""


class GateCooldownError(GateError):
    """A failed attempt's 30-minute cooldown has not expired."""

    def __init__(self, retry_after_seconds: int) -> None:
        minutes = max(1, -(-retry_after_seconds // 60))  # ceil
        super().__init__(
            f"Gate failed recently — retry available in about {minutes} minute(s)."
        )
        self.retry_after_seconds = retry_after_seconds


class GateSessionNotFoundError(GateError):
    """No such gate session for this user."""


class GateOutOfOrderError(GateError):
    """The requested step doesn't match the session's state."""


class AnchorInvalidError(GateError):
    """The anchor statement names no concrete implementation element."""


class GateGenerationError(GateError):
    """The LLM call failed or returned unusable output — nothing was stored."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def anchor_names_concrete_element(anchor: str) -> bool:
    return any(p.search(anchor) for p in _CONCRETE_PATTERNS)


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _fill(prompt: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        prompt = prompt.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", prompt)
    if leftover:  # programming error, not a client error
        raise RuntimeError(f"unfilled prompt placeholders: {leftover}")
    return prompt


def _project_summary(project: dict) -> str:
    return f"{project['intake_purpose']} Scope: {project['intake_scope']}"


def _history(project: dict) -> str:
    return project.get("gate_history_summary") or _NO_HISTORY


def _turn1_prompt(project: dict, phase: dict, anchor: str) -> str:
    base = _fill(_load_prompt("gate_turn_1.md"), {
        "GATE_TARGETS": json.dumps(phase["explanation_gate_targets"]),
        "GATE_DEPTH": phase["gate_depth"],
        "PROJECT_SUMMARY": _project_summary(project),
        "STUDENT_STACK": project["intake_stack"],
        "GATE_HISTORY_SUMMARY": _history(project),
    })
    # Composition live-verified in docs/prebuild/adversarial_tests.md: the
    # model re-validates the anchor (defense in depth) and replies with either
    # the rejection marker or the bare Turn 1 question.
    return (
        f"{base}\n\n---\n\n"
        f'The student\'s reply to the anchor request (Step 1) was:\n\n"{anchor}"\n\n'
        "Apply the Step 1 validation rules to this reply. If it is NOT a valid "
        f"anchor, respond with exactly the marker {_ANCHOR_REJECTED} followed by "
        "one sentence telling the student what is missing — and nothing else. "
        "If it IS a valid anchor, perform Step 2: respond with ONLY the text "
        "of the one Turn 1 question — no validation commentary, no preamble, "
        "no restatement of the anchor."
    )


def _turn2_prompt(session: dict, answer: str) -> str:
    base = _fill(_load_prompt("gate_turn_2.md"), {
        "ANCHOR_STATEMENT": session["anchor_statement"],
        "TURN_1_QUESTION": session["turns"][0]["question"],
        "TURN_1_RESPONSE": answer,
    })
    return f"{base}\n\nRespond with ONLY the text of the one follow-up question."


def _turn3_prompt(project: dict, session: dict, answer: str) -> str:
    turns = session["turns"]
    base = _fill(_load_prompt("gate_turn_3.md"), {
        "ANCHOR_STATEMENT": session["anchor_statement"],
        "TURN_1_QUESTION": turns[0]["question"],
        "TURN_1_RESPONSE": turns[0]["answer"],
        "TURN_2_QUESTION": turns[1]["question"],
        "TURN_2_RESPONSE": answer,
        "GATE_HISTORY_SUMMARY": _history(project),
    })
    return f"{base}\n\nRespond with ONLY the text of the one hypothetical question."


def _evaluation_prompt(session: dict, answer: str) -> str:
    turns = session["turns"]
    return _fill(_load_prompt("gate_evaluation.md"), {
        "ANCHOR_STATEMENT": session["anchor_statement"],
        "TURN_1_QUESTION": turns[0]["question"],
        "TURN_1_RESPONSE": turns[0]["answer"],
        "TURN_2_QUESTION": turns[1]["question"],
        "TURN_2_RESPONSE": turns[1]["answer"],
        "TURN_3_QUESTION": turns[2]["question"],
        "TURN_3_RESPONSE": answer,
    })


def parse_evaluation(raw: str) -> dict:
    """Strict, fail-closed parse of the evaluator's JSON verdict."""
    text = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise GateGenerationError("Gate evaluation failed. Please try again.")
    if (
        not isinstance(data, dict)
        or data.get("verdict") not in ("PASS", "FAIL")
        or not isinstance(data.get("reason"), str)
        or not data["reason"].strip()
        or not isinstance(data.get("score"), int)
        or isinstance(data.get("score"), bool)
        or not 0 <= data["score"] <= 10
    ):
        raise GateGenerationError("Gate evaluation failed. Please try again.")
    return {"verdict": data["verdict"], "reason": data["reason"].strip(), "score": data["score"]}


async def _complete(llm: LLMService, prompt: str, temperature: float) -> str:
    try:
        return await llm.complete(prompt, temperature)
    except llm_service.LLMError as e:
        raise GateGenerationError(
            "The gate could not generate the next step. Please try again."
        ) from e


async def _load_gate_context(repo: ProjectRepository, user_id: str) -> tuple[dict, dict]:
    """Eligibility: active project + roadmap + current phase present."""
    try:
        project = await phase_service.load_active_project(repo, user_id)
    except phase_service.WorkspaceNotReadyError:
        raise GateNotReadyError(
            "The gate needs an active project with a generated roadmap."
        )
    for phase in project["roadmap"]["phases"]:
        if phase["phase"] == project.get("current_phase"):
            return project, phase
    raise GateNotReadyError("The gate needs an active project with a current phase.")


def _next_step(session: dict) -> str:
    """Which call the session expects next: turn1|turn2|turn3|evaluate|completed."""
    if session.get("passed") is not None:
        return "completed"
    turns = session.get("turns") or []
    if not turns:
        return "turn1"
    last = turns[-1]
    if last.get("answer") is None:
        return {1: "turn2", 2: "turn3", 3: "evaluate"}[last["turn"]]
    # Unreachable by construction: answers are stored together with the next
    # question in one update.
    raise GateOutOfOrderError("This gate session is in an unexpected state.")


async def _load_session(
    project_repo: ProjectRepository,
    gate_repo: GateSessionRepository,
    user_id: str,
    session_id: str,
    expected_step: str,
) -> tuple[dict, dict, dict]:
    project, phase = await _load_gate_context(project_repo, user_id)
    session = await gate_repo.get_session(user_id, session_id)
    # Ownership: the repo query filters by user_id, so another user's session
    # id is simply not found.
    if session is None or session["project_id"] != project["id"]:
        raise GateSessionNotFoundError("Gate session not found.")
    step = _next_step(session)
    if step == "completed":
        raise GateOutOfOrderError("This gate session has already been evaluated.")
    if step != expected_step:
        raise GateOutOfOrderError(
            f"Out of order: this session's next step is {step}, not {expected_step}."
        )
    return project, phase, session


def _cooldown_remaining(latest_session: dict | None) -> int:
    """Seconds left on the newest failed attempt's cooldown; 0 when none."""
    if not latest_session or latest_session.get("passed") is not False:
        return 0
    failed_at = _parse_ts(latest_session.get("failed_at"))
    if failed_at is None:
        return 0
    remaining = COOLDOWN - (_now() - failed_at)
    return max(0, int(remaining.total_seconds()))


# ---------------------------------------------------------------------------
# Public flow
# ---------------------------------------------------------------------------


async def start_gate(
    project_repo: ProjectRepository, gate_repo: GateSessionRepository, user_id: str
) -> dict:
    project, phase = await _load_gate_context(project_repo, user_id)
    sessions = await gate_repo.list_phase_sessions(user_id, project["id"], phase["phase"])
    latest = sessions[0] if sessions else None
    if latest is not None:
        if latest.get("passed") is True:
            raise GateAlreadyPassedError("This phase's gate has already been passed.")
        if latest.get("passed") is None:
            raise GateInProgressError(
                "A gate session is already in progress for this phase — resume it via GET /gate/current."
            )
        remaining = _cooldown_remaining(latest)
        if remaining > 0:
            raise GateCooldownError(remaining)
    session = await gate_repo.create_session(
        user_id, {"project_id": project["id"], "phase_id": phase["phase"], "turns": []}
    )
    return {
        "gate_session_id": session["id"],
        "phase": phase["phase"],
        "phase_title": phase["phase_title"],
        "anchor_prompt": ANCHOR_PROMPT,
    }


async def submit_anchor(
    project_repo: ProjectRepository,
    gate_repo: GateSessionRepository,
    llm: LLMService,
    user_id: str,
    session_id: str,
    anchor_statement: str,
) -> dict:
    project, phase, session = await _load_session(
        project_repo, gate_repo, user_id, session_id, "turn1"
    )
    anchor = anchor_statement.strip()
    if not anchor or not anchor_names_concrete_element(anchor):
        raise AnchorInvalidError(_ANCHOR_HELP)

    raw = (await _complete(llm, _turn1_prompt(project, phase, anchor), TURN_TEMPERATURE)).strip()
    if raw.startswith(_ANCHOR_REJECTED):
        raise AnchorInvalidError(raw[len(_ANCHOR_REJECTED):].strip() or _ANCHOR_HELP)
    if not raw:
        raise GateGenerationError("The gate could not generate the next step. Please try again.")

    # Anchor + question in one write: an LLM failure leaves nothing stored.
    await gate_repo.update_session(
        user_id, session_id,
        {"anchor_statement": anchor, "turns": [{"turn": 1, "question": raw, "answer": None}]},
    )
    return {"gate_session_id": session_id, "turn": 1, "question": raw}


async def generate_followup(
    project_repo: ProjectRepository,
    gate_repo: GateSessionRepository,
    llm: LLMService,
    user_id: str,
    session_id: str,
    turn: int,
    answer: str,
) -> dict:
    """Turn 2 and Turn 3: store the previous turn's answer, ask the next question."""
    assert turn in (2, 3)
    project, phase, session = await _load_session(
        project_repo, gate_repo, user_id, session_id, f"turn{turn}"
    )
    answer = answer.strip()
    prompt = (
        _turn2_prompt(session, answer) if turn == 2
        else _turn3_prompt(project, session, answer)
    )
    question = (await _complete(llm, prompt, TURN_TEMPERATURE)).strip()
    if not question:
        raise GateGenerationError("The gate could not generate the next step. Please try again.")

    turns = list(session["turns"])
    turns[-1] = {**turns[-1], "answer": answer}
    turns.append({"turn": turn, "question": question, "answer": None})
    await gate_repo.update_session(user_id, session_id, {"turns": turns})
    return {"gate_session_id": session_id, "turn": turn, "question": question}


def _summary_line(phase: dict, attempt_count: int) -> str:
    attempts = (
        "first attempt" if attempt_count <= 1
        else f"attempt {attempt_count} ({attempt_count - 1} failed cooldown attempt(s) before)"
    )
    return f"Phase {phase['phase']} ({phase['phase_title']}): gate passed on {attempts}."


async def evaluate_gate(
    project_repo: ProjectRepository,
    gate_repo: GateSessionRepository,
    llm: LLMService,
    user_id: str,
    session_id: str,
    answer: str,
) -> dict:
    project, phase, session = await _load_session(
        project_repo, gate_repo, user_id, session_id, "evaluate"
    )
    answer = answer.strip()
    raw = await _complete(llm, _evaluation_prompt(session, answer), EVAL_TEMPERATURE)
    verdict = parse_evaluation(raw)  # fail-closed: malformed output stores nothing
    passed = verdict["verdict"] == "PASS"

    turns = list(session["turns"])
    turns[-1] = {**turns[-1], "answer": answer}
    fields: dict = {
        "turns": turns,
        "passed": passed,
        "reason": verdict["reason"],
        "score": verdict["score"],  # stored for M10 unlock thresholds, never returned
        ("passed_at" if passed else "failed_at"): _now().isoformat(),
    }
    await gate_repo.update_session(user_id, session_id, fields)

    result = {
        "gate_session_id": session_id,
        "phase": phase["phase"],
        "verdict": verdict["verdict"],
        "reason": verdict["reason"],
    }
    if passed:
        sessions = await gate_repo.list_phase_sessions(user_id, project["id"], phase["phase"])
        summary = _summary_line(phase, len(sessions))
        history = project.get("gate_history_summary")
        project_fields: dict = {
            "gate_history_summary": f"{history}\n{summary}" if history else summary
        }
        if phase["phase"] < len(project["roadmap"]["phases"]):
            project_fields["current_phase"] = phase["phase"] + 1
        project = await project_repo.update_project(user_id, project["id"], project_fields)
        result["current_phase"] = project["current_phase"]
    else:
        result["current_phase"] = phase["phase"]
        result["cooldown_seconds"] = int(COOLDOWN.total_seconds())
    return result


def _turns_view(session: dict) -> list[dict]:
    """Transcript for the client — questions and answers only, never verdict data."""
    return [
        {"turn": t["turn"], "question": t["question"], "answer": t["answer"]}
        for t in session.get("turns") or []
    ]


async def get_current_gate(
    project_repo: ProjectRepository, gate_repo: GateSessionRepository, user_id: str
) -> dict:
    project, phase = await _load_gate_context(project_repo, user_id)
    sessions = await gate_repo.list_phase_sessions(user_id, project["id"], phase["phase"])
    latest = sessions[0] if sessions else None
    base = {"phase": phase["phase"], "phase_title": phase["phase_title"]}

    if latest is None:
        return {**base, "state": "not_started", "anchor_prompt": ANCHOR_PROMPT}
    if latest.get("passed") is True:
        # Only reachable on the final phase — passing any earlier phase
        # advances current_phase, so its sessions are no longer "current".
        return {**base, "state": "passed", "reason": latest.get("reason")}
    if latest.get("passed") is False:
        remaining = _cooldown_remaining(latest)
        if remaining > 0:
            return {
                **base,
                "state": "cooldown",
                "reason": latest.get("reason"),
                "cooldown_seconds_remaining": remaining,
            }
        return {**base, "state": "not_started", "anchor_prompt": ANCHOR_PROMPT}

    view = {
        **base,
        "state": "in_progress",
        "gate_session_id": latest["id"],
        "next_action": _next_step(latest),
        "anchor_statement": latest.get("anchor_statement"),
        "turns": _turns_view(latest),
    }
    if view["next_action"] == "turn1":
        view["anchor_prompt"] = ANCHOR_PROMPT
    return view
