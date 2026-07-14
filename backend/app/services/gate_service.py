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

The `score` column is written here but never returned to the client — it
feeds the hidden unlock thresholds consumed server-side by unlock_service
(M10), which runs after every PASS (schema revokes the column from client
roles; this module keeps it out of every response body).
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services import (
    defense_context_service,
    grounding_service,
    llm_service,
    phase_service,
    unlock_service,
    workflow_context_service,
)
from app.services.llm_service import LLMService
from app.services.project_repository import (
    GateSessionRepository,
    ProjectRepository,
    RepositoryError,
    UnlockRepository,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Fixed by prompts/README.md — gate turns at 0.3, evaluation at 0.
TURN_TEMPERATURE = 0.3
EVAL_TEMPERATURE = 0.0

# M14B: per-turn grounding preference carried in the artifact-context block
# (composition only — the prompt .md files are unchanged). Artifacts guide
# the questions; the evaluator never sees them and is untouched.
_TURN_HINTS = {
    1: (
        "prefer the student's anchor, then the Prompt Builder artifact, then "
        "the Review Board notes."
    ),
    2: (
        "prefer the student's previous answer, then the Review Board notes, "
        "then the phase goal and any relevant recorded artifact."
    ),
    3: (
        "prefer the student's previous answers, then recorded Verification "
        "results (especially checks recorded as skipped, failed, or "
        "not_applicable) and Evidence entries."
    ),
}
# One corrective regeneration after a grounding rejection, then the existing
# retryable failure — bounded LLM spend (at most 2 calls per turn).
_MAX_GROUNDING_ATTEMPTS = 2

COOLDOWN = timedelta(minutes=30)  # spec: no immediate retry after a failed gate

# Spec-verbatim anchor request (Section 3, Turn 1).
ANCHOR_PROMPT = (
    "Before we start — in one sentence, describe the specific structure you "
    "built for this phase. Name at least one variable, function, or database field."
)

_ANCHOR_REJECTED = "ANCHOR_REJECTED:"
_ANCHOR_HELP = (
    "Name one exact thing from your code, like `likes_score`, "
    "`update_likes_score()`, `tasks.user_id`, or `app/models.py`."
)
_NO_HISTORY = "No previous gates completed."

# A valid anchor names a concrete implementation element. Two tiers (M13E.2):
#
# STRONG — the anchor contains an actual code-shaped identifier (backticks,
# snake_case, "the variable is called likes_score", a path…). The server-side
# check is authoritative for these; the Turn 1 model is told the anchor is
# already validated and must not reject it, because in the pilot it falsely
# rejected realistic student phrasing that plainly named an identifier.
#
# WEAK — the anchor only gestures at an element type ("the users table") with
# no code-shaped name. Deliberately permissive; the Turn 1 model re-validates
# these (defense in depth, live-verified in the M9 adversarial suite).
_STRONG_PATTERNS = (
    re.compile(r"`[^`]+`"),                       # backticked code
    re.compile(r"\b\w+_\w+\b"),                   # snake_case identifier
    re.compile(r"\b[a-z]+[A-Z][A-Za-z]*\b"),      # camelCase identifier
    re.compile(r"\b\w+\s*\("),                    # function call
    re.compile(r"\b\w+\.\w+\b"),                  # dotted name / filename
    re.compile(r"\b\w+/[\w.\-/]+"),               # path with a slash (routes/tasks.py)
    re.compile(r"['\"]\w+['\"]"),                 # quoted identifier
    # "a variable called score" / "field named owner" — plain student phrasing
    # that explicitly names the element.
    re.compile(r"\b(?:called|named)\s+['\"`]?[A-Za-z_]\w*", re.IGNORECASE),
)
_WEAK_PATTERNS = (
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
    return any(p.search(anchor) for p in _STRONG_PATTERNS + _WEAK_PATTERNS)


def anchor_has_strong_element(anchor: str) -> bool:
    """True when the anchor contains a code-shaped identifier — the server-side
    check is authoritative and the model must not re-reject it."""
    return any(p.search(anchor) for p in _STRONG_PATTERNS)


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


def _turn1_prompt(
    project: dict, phase: dict, anchor: str, strong: bool, context_block: str
) -> str:
    base = _fill(_load_prompt("gate_turn_1.md"), {
        "GATE_TARGETS": json.dumps(phase["explanation_gate_targets"]),
        "GATE_DEPTH": phase["gate_depth"],
        "PROJECT_SUMMARY": _project_summary(project),
        "STUDENT_STACK": project["intake_stack"],
        "GATE_HISTORY_SUMMARY": _history(project),
    })
    base = f"{base}{context_block}"
    # Composition tails live-tuned in M9 (docs/prebuild/adversarial_tests.md);
    # "respond with ONLY the text of the one question" is load-bearing.
    if strong:
        # M13E.2: the anchor names a code-shaped identifier, so the server-side
        # check is authoritative — the model must not re-reject realistic
        # student phrasing ("the variable is called likes_score").
        return (
            f"{base}\n\n---\n\n"
            f'The student\'s reply to the anchor request (Step 1) was:\n\n"{anchor}"\n\n'
            "This reply has already been validated server-side: it names at "
            "least one concrete implementation element, so it IS a valid anchor. "
            "Do not re-validate it and do not reject it. Perform Step 2: respond "
            "with ONLY the text of the one Turn 1 question — no validation "
            "commentary, no preamble, no restatement of the anchor."
        )
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


def _turn2_prompt(session: dict, answer: str, context_block: str) -> str:
    base = _fill(_load_prompt("gate_turn_2.md"), {
        "ANCHOR_STATEMENT": session["anchor_statement"],
        "TURN_1_QUESTION": session["turns"][0]["question"],
        "TURN_1_RESPONSE": answer,
    })
    return f"{base}{context_block}\n\nRespond with ONLY the text of the one follow-up question."


def _turn3_prompt(project: dict, session: dict, answer: str, context_block: str) -> str:
    turns = session["turns"]
    base = _fill(_load_prompt("gate_turn_3.md"), {
        "ANCHOR_STATEMENT": session["anchor_statement"],
        "TURN_1_QUESTION": turns[0]["question"],
        "TURN_1_RESPONSE": turns[0]["answer"],
        "TURN_2_QUESTION": turns[1]["question"],
        "TURN_2_RESPONSE": answer,
        "GATE_HISTORY_SUMMARY": _history(project),
    })
    return f"{base}{context_block}\n\nRespond with ONLY the text of the one hypothetical question."


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


# ---------------------------------------------------------------------------
# User-facing question cleanliness (M13C.2B)
# ---------------------------------------------------------------------------
#
# flash-lite occasionally leaks meta/preamble text into a generated question —
# "The student's reply is a valid anchor... Here is the Turn 1 question: ...",
# rubric language, internal step labels — despite the prompt asking for the
# bare question. The frontend faithfully renders whatever the backend returns,
# so the clean-up belongs here, at the generation boundary, as a deterministic
# guard (no extra LLM call). It strips leading meta sentences and, as a last
# resort, rejects an all-meta output so the existing retry path re-runs the
# turn. It NEVER touches the evaluator (that stays parse_evaluation), pass/fail
# logic, scores, cooldown, or the prompts.

_GENERIC_RETRY = "The gate could not generate the next step. Please try again."

# A leading meta/preamble sentence — the model talking ABOUT the task, the
# anchor, or the rubric instead of asking the student a question. Deliberately
# narrow: it must not match a legitimate question opener (imperatives like
# "Explain…", "Walk me through…", conversational "Good — you covered…", or any
# question that references the student's own anchor). None of these begin with
# the third-person/rubric phrasings enumerated here.
_META_SENTENCE = re.compile(
    r"^\s*(?:"
    r"the student\b|"
    r"(?:the\s+|this\s+|that\s+|your\s+|their\s+)?(?:reply|response|answer|anchor(?:\s+statement)?)\s+(?:is|looks|counts|qualifies|names|is\s+a)\b[^?]*\bvalid\b|"
    r"valid anchor\b|"
    r"this\s+is\s+a\s+valid\b|"
    r"that(?:'s| is)\s+a\s+valid\b|"
    r"it(?:'s|\s+is)\s+a\s+valid\b|"
    r"therefore\b|"
    r"the anchor(?:\s+statement)?\s+is\b|"
    r"here(?:'s| is| are)\b[^?]*\b(?:question|hypothetical|follow[\s-]?up|turn)\b|"
    r"(?:according to|as per|per)\s+(?:the\s+)?(?:rubric|evaluator|criteria|instructions?|gate\s+targets?)\b|"
    r"based on\s+(?:the\s+)?(?:rubric|criteria|evaluator|gate\s+targets?)\b|"
    r"i(?:'ll| will| am going to| shall)\s+(?:now\s+)?ask\b|"
    r"i(?:'ll| will)?\s*now\s+ask\b|"
    r"(?:now,?\s+)?i\s+(?:need|want|have|am\s+going)\s+to\b|"
    r"now,?\s+i\b|"
    r"let(?:'s|\s+us)\s+(?:craft|formulate|write|compose|draft|construct|generate|proceed|move|begin)\b|"
    r"(?:question|prompt)\s+formulation\b|"
    r"student'?s\s+anchor\b|"
    r"(?:step|turn)\s*\d\b|"
    r"note\s*:|"
    r"as instructed\b|"
    r"the student (?:must|should|needs|has to)\b"
    r")",
    re.IGNORECASE,
)

# An inline hand-off: preamble that ends by announcing the question on the same
# line ("… Here is the Turn 1 question: <q>", "… Let's craft the question: <q>").
# Removed up to and including the colon so a question with no space after the
# colon is still recovered.
_HANDOFF = re.compile(
    r"^.*?(?:here(?:'s| is| are)|this is|below is|the following is|"
    r"let(?:'s| us) (?:craft|formulate|write|compose|draft)|"
    r"i(?:'ll| will| need to| am going to)?\s*(?:now\s+)?(?:craft|formulate|write|compose|ask))"
    r"[^:?]{0,80}?(?:question|hypothetical|follow[\s-]?up)[^:?]{0,20}?:\s*",
    re.IGNORECASE | re.DOTALL,
)

# A line that is only a markdown heading, a bold section label, or a bare
# internal label ("**Question Formulation**", "### Student's Anchor") — never
# part of a legitimate student-facing question; dropped whole. A line
# containing "?" is never treated as a label (it may BE the question,
# heading/italic-formatted).
_LABEL_LINE = re.compile(
    r"^\s*(?:#{1,6}\s[^?\n]*|\*{1,2}[^*\n?]{1,80}\*{1,2}:?\s*|-{3,}\s*|"
    r"(?:question\s+formulation|student'?s\s+anchor|anchor\s+validation|gate\s+targets?)\s*:?\s*)$",
    re.IGNORECASE,
)

# Backstop (M13E.2): internal/rubric vocabulary that must never reach the
# student, even inside an otherwise question-shaped output. A match after
# sanitization rejects the output as retryable — same path as all-meta output.
_HARD_LEAK = re.compile(
    r"valid\s+anchor|anchor_rejected|question\s+formulation|student'?s\s+anchor|"
    r"gate\s+targets?|gate\s+depth|\brubric\b|\bevaluator\b|"
    r"\bspecificity\b|\bpersonalization\b|"
    r"now,?\s+i\s+need\s+to|i\s+need\s+to\s+formulate|"
    # M14B: injected artifact text must never surface as a question about the
    # internals — no legitimate defense question mentions these.
    r"system\s+prompt|context\s+pack|"
    r"^#{1,6}\s|\*\*[^*\n]+\*\*\s*:",
    re.IGNORECASE | re.MULTILINE,
)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.:!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _unwrap(text: str) -> str:
    fenced = re.match(r"^```(?:\w+)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    quotes = "\"'“”‘’"
    if len(text) >= 2 and text[0] in quotes and text[-1] in quotes:
        text = text[1:-1].strip()
    return text


def _is_meta(sentence: str) -> bool:
    # Never treat the actual question as meta: a real question ends with "?".
    if sentence.rstrip().endswith("?"):
        return False
    return bool(_META_SENTENCE.match(sentence))


def sanitize_gate_question(raw: str) -> str:
    """Strip leading meta/preamble from a generated question, deterministically.

    Returns the cleaned question text (possibly empty if the output was only
    preamble). Leaves already-clean output byte-for-byte unchanged."""
    text = _unwrap(raw.strip())
    # Drop whole lines that are markdown headings / internal section labels.
    text = "\n".join(ln for ln in text.splitlines() if not _LABEL_LINE.match(ln)).strip()
    handoff = _HANDOFF.sub("", text, count=1)
    if handoff != text:
        # The announced question is often quoted ('Let\'s craft the question:
        # "…?"') — unwrap again after removing the hand-off.
        text = _unwrap(handoff.strip())
    else:
        text = handoff.strip()

    sentences = _sentences(text)
    dropped = 0
    # Drop leading meta sentences, but never strip the final remaining one.
    while len(sentences) - dropped > 1 and _is_meta(sentences[dropped]):
        dropped += 1
    if dropped == 0:
        return text  # nothing to strip — preserve original formatting
    return _unwrap(" ".join(s.strip() for s in sentences[dropped:]).strip())


def clean_gate_question(raw: str) -> str:
    """Sanitize a generated question and reject an unusable/all-meta result.

    Rejection raises GateGenerationError, which the existing turn flow treats
    as a retryable failure (nothing is stored), so the student simply re-runs
    the step and a clean question is generated."""
    cleaned = sanitize_gate_question(raw)
    if not cleaned or _is_meta(cleaned) or _HARD_LEAK.search(cleaned):
        raise GateGenerationError(_GENERIC_RETRY)
    return cleaned


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


async def _artifact_context(
    repo: ProjectRepository,
    user_id: str,
    phase: dict,
    turn: int,
    workflow_context=None,
) -> tuple:
    """The M14A pack + the composed artifact-context block for one turn.
    Built fresh per call (pure read); missing artifacts never fail — they
    arrive as missing_sources the prompt is told not to invent."""
    pack = await defense_context_service.build_defense_context(
        repo,
        user_id,
        phase["phase"],
        workflow_context=workflow_context,
    )
    block = grounding_service.context_block(
        defense_context_service.render_defense_context(pack), _TURN_HINTS[turn]
    )
    return pack, block


async def _grounded_question(
    llm: LLMService,
    prompt: str,
    *,
    pack,
    anchor: str | None,
    prior_answers: list[str],
    prior_questions: list[str],
    anchor_mode: str | None = None,
) -> tuple[str, dict]:
    """Generate one turn question and hold it to the M14B safety order:

        generate → (turn-1 anchor-marker check) → M13E.2 sanitize + hard-leak
                 → deterministic grounding validation → return for storage

    Grounding is validated on the CLEANED user-facing text (a deliberate,
    tested deviation from validating the raw output: what is stored is what
    must be grounded). A grounding rejection triggers exactly one corrective
    regeneration; a second rejection is the existing retryable failure
    (nothing stored). Sanitizer failures keep their M13E.2 behavior —
    immediately retryable, no corrective loop."""
    corrective = None
    for attempt in range(_MAX_GROUNDING_ATTEMPTS):
        composed = prompt if corrective is None else f"{prompt}\n\n{corrective}"
        raw = (await _complete(llm, composed, TURN_TEMPERATURE)).strip()
        if anchor_mode is not None and raw.startswith(_ANCHOR_REJECTED):
            if anchor_mode == "strong":
                # The anchor names a real identifier and the model was told
                # not to re-validate — a rejection is the model disobeying,
                # never the student failing (M13E.2).
                logger.warning("model rejected a pre-validated strong anchor; retryable")
                raise GateGenerationError(_GENERIC_RETRY)
            raise AnchorInvalidError(raw[len(_ANCHOR_REJECTED):].strip() or _ANCHOR_HELP)
        question = clean_gate_question(raw)
        try:
            grounding = grounding_service.validate_question(
                question,
                pack=pack,
                anchor=anchor,
                prior_answers=prior_answers,
                prior_questions=prior_questions,
            )
        except grounding_service.GroundingRejectedError as exc:
            if attempt + 1 < _MAX_GROUNDING_ATTEMPTS:
                corrective = grounding_service.corrective_feedback(exc.issues)
                continue
            # Identifier-level issues only — never raw model output.
            logger.warning("grounded generation rejected twice: %s", exc.issues)
            raise GateGenerationError(_GENERIC_RETRY)
        return question, grounding.as_dict()
    raise GateGenerationError(_GENERIC_RETRY)  # pragma: no cover — loop always returns/raises


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


def cooldown_remaining(latest_session: dict | None) -> int:
    """Seconds left on the newest failed attempt's cooldown; 0 when none.
    Public since M12 — the evaluation service reports cooldown state from the
    same derivation, so the 30-minute rule stays single-sourced here."""
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
        remaining = cooldown_remaining(latest)
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
    strong = anchor_has_strong_element(anchor)

    # M14B: ground the question in the recorded workflow context.
    workflow_context = workflow_context_service.build_workflow_context(
        project, phase["phase"]
    )
    pack, block = await _artifact_context(
        project_repo, user_id, phase, 1, workflow_context
    )
    question, grounding = await _grounded_question(
        llm,
        _turn1_prompt(project, phase, anchor, strong, block),
        pack=pack,
        anchor=anchor,
        prior_answers=[],
        prior_questions=[],
        anchor_mode="strong" if strong else "weak",
    )

    # Anchor + question in one write: an LLM failure leaves nothing stored.
    # The grounding metadata lives inside the turns JSONB but never reaches
    # the client — _turns_view whitelists turn/question/answer only.
    await gate_repo.update_session(
        user_id, session_id,
        {"anchor_statement": anchor,
         "turns": [{
             "turn": 1,
             "question": question,
             "answer": None,
             "grounding": grounding,
             "workflow_context_snapshot": workflow_context_service.snapshot_payload(
                 workflow_context
             ),
         }]},
    )
    return {"gate_session_id": session_id, "turn": 1, "question": question}


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

    # M14B: ground the follow-up in the recorded workflow context plus the
    # student's own transcript so far (including the answer being submitted).
    workflow_context = workflow_context_service.context_from_snapshot(session)
    snapshot_missing = workflow_context is None
    if workflow_context is None:
        # Legacy/in-flight sessions created before M16C.1 gain a stable
        # snapshot on their next successful turn. Nothing is written until
        # the answer + next question atomic update succeeds.
        workflow_context = workflow_context_service.build_workflow_context(
            project, phase["phase"]
        )
    pack, block = await _artifact_context(
        project_repo, user_id, phase, turn, workflow_context
    )
    prompt = (
        _turn2_prompt(session, answer, block) if turn == 2
        else _turn3_prompt(project, session, answer, block)
    )
    stored_turns = session["turns"]
    prior_answers = [t["answer"] for t in stored_turns if t.get("answer")] + [answer]
    prior_questions = [t["question"] for t in stored_turns]
    question, grounding = await _grounded_question(
        llm,
        prompt,
        pack=pack,
        anchor=session.get("anchor_statement"),
        prior_answers=prior_answers,
        prior_questions=prior_questions,
    )

    turns = list(stored_turns)
    if snapshot_missing:
        turns[0] = {
            **turns[0],
            "workflow_context_snapshot": workflow_context_service.snapshot_payload(
                workflow_context
            ),
        }
    turns[-1] = {**turns[-1], "answer": answer}
    turns.append({"turn": turn, "question": question, "answer": None, "grounding": grounding})
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
    unlock_repo: UnlockRepository,
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
        # Functional unlocks (M10) are evaluated only on PASS. The pass is
        # already stored, so an unlock storage error must not fail the verdict
        # response — evaluation recomputes from full history on every PASS,
        # so a missed grant self-heals at the next one.
        try:
            result["new_unlocks"] = await unlock_service.evaluate_unlocks(
                gate_repo, unlock_repo, user_id, project
            )
        except RepositoryError:
            logger.warning("unlock evaluation failed after gate pass", exc_info=True)
            result["new_unlocks"] = []
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
        remaining = cooldown_remaining(latest)
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
