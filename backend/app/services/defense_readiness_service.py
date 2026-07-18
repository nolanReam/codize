"""Deterministic formal Project Defense preparation.

Route availability is not readiness. This pure helper combines current-phase
build tasks with saved, phase-scoped workflow truth. It never calls a provider,
reads hidden evaluator data, or mutates lifecycle state.
"""

from app.services import phase_service, workflow_context_service, workflow_service


def _blocker(code: str, label: str, detail: str) -> dict:
    return {"code": code, "label": label, "detail": detail}


def preparation(project: dict, phase: dict) -> dict:
    number = phase["phase"]
    sections = workflow_service.stored_sections(project, number)
    context = workflow_context_service.build_workflow_context(project, number)
    blockers: list[dict] = []

    # Recovery entry may legitimately begin with a saved Import. A missing
    # Prompt alone is therefore not a blocker once Import exists.
    if "prompt_builder" not in sections and "implementation_import" not in sections:
        blockers.append(
            _blocker(
                "prompt_missing",
                "Prompt Builder is not saved",
                "Save the prompt for this phase before formal Project Defense.",
            )
        )
    if workflow_service.get_implementation_import(project, number) is None:
        blockers.append(
            _blocker(
                "import_missing",
                "Implementation Import is missing",
                "Bring back the AI response, diff, changed files, or your own summary.",
            )
        )

    for source_id, label in (
        ("change_map", "Change Map"),
        ("review", "Review"),
        ("verification", "Verification"),
        ("evidence", "Evidence"),
    ):
        state = getattr(context, source_id).state
        if state in {"current", "manual"}:
            continue
        if state == "missing":
            detail = f"Complete {label} for this phase before formal Project Defense."
        elif state == "stale":
            detail = f"Rebuild {label} from the current upstream record before formal Project Defense."
        elif state == "incomplete":
            detail = f"Finish the saved {label} record before formal Project Defense."
        else:
            detail = f"Repair the unreadable {label} record before formal Project Defense."
        blockers.append(_blocker(f"{source_id}_{state}", f"{label} is {state}", detail))

    phase_view = phase_service.phase_view(project, number)
    incomplete_tasks = phase_service.incomplete_tasks(phase_view)
    if incomplete_tasks:
        count = len(incomplete_tasks)
        blockers.append(
            _blocker(
                "build_tasks_incomplete",
                f"{count} phase build task{'s' if count != 1 else ''} remain",
                "Tick each build task only after you actually finish it.",
            )
        )

    return {
        "state": "ready" if not blockers else "not_ready",
        "formal_ready": not blockers,
        "blockers": blockers,
    }


def lifecycle_view(state: str) -> dict:
    return {"state": state, "formal_ready": False, "blockers": []}
