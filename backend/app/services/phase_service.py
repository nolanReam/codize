"""Phase workspace engine (Milestone 8).

The stored roadmap JSONB is the single source of truth for phase content —
personalized wording over the fixed archetype structure, validated fail-closed
at generation time (M7). This module never writes to the roadmap: task
completion lives in the separate projects.task_progress column
({"<phase_number>": ["ai-1", "human-2", ...]}), so marking tasks complete
cannot corrupt the fixed structure by construction.

Eligibility: intake complete + archetype assigned + roadmap stored + status
'active'. projects.current_phase (schema default 1) is the student's position;
it is advanced by the Interrogation Gate (Milestone 9), never by ticking off
tasks — the gate, not the checklist, completes a phase.

No LLM calls here: the roadmap already carries the personalized phase content,
so the phase_explanation.md prose call is deliberately not wired up yet.
"""

from app.services.project_repository import ProjectRepository

# Task ids are "<list>-<1-based index>" into the roadmap phase's task lists.
# The roadmap structure is immutable after generation, so indexes are stable.
_TASK_LISTS = {"ai": "ai_appropriate_tasks", "human": "human_required_tasks"}


class PhaseWorkspaceError(Exception):
    """Base for controlled workspace errors; messages are safe client strings."""


class WorkspaceNotReadyError(PhaseWorkspaceError):
    """No project, intake incomplete, no roadmap, or project not active."""


class PhaseNotFoundError(PhaseWorkspaceError):
    """Phase number is not in this roadmap."""


class TaskNotFoundError(PhaseWorkspaceError):
    """Task id does not resolve to a task in this phase."""


async def load_active_project(repo: ProjectRepository, user_id: str) -> dict:
    project = await repo.get_project(user_id)
    if (
        project is None
        or not project.get("intake_completed_at")
        or not project.get("archetype_id")
        or not project.get("roadmap")
        or project.get("status") != "active"
    ):
        raise WorkspaceNotReadyError(
            "The phase workspace needs an active project with a generated roadmap."
        )
    return project


def _find_phase(project: dict, phase_number: int) -> dict:
    for phase in project["roadmap"]["phases"]:
        if phase["phase"] == phase_number:
            return phase
    raise PhaseNotFoundError(f"Phase {phase_number} does not exist in this roadmap.")


def _valid_task_ids(phase: dict) -> set[str]:
    return {
        f"{prefix}-{i}"
        for prefix, field in _TASK_LISTS.items()
        for i in range(1, len(phase[field]) + 1)
    }


def _completed_ids(project: dict, phase: dict) -> set[str]:
    """Completed task ids for one phase. Anything that doesn't resolve to a
    real task in this phase is dropped on read — stored progress can never
    corrupt what the workspace reports."""
    progress = project.get("task_progress")
    stored = progress.get(str(phase["phase"])) if isinstance(progress, dict) else None
    if not isinstance(stored, list):
        return set()
    return {t for t in stored if t in _valid_task_ids(phase)}


def _task_entries(phase: dict, prefix: str, completed: set[str]) -> list[dict]:
    return [
        {
            "task_id": f"{prefix}-{i}",
            "description": task,
            "completed": f"{prefix}-{i}" in completed,
        }
        for i, task in enumerate(phase[_TASK_LISTS[prefix]], start=1)
    ]


def _phase_view(project: dict, phase: dict) -> dict:
    completed = _completed_ids(project, phase)
    return {
        "phase": phase["phase"],
        "phase_title": phase["phase_title"],
        "core_concept": phase["core_concept"],
        "ai_appropriate_tasks": _task_entries(phase, "ai", completed),
        "human_required_tasks": _task_entries(phase, "human", completed),
        "explanation_gate_targets": phase["explanation_gate_targets"],
        "gate_depth": phase["gate_depth"],
        "unlock_condition": phase["unlock_condition"],
        "functional_unlock": phase["functional_unlock"],
        "is_current": phase["phase"] == project.get("current_phase"),
        "completed_task_count": len(completed),
        "total_task_count": len(_valid_task_ids(phase)),
    }


def _phase_summary(project: dict, phase: dict) -> dict:
    return {
        "phase": phase["phase"],
        "phase_title": phase["phase_title"],
        "gate_depth": phase["gate_depth"],
        "is_current": phase["phase"] == project.get("current_phase"),
        "completed_task_count": len(_completed_ids(project, phase)),
        "total_task_count": len(_valid_task_ids(phase)),
    }


async def list_phases(repo: ProjectRepository, user_id: str) -> dict:
    project = await load_active_project(repo, user_id)
    return {
        "current_phase": project["current_phase"],
        "phases": [_phase_summary(project, p) for p in project["roadmap"]["phases"]],
    }


async def get_phase(repo: ProjectRepository, user_id: str, phase_number: int) -> dict:
    project = await load_active_project(repo, user_id)
    return _phase_view(project, _find_phase(project, phase_number))


def current_phase_view(project: dict) -> dict:
    """Full view of an already-loaded active project's current phase — shared
    with the reconnection (M11) and evaluation (M12) services, which load the
    project once themselves."""
    return _phase_view(project, _find_phase(project, project["current_phase"]))


def incomplete_tasks(phase_view: dict) -> list[dict]:
    """The not-yet-completed tasks of a phase view, id + description only —
    shared with the reconnection (M11) and evaluation (M12) services."""
    return [
        {"task_id": t["task_id"], "description": t["description"]}
        for field in ("ai_appropriate_tasks", "human_required_tasks")
        for t in phase_view[field]
        if not t["completed"]
    ]


async def get_current_phase(repo: ProjectRepository, user_id: str) -> dict:
    project = await load_active_project(repo, user_id)
    return current_phase_view(project)


async def set_task_completion(
    repo: ProjectRepository, user_id: str, phase_number: int, task_id: str, completed: bool
) -> dict:
    project = await load_active_project(repo, user_id)
    phase = _find_phase(project, phase_number)
    if task_id not in _valid_task_ids(phase):
        raise TaskNotFoundError(f"Task '{task_id}' does not exist in phase {phase_number}.")

    done = _completed_ids(project, phase)
    if completed:
        done.add(task_id)
    else:
        done.discard(task_id)

    stored = project.get("task_progress")
    progress = dict(stored) if isinstance(stored, dict) else {}
    progress[str(phase_number)] = sorted(done, key=lambda t: (t.split("-")[0], int(t.split("-")[1])))
    # The write touches ONLY task_progress — roadmap, status, and current_phase
    # cannot change through the workspace.
    project = await repo.update_project(user_id, project["id"], {"task_progress": progress})
    return _phase_view(project, phase)
