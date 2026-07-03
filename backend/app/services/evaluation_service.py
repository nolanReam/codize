"""Evaluation engine (Milestone 12).

A student-facing progress evaluation for the authenticated user's current
project: where am I, what's done, what's left, what did my recent gate
outcomes mean, and what should I do next.

The evaluation is DETERMINISTIC and COMPUTED ON READ — no LLM call, no
persistence, no schema change. The spec defines no evaluation snapshot to
store, and its tracking section is explicit that process metrics (gate quality
scores, return rate, vocabulary growth) "are not shown to the student as
numbers or scores" — so this module derives everything from state the client
may already see: the stored roadmap's current phase view, task progress,
gate_history_summary lines (attempt counts only), the evaluator's one-sentence
reason (already returned at evaluate time), and the safe unlock views. Raw
gate scores, the unlock threshold/rule, evaluator internals, and prompt text
appear nowhere.

Readiness states, decided in the same order as phase eligibility:

  not_started     no project row yet — intake is the first step
  intake_needed   project exists but the five intake answers aren't complete
  roadmap_needed  intake complete but no validated roadmap stored yet
  in_progress     active project, current-phase tasks remain
  gate_ready      active project, the Interrogation Gate is the next action
                  (all tasks checked off, or a gate session is mid-flight)
  cooldown        the current phase's gate failed < 30 minutes ago
  complete        the final phase's gate is passed — the roadmap is done

Every state is a controlled 200 — never an error. Evaluation only reads: it
never mutates the roadmap, task progress, gate sessions, or unlocks, never
advances phases, and never touches reconnection's last_login_at (it doesn't
even take a ProfileRepository).
"""

from app.services import gate_service, phase_service, unlock_service
from app.services.project_repository import (
    GateSessionRepository,
    ProjectRepository,
    UnlockRepository,
)


def _pre_active(state: str, project: dict | None, next_action: str) -> dict:
    return {
        "state": state,
        "project_status": project.get("status") if project else None,
        "next_action": next_action,
    }


def _recent_gate(project: dict, latest_session: dict | None) -> dict | None:
    """The most recent gate outcome in safe language: a label plus either the
    newest gate_history_summary line (passes — attempt counts only by
    construction) or the evaluator's one-sentence reason (fails — already
    shown to the student at evaluate time). Never a score."""
    if latest_session is not None:
        if latest_session.get("passed") is None:
            return {"outcome": "in_progress", "summary": None}
        if latest_session.get("passed") is False:
            return {"outcome": "failed", "summary": latest_session.get("reason")}
    history = project.get("gate_history_summary")
    if history:  # newest line covers a current-phase final pass too
        return {"outcome": "passed", "summary": history.strip().splitlines()[-1]}
    return None


def _next_action(state: str, view: dict, incomplete: list[dict],
                 cooldown_seconds: int, gate_in_progress: bool) -> str:
    n, title = view["phase"], view["phase_title"]
    if state == "complete":
        return (
            f"You passed the final phase's gate — Phase {n} ({title}) closes "
            "out your roadmap. Review your phases and earned unlocks."
        )
    if state == "cooldown":
        minutes = max(1, -(-cooldown_seconds // 60))  # ceil
        return (
            f"The Phase {n} ({title}) gate can be retried in about "
            f"{minutes} minute(s) — revisit the phase concept and your own "
            "implementation, then try again."
        )
    if gate_in_progress:
        return f"Resume your in-progress Phase {n} ({title}) Interrogation Gate."
    if state == "gate_ready":
        return (
            f"All Phase {n} ({title}) tasks are checked off — take the "
            "Interrogation Gate to advance."
        )
    return (
        f"Continue Phase {n} ({title}): {len(incomplete)} task(s) remain, "
        "then take the Interrogation Gate."
    )


async def get_evaluation(
    project_repo: ProjectRepository,
    gate_repo: GateSessionRepository,
    unlock_repo: UnlockRepository,
    user_id: str,
) -> dict:
    """Safe evaluation of the user's current project. Pure read — every
    branch is a controlled state, never an error."""
    project = await project_repo.get_project(user_id)
    if project is None:
        return _pre_active(
            "not_started", None,
            "Start your project: answer the five intake questions, beginning "
            "with the problem you want to solve.",
        )
    if not project.get("intake_completed_at") or not project.get("archetype_id"):
        return _pre_active(
            "intake_needed", project,
            "Finish the five intake questions so Codize can classify your "
            "project and build your roadmap.",
        )
    if not project.get("roadmap") or project.get("status") != "active":
        return _pre_active(
            "roadmap_needed", project,
            "Generate your roadmap to open the phase workspace.",
        )

    view = phase_service.current_phase_view(project)
    incomplete = phase_service.incomplete_tasks(view)
    sessions = await gate_repo.list_phase_sessions(user_id, project["id"], view["phase"])
    latest = sessions[0] if sessions else None
    total_phases = len(project["roadmap"]["phases"])
    cooldown_seconds = gate_service.cooldown_remaining(latest)
    gate_in_progress = latest is not None and latest.get("passed") is None

    if latest is not None and latest.get("passed") is True:
        # Only reachable on the final phase: passing any earlier phase
        # advances current_phase, so its sessions are no longer "current".
        state = "complete"
    elif gate_in_progress:
        state = "gate_ready"  # a session is mid-flight — resume it
    elif cooldown_seconds > 0:
        state = "cooldown"
    elif not incomplete:
        state = "gate_ready"
    else:
        state = "in_progress"

    evaluation = {
        "state": state,
        "project_status": project["status"],
        "current_phase": view["phase"],
        "phase_title": view["phase_title"],
        "total_phases": total_phases,
        # The gate, not the checklist, completes a phase: phases pass strictly
        # in order, one at a time, so the count falls out of current_phase.
        "completed_phases": total_phases if state == "complete" else view["phase"] - 1,
        "completed_task_count": view["completed_task_count"],
        "total_task_count": view["total_task_count"],
        "incomplete_tasks": incomplete,
        "recent_gate": _recent_gate(project, latest),
        "unlocks": await unlock_service.unlock_views(unlock_repo, user_id, project),
        "next_action": _next_action(state, view, incomplete, cooldown_seconds,
                                    gate_in_progress),
    }
    if state == "cooldown":
        evaluation["cooldown_seconds_remaining"] = cooldown_seconds
    return evaluation
