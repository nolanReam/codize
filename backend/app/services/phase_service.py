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

import hashlib
import json

from app.services.project_repository import ProjectRepository

# Task ids are "<list>-<1-based index>" into the roadmap phase's task lists.
# The roadmap structure is immutable after generation, so indexes are stable.
_TASK_LISTS = {"ai": "ai_appropriate_tasks", "human": "human_required_tasks"}
_ASSIGNMENTS_KEY = "_phase_assignments"
_MAX_TASK_PROGRESS_RETRIES = 3


class PhaseWorkspaceError(Exception):
    """Base for controlled workspace errors; messages are safe client strings."""


class WorkspaceNotReadyError(PhaseWorkspaceError):
    """No project, intake incomplete, no roadmap, or project not active."""


class PhaseNotFoundError(PhaseWorkspaceError):
    """Phase number is not in this roadmap."""


class TaskNotFoundError(PhaseWorkspaceError):
    """Task id does not resolve to a task in this phase."""


class TaskProgressConflictError(PhaseWorkspaceError):
    """Concurrent task-state writes did not settle after bounded retries."""


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
    valid: set[str] = set()
    for prefix, field in _TASK_LISTS.items():
        tasks = phase.get(field)
        if not isinstance(tasks, list):
            continue
        for index in range(1, len(tasks) + 1):
            task_id = f"{prefix}-{index}"
            if resolve_task(phase, task_id) is not None:
                valid.add(task_id)
    return valid


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
    tasks = phase.get(_TASK_LISTS[prefix])
    if not isinstance(tasks, list):
        return []
    entries: list[dict] = []
    for index in range(1, len(tasks) + 1):
        resolved = resolve_task(phase, f"{prefix}-{index}", completed)
        if resolved is not None:
            entries.append(
                {
                    "task_id": resolved["task_id"],
                    "description": resolved["description"],
                    "completed": resolved["completed"],
                }
            )
    return entries


def resolve_task(phase: dict, task_id: str, completed: set[str] | None = None) -> dict | None:
    """Resolve a stable phase-local roadmap id into server-owned task truth."""
    try:
        prefix, raw_index = task_id.split("-", 1)
        index = int(raw_index)
    except (AttributeError, TypeError, ValueError):
        return None
    field = _TASK_LISTS.get(prefix)
    tasks = phase.get(field) if field else None
    if not isinstance(tasks, list) or index < 1 or index > len(tasks):
        return None
    description = tasks[index - 1]
    if not isinstance(description, str) or not description.strip():
        return None
    return {
        "task_id": task_id,
        "description": description,
        "completed": task_id in (completed or set()),
        "owner": "ai" if prefix == "ai" else "student",
        "owner_label": "Use AI" if prefix == "ai" else "You decide",
    }


def _assignment_candidates(project: dict, phase: dict) -> list[dict]:
    completed = _completed_ids(project, phase)
    result: list[dict] = []
    for prefix in ("ai", "human"):
        tasks = phase.get(_TASK_LISTS[prefix])
        if not isinstance(tasks, list):
            continue
        for index in range(1, len(tasks) + 1):
            task = resolve_task(phase, f"{prefix}-{index}", completed)
            if task is not None:
                result.append(task)
    return result


def _stored_assignment(project: dict, phase_number: int) -> dict | None:
    progress = project.get("task_progress")
    assignments = progress.get(_ASSIGNMENTS_KEY) if isinstance(progress, dict) else None
    stored = assignments.get(str(phase_number)) if isinstance(assignments, dict) else None
    if not isinstance(stored, dict):
        return None
    task_id = stored.get("task_id")
    selected_while_completed = stored.get("selected_while_completed")
    roadmap_fingerprint = stored.get("roadmap_fingerprint")
    if (
        not isinstance(task_id, str)
        or not isinstance(selected_while_completed, bool)
        or not isinstance(roadmap_fingerprint, str)
    ):
        return {"invalid": True}
    return {
        "task_id": task_id,
        "selected_while_completed": selected_while_completed,
        "roadmap_fingerprint": roadmap_fingerprint,
    }


def _roadmap_fingerprint(project: dict) -> str:
    canonical = json.dumps(
        project.get("roadmap"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assignment_revision(project: dict) -> str:
    """Opaque revision for binding assignment-scoped Prompt work.

    Task ids are phase-local positions and may be reused after a roadmap
    replacement. Exposing only the roadmap fingerprint lets clients keep old
    drafts under their original binding without exposing roadmap content or
    accepting client-authored authority.
    """
    return _roadmap_fingerprint(project)


def current_assignment_view(project: dict) -> dict:
    """Authoritative current-phase selection or deterministic recommendation."""
    phase = _find_phase(project, project["current_phase"])
    candidates = _assignment_candidates(project, phase)
    stored = _stored_assignment(project, phase["phase"])
    selected = None
    invalidated = False
    previous_selection = None
    if stored:
        if stored.get("invalid") or stored.get("roadmap_fingerprint") != _roadmap_fingerprint(project):
            invalidated = True
        else:
            selected = next((task for task in candidates if task["task_id"] == stored["task_id"]), None)
            if selected is None:
                invalidated = True
            elif selected["completed"] and not stored["selected_while_completed"]:
                previous_selection = selected
                selected = None

    if selected is not None:
        selected = dict(selected)
        selected["reason"] = (
            "You chose to revisit this completed current-phase task."
            if selected["completed"]
            else "You selected this current-phase task."
        )
        return {
            "phase": phase["phase"],
            "phase_title": phase["phase_title"],
            "assignment_revision": assignment_revision(project),
            "state": "selected",
            "assignment": selected,
            "previous_selection": None,
            "invalidated_selection": False,
        }

    recommended = next((task for task in candidates if not task["completed"]), None)
    if recommended is not None:
        recommended = dict(recommended)
        recommended["reason"] = (
            "This is the next incomplete AI-appropriate task in the current phase."
            if recommended["owner"] == "ai"
            else "The AI-appropriate work is complete; this is the next decision for you to make."
        )
        return {
            "phase": phase["phase"],
            "phase_title": phase["phase_title"],
            "assignment_revision": assignment_revision(project),
            "state": "recommended",
            "assignment": recommended,
            "previous_selection": previous_selection,
            "invalidated_selection": invalidated,
        }

    return {
        "phase": phase["phase"],
        "phase_title": phase["phase_title"],
        "assignment_revision": assignment_revision(project),
        "state": "phase_complete" if candidates else "no_valid_task",
        "assignment": None,
        "previous_selection": previous_selection,
        "invalidated_selection": invalidated,
    }


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


def require_phase(project: dict, phase_number: int) -> dict:
    """Validate a phase number against an already-loaded project's roadmap
    (PhaseNotFoundError if absent) — shared with the workflow artifact store
    (M13B), which scopes artifacts to real roadmap phases."""
    return _find_phase(project, phase_number)


def current_phase_view(project: dict) -> dict:
    """Full view of an already-loaded active project's current phase — shared
    with the reconnection (M11) and evaluation (M12) services, which load the
    project once themselves."""
    return _phase_view(project, _find_phase(project, project["current_phase"]))


def phase_view(project: dict, phase_number: int) -> dict:
    """Full view of any phase of an already-loaded active project
    (PhaseNotFoundError if absent) — shared with the defense context builder
    (M14A), which loads the project once itself."""
    return _phase_view(project, _find_phase(project, phase_number))


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


async def get_current_assignment(repo: ProjectRepository, user_id: str) -> dict:
    project = await load_active_project(repo, user_id)
    return current_assignment_view(project)


async def select_current_assignment(
    repo: ProjectRepository, user_id: str, task_id: str
) -> dict:
    """Persist one explicit current-phase task without touching completion state."""
    for _ in range(_MAX_TASK_PROGRESS_RETRIES):
        project = await load_active_project(repo, user_id)
        phase = _find_phase(project, project["current_phase"])
        completed = _completed_ids(project, phase)
        task = resolve_task(phase, task_id, completed)
        if task is None:
            raise TaskNotFoundError(
                "That task is not available in the current phase. Choose a current-phase task."
            )

        stored = project.get("task_progress")
        expected = dict(stored) if isinstance(stored, dict) else {}
        progress = dict(expected)
        raw_assignments = progress.get(_ASSIGNMENTS_KEY)
        assignments = dict(raw_assignments) if isinstance(raw_assignments, dict) else {}
        assignments[str(phase["phase"])] = {
            "task_id": task_id,
            "selected_while_completed": task["completed"],
            "roadmap_fingerprint": _roadmap_fingerprint(project),
        }
        progress[_ASSIGNMENTS_KEY] = assignments
        updated = await repo.update_task_progress_if_current(
            user_id, project["id"], expected, progress
        )
        if updated is not None:
            return current_assignment_view(updated)
    raise TaskProgressConflictError(
        "Task state changed in another tab. Reload Project Home and choose again."
    )


async def set_task_completion(
    repo: ProjectRepository, user_id: str, phase_number: int, task_id: str, completed: bool
) -> dict:
    for _ in range(_MAX_TASK_PROGRESS_RETRIES):
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
        expected = dict(stored) if isinstance(stored, dict) else {}
        progress = dict(expected)
        progress[str(phase_number)] = sorted(
            done, key=lambda t: (t.split("-")[0], int(t.split("-")[1]))
        )
        # The write touches ONLY task_progress — roadmap, status, and current_phase
        # cannot change through the workspace.
        updated = await repo.update_task_progress_if_current(
            user_id, project["id"], expected, progress
        )
        if updated is not None:
            return _phase_view(updated, phase)
    raise TaskProgressConflictError(
        "Task state changed in another tab. Reload Project Home and try again."
    )
