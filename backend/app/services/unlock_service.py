"""Functional unlock engine (Milestone 10).

Unlocks reward demonstrated quality, never phase completion (spec Section 4):
the hidden rule — locked by the spec's resolved decisions — is a gate quality
score of at least QUALIFYING_SCORE on two consecutive phases' passed gates.
Only the passing attempt's score counts (no retry deductions); a phase whose
gate was never passed contributes nothing, so a failure can never earn an
unlock. The reward granted for qualifying at phase N is roadmap phase N's
`functional_unlock` — template-defined content that skips configuration work
or provides a pre-built component for an upcoming phase.

The threshold, the rule, and the raw scores are server-only. Client responses
carry only the unlock row plus the roadmap's reward description — data the
student may see. The score column itself is revoked from client roles (M2/M9),
and this module never puts a score or threshold in any returned view.

Evaluation recomputes the full earned set from passed-gate history on every
call and inserts only what's missing, so it is idempotent and self-healing:
a grant missed to a transient storage error is re-attempted at the next PASS.
Unlocks never mutate the roadmap and never advance phases — they only add
rows to the owner-read-only `unlocks` table.
"""

from app.services.project_repository import (
    GateSessionRepository,
    ProjectRepository,
    UnlockRepository,
)

# Hidden threshold (spec: "Score >=7 across two consecutive phases triggers
# first functional unlock"). Server-only — never serialized into a response.
QUALIFYING_SCORE = 7


def _unlock_key(phase_number: int) -> str:
    return f"phase-{phase_number}-functional-unlock"


def qualifying_phases(phase_scores: dict[int, int]) -> set[int]:
    """Phases whose passed-gate score AND the previous phase's passed-gate
    score both meet the hidden threshold. Phase 1 alone can never qualify."""
    return {
        n for n, score in phase_scores.items()
        if score >= QUALIFYING_SCORE
        and (n - 1) in phase_scores
        and phase_scores[n - 1] >= QUALIFYING_SCORE
    }


def _reward_description(project: dict, phase_number: int) -> str | None:
    for phase in (project.get("roadmap") or {}).get("phases", []):
        if phase["phase"] == phase_number:
            return phase.get("functional_unlock")
    return None


def _view(row: dict, project: dict) -> dict:
    """Client-safe unlock view — never scores, thresholds, or rule internals."""
    return {
        "id": row["id"],
        "unlock_key": row["unlock_key"],
        "project_id": row["project_id"],
        "phase": row["phase_number"],
        "description": _reward_description(project, row["phase_number"]),
        "unlocked_at": row["granted_at"],
    }


async def evaluate_unlocks(
    gate_repo: GateSessionRepository,
    unlock_repo: UnlockRepository,
    user_id: str,
    project: dict,
) -> list[dict]:
    """Grant any earned-but-missing unlocks; returns the newly granted views.

    Called from the gate flow after a PASS (never after a FAIL). Recomputes
    from all passed sessions, so repeated calls insert nothing new; the DB's
    unique (project_id, unlock_key) additionally ignores duplicate inserts.
    """
    passed = await gate_repo.list_passed_sessions(user_id, project["id"])
    scores = {
        s["phase_id"]: s["score"] for s in passed
        if s.get("passed") is True and isinstance(s.get("score"), int)
    }
    earned = qualifying_phases(scores)
    if not earned:
        return []
    existing = {u["unlock_key"] for u in await unlock_repo.list_unlocks(user_id, project["id"])}
    granted = []
    for n in sorted(earned):
        if _unlock_key(n) in existing:
            continue
        row = await unlock_repo.create_unlock(
            user_id,
            {"project_id": project["id"], "phase_number": n, "unlock_key": _unlock_key(n)},
        )
        if row is not None:  # None: another writer got there first — not new
            granted.append(_view(row, project))
    return granted


async def unlock_views(
    unlock_repo: UnlockRepository, user_id: str, project: dict
) -> list[dict]:
    """Client-safe views of every unlock earned on an already-loaded project —
    shared with the reconnection service (M11)."""
    rows = await unlock_repo.list_unlocks(user_id, project["id"])
    return [_view(r, project) for r in rows]


async def list_unlocks(
    project_repo: ProjectRepository, unlock_repo: UnlockRepository, user_id: str
) -> dict:
    """Earned unlocks for the user's current project. No project (or none
    earned) is simply an empty list — not an error."""
    project = await project_repo.get_project(user_id)
    if project is None:
        return {"unlocks": []}
    return {"unlocks": await unlock_views(unlock_repo, user_id, project)}
