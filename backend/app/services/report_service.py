"""Deterministic Defense Report context; no provider call and no persistence.

The current frontend Report remains client-assembled in M16C.1.  This service
is the M16C.2 backend seam: it reuses the one curated workflow context and the
latest Defense attempt's server-owned snapshot when available.
"""

from app.schemas.report import (
    DefenseReportContext,
    ReportDefenseRecord,
    ReportDefenseTurn,
)
from app.services import phase_service, workflow_context_service
from app.services.content_safety_service import has_unsafe_control_chars, redact_secrets
from app.services.project_repository import GateSessionRepository, ProjectRepository


MAX_REPORT_QUESTION_CHARS = 4_000
MAX_REPORT_ANSWER_CHARS = 8_000
MAX_REPORT_REASON_CHARS = 2_000
_TRUNCATION_MARKER = " …[TRUNCATED]"


def _safe_report_text(value, limit: int) -> str | None:
    """Bound and redact historical transcript text without echoing bad rows."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or has_unsafe_control_chars(value)
    ):
        return None
    cleaned, _ = redact_secrets(value)
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER
    return cleaned


def _defense_record(session: dict | None) -> ReportDefenseRecord:
    if session is None:
        return ReportDefenseRecord(state="not_started", turns=[])
    passed = session.get("passed")
    state = "in_progress" if passed is None else ("passed" if passed else "failed")
    turns = []
    for raw in session.get("turns") or []:
        if not isinstance(raw, dict):
            continue
        turn = raw.get("turn")
        question = _safe_report_text(raw.get("question"), MAX_REPORT_QUESTION_CHARS)
        answer = _safe_report_text(raw.get("answer"), MAX_REPORT_ANSWER_CHARS)
        if turn in (1, 2, 3) and question is not None:
            turns.append(
                ReportDefenseTurn(
                    turn=turn,
                    question=question,
                    answer=answer,
                )
            )
    return ReportDefenseRecord(
        state=state,
        turns=turns,
        evaluator_outcome=("PASS" if passed is True else "FAIL" if passed is False else None),
        evaluator_reason=_safe_report_text(
            session.get("reason"), MAX_REPORT_REASON_CHARS
        ),
    )


async def build_report_context(
    project_repo: ProjectRepository,
    gate_repo: GateSessionRepository,
    user_id: str,
    phase_number: int,
) -> DefenseReportContext:
    """Build the owner/phase-scoped report foundation as a pure read."""
    project = await phase_service.load_active_project(project_repo, user_id)
    phase = phase_service.phase_view(project, phase_number)
    sessions = await gate_repo.list_phase_sessions(
        user_id, project["id"], phase_number
    )
    latest = sessions[0] if sessions else None
    context = (
        workflow_context_service.context_from_snapshot(latest)
        if latest is not None
        else None
    )
    source = "defense_attempt" if context is not None else "current_workflow"
    if context is None:
        context = workflow_context_service.build_workflow_context(
            project, phase_number
        )
    return DefenseReportContext(
        phase_number=phase_number,
        phase_title=phase["phase_title"],
        workflow_context_source=source,
        workflow_context=context,
        defense=_defense_record(latest),
    )
