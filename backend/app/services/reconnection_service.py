"""Yeager reconnection engine (Milestone 11).

The spec's mechanic: when a student returns after 72+ hours away, an in-app
modal surfaces their verbatim intake purpose before the workspace loads,
dismissed only by clicking "Let's keep building" (frontend concern — this
module is the state machine and safe summary behind it).

Timestamp semantics (the load-bearing decision): `profiles.last_login_at`
means "last acknowledged presence in the app". It is initialized by the
signup trigger's `default now()` — so a brand-new user is never shown the
modal — and thereafter written ONLY by POST /reconnection/acknowledge.
GET /reconnection never writes, so checking state can never suppress the
modal. Frontend contract: on every login, GET /reconnection first; then call
acknowledge — immediately when `reconnection_needed` is false, on the
"Let's keep building" click when it is true.

The summary is deliberately deterministic (no LLM call) and built only from
data the client may already see: verbatim intake purpose, the current phase
view (minus its full task lists — just what's left to do), the last
gate-history line (attempt counts only — never scores), and earned unlock
views. Raw gate scores, the unlock threshold/rule, evaluator internals, and
prompts appear nowhere. Reconnection never mutates the roadmap, never
advances phases, and never grants unlocks — it only reads, plus the one
`last_login_at` write on acknowledge.
"""

from datetime import datetime, timedelta, timezone

from app.services import phase_service, unlock_service
from app.services.project_repository import (
    ProfileRepository,
    ProjectRepository,
    UnlockRepository,
)

# Spec: reconnection surfaces when the student has been away 72+ hours.
AWAY_THRESHOLD = timedelta(hours=72)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _incomplete_tasks(phase_view: dict) -> list[dict]:
    return [
        {"task_id": t["task_id"], "description": t["description"]}
        for field in ("ai_appropriate_tasks", "human_required_tasks")
        for t in phase_view[field]
        if not t["completed"]
    ]


def _last_gate_summary(project: dict) -> str | None:
    """The newest line of gate_history_summary — attempt counts only by
    construction (gate_service never writes scores into it)."""
    history = project.get("gate_history_summary")
    return history.strip().splitlines()[-1] if history else None


def _next_action(phase_view: dict, incomplete: list[dict]) -> str:
    n, title = phase_view["phase"], phase_view["phase_title"]
    if incomplete:
        return (
            f"Continue Phase {n} ({title}): {len(incomplete)} task(s) remain, "
            "then take the Interrogation Gate."
        )
    return (
        f"All Phase {n} ({title}) tasks are checked off — take the "
        "Interrogation Gate to advance."
    )


async def _build_summary(
    unlock_repo: UnlockRepository, user_id: str, project: dict
) -> dict:
    view = phase_service.current_phase_view(project)
    incomplete = _incomplete_tasks(view)
    return {
        "intake_purpose": project["intake_purpose"],  # spec: shown verbatim
        "current_phase": view["phase"],
        "phase_title": view["phase_title"],
        "phase_reminder": view["core_concept"],
        "incomplete_tasks": incomplete,
        "last_gate_summary": _last_gate_summary(project),
        "unlocks": await unlock_service.unlock_views(unlock_repo, user_id, project),
        "next_action": _next_action(view, incomplete),
    }


async def get_reconnection_state(
    profile_repo: ProfileRepository,
    project_repo: ProjectRepository,
    unlock_repo: UnlockRepository,
    user_id: str,
) -> dict:
    """Pure read: does this user need the reconnection modal, and with what
    summary? Every branch is a controlled state — never an error."""
    profile = await profile_repo.get_profile(user_id)
    last_seen = _parse_ts(profile.get("last_login_at")) if profile else None
    if last_seen is None:
        # No profile row (or no timestamp) means no history to reconnect to —
        # live, the signup trigger guarantees a fresh timestamp instead.
        return {"reconnection_needed": False, "state": "new_user"}
    if _now() - last_seen < AWAY_THRESHOLD:
        return {"reconnection_needed": False, "state": "recently_active"}

    try:
        project = await phase_service.load_active_project(project_repo, user_id)
    except phase_service.WorkspaceNotReadyError:
        # Away 72h+ but nothing to reconnect to yet (no project or roadmap):
        # controlled "not ready" — the intake flow is the next step, not a modal.
        return {"reconnection_needed": False, "state": "workspace_not_ready"}

    return {
        "reconnection_needed": True,
        "state": "reconnection",
        "summary": await _build_summary(unlock_repo, user_id, project),
    }


async def acknowledge(profile_repo: ProfileRepository, user_id: str) -> dict:
    """Record acknowledged presence: set last_login_at to now. Idempotent —
    repeat calls just refresh the timestamp for the caller's own row."""
    profile = await profile_repo.set_last_login(user_id, _now().isoformat())
    return {"acknowledged": True, "last_login_at": profile["last_login_at"]}
