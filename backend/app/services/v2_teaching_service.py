"""Phase 5 adaptive teaching application layer."""

from __future__ import annotations

from uuid import UUID

from app.schemas.v2 import (
    CheckPlanRequest,
    EffortAttemptRequest,
    EffortAttemptResponse,
    EffortFeedbackView,
    TeachingCommandResponse,
    TeachingHelpRequest,
    TeachingInteractionView,
    TeachingResponseRequest,
)
from app.services.v2_current_change_service import current_change_view
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_repository import (
    V2Repository,
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)
from app.services.v2_teaching_policy import (
    EVIDENCE_POLICY_VERSION,
    RISK_POLICY_VERSION,
    TEACHING_POLICY_VERSION,
    Elicitation,
    EvidenceObservation,
    RiskMode,
    SupportLevel,
    TeachingMode,
    derive_learner_status,
    classify_risk,
    mode_for_evidence,
    recommend_effort,
    resolve_teaching_decision,
    risk_input_fingerprint,
    risk_relevant_text,
)


def _translate(exc: Exception, message: str) -> Exception:
    if isinstance(exc, V2RepositoryNotFound):
        return V2NotFoundError("V2 Project or Current Change not found.")
    if isinstance(exc, (V2RepositoryConflict, V2RepositoryInvalidState)):
        return V2ConflictError(message)
    return exc


def _observations(items) -> list[EvidenceObservation]:
    return [
        EvidenceObservation(
            competency_key=item.competency_key,
            elicitation=Elicitation(item.elicitation),
            support_level=SupportLevel(item.support_level.value),
            observed_at=item.observed_at,
            source_current_change_id=(
                str(item.source_current_change_id) if item.source_current_change_id else None
            ),
            status=item.status,
        )
        for item in items
    ]


def _evidence_qualification(mode: TeachingMode, disclosed) -> tuple[str, str]:
    support = SupportLevel(disclosed.value)
    if support in {SupportLevel.NUDGE, SupportLevel.CLUE}:
        return Elicitation.AFTER_HINT.value, support.value
    if support is SupportLevel.TEACH or mode is TeachingMode.TEACH:
        return Elicitation.TAUGHT.value, SupportLevel.TEACH.value
    if mode is TeachingMode.SKIP:
        return Elicitation.SPONTANEOUS.value, SupportLevel.NONE.value
    # ASK and REMIND describe the policy-selected presentation. Neither proves
    # that the learner consumed Help in this interaction.
    return Elicitation.ASKED.value, SupportLevel.NONE.value


def _support_for_context(change, *, context: str, target: str | None = None) -> SupportLevel:
    """Read help only from the interaction that is currently being answered."""

    active_key = (
        (target or change.teaching_target or "define_done")
        if context == "prebuild"
        else "testing" if context in {"verification", "recovery_recheck"}
        else "debugging" if context.startswith("recovery_")
        else "causal_explanation"
    )
    if change.help_context_key != active_key:
        return SupportLevel.NONE
    return SupportLevel(change.support_level_disclosed.value)


async def resolve_policy(
    repo: V2Repository,
    owner: str,
    project_id: UUID,
    current_change_id: UUID,
    expected_version: int,
    command_id: UUID,
):
    change = await repo.get_current_change_by_id(owner, project_id, current_change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    plan = await repo.get_plan(owner, project_id)
    plan_done = next(
        (item.intended_outcome for item in plan.items if item.id == change.plan_item_id),
        None,
    ) if plan is not None else None
    evidence = await repo.list_learner_evidence(owner)
    decision = resolve_teaching_decision(
        goal=change.goal_snapshot,
        done_condition=change.done_condition_snapshot or plan_done,
        boundaries=change.boundary_snapshots,
        evidence=_observations(evidence),
        prompt_draft=change.prompt_draft,
    )
    fingerprint = risk_input_fingerprint(
        change.goal_snapshot,
        change.done_condition_snapshot or plan_done,
        change.boundary_snapshots,
        change.prompt_draft,
    )
    try:
        return await repo.resolve_teaching_policy(
            owner,
            project_id,
            current_change_id,
            expected_version,
            command_id,
            {
                "mode": decision.mode.value,
                "target": decision.target,
                "reason_key": decision.reason_key,
                "teaching_policy_version": TEACHING_POLICY_VERSION,
                "risk": decision.risk.value,
                "risk_reason_key": decision.risk_reason_key,
                "risk_policy_version": RISK_POLICY_VERSION,
                "risk_input_fingerprint": fingerprint,
                "check_requirement": decision.check_requirement,
            },
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The teaching decision changed. Reload this change.") from exc


_TARGET_COPY = {
    "define_done": {
        "title": "Make “done” specific",
        "explanation": "A useful coding prompt gives you a result you can actually try afterward.",
        "example": "For this change, describe what you would type, click, or see when it works.",
        "question": "What should you actually be able to do when this change is finished?",
        "reminder": "Remember: make the result observable, not just “build the feature.”",
    },
    "protect_working_behavior": {
        "title": "Protect what already works",
        "explanation": "A boundary tells your coding AI which working part does not need to change.",
        "example": "Name one existing behavior this change should leave alone.",
        "question": "What should your coding AI leave alone while it makes this change?",
        "reminder": "Remember to name one working part that should stay untouched.",
    },
    "data_ownership": {
        "title": "Slow down around access",
        "explanation": "This change affects who can access data, so the boundary matters more than usual.",
        "example": "Think about what the intended user may do and what another user must not be able to do.",
        "question": "What access must this change allow, and what access must it prevent?",
        "reminder": "Be explicit about both allowed and disallowed access.",
    },
    "effort_selection": {
        "title": "Choose effort intentionally",
        "explanation": "Match the agent's thinking effort to the size and consequence of this change.",
        "example": "A bounded feature is usually Standard; security-sensitive work is usually Deep.",
        "question": "What about this change should influence your effort choice?",
        "reminder": "Choose effort from the task's complexity and risk, not habit.",
    },
    "testing": {
        "title": "Check what actually happened",
        "explanation": "A coding agent saying it finished is a claim. A check is something you personally try and observe.",
        "example": "Use the result you called “done” and turn it into one action you can try in the app.",
        "question": "What would you actually try in the app to know this change worked?",
        "reminder": "Remember: pick something you can try yourself, not something the AI claimed.",
    },
    "causal_explanation": {
        "title": "One thing worth understanding",
        "explanation": "You do not need to explain every generated line. Focus on the important cause-and-effect relationship in this change.",
        "example": "Name what action or condition now causes the new behavior.",
        "question": "What now causes this change's important behavior to happen?",
        "reminder": "Focus on what causes the behavior, not polished technical vocabulary.",
    },
    "debugging": {
        "title": "Investigate before changing more code",
        "explanation": "A symptom is what you observed. A cause is still a hypothesis until evidence supports it.",
        "example": "Name the first visible difference, then ask the coding AI to point to code or behavior that could explain it.",
        "question": "What did you actually observe, without guessing at the cause?",
        "reminder": "Keep observations separate from coding-agent suggestions and verified results.",
    },
}


def intervention_view(change, progress, *, context: str = "prebuild", mode=None, target=None):
    selected_target = target or change.teaching_target or "define_done"
    selected_mode = mode or TeachingMode(change.teaching_mode.value)
    copy = _TARGET_COPY.get(selected_target, _TARGET_COPY["define_done"])
    hint_text = None
    # The Current Change carries the currently active context's disclosed
    # support. Historical Build Turns are used for answered/attempt progress,
    # not to leak a hint from one competency into another.
    hint = _support_for_context(change, context=context, target=selected_target)
    if hint is SupportLevel.NUDGE:
        hint_text = (
            "Name the first visible thing that differed from what you expected."
            if selected_target == "debugging"
            else "Think about one concrete action or result in this project."
        )
    elif hint is SupportLevel.CLUE:
        hint_text = copy["example"]
    elif hint is SupportLevel.TEACH:
        hint_text = f"{copy['explanation']} {copy['example']}"
    return TeachingInteractionView(
        context=context,
        competency_key=selected_target,
        mode=selected_mode.value,
        risk=change.risk,
        risk_reason_key=change.risk_reason_key,
        title=copy["title"],
        explanation=copy["explanation"] if selected_mode is TeachingMode.TEACH else None,
        example=copy["example"] if selected_mode is TeachingMode.TEACH else None,
        question=(copy["question"] if selected_mode in {TeachingMode.ASK, TeachingMode.TEACH} else None),
        reminder=(copy["reminder"] if selected_mode is TeachingMode.REMIND else None),
        hint_level=hint.value,
        hint_text=hint_text,
        can_request_help=(selected_mode in {
            TeachingMode.ASK, TeachingMode.REMIND, TeachingMode.TEACH
        }
                          and hint is not SupportLevel.TEACH),
    )


async def learner_statuses(repo: V2Repository, owner: str, keys: list[str]) -> dict[str, str]:
    evidence = _observations(await repo.list_learner_evidence(owner, keys))
    return {key: derive_learner_status(evidence, key).value for key in keys}


async def teaching_mode_for(repo: V2Repository, owner: str, competency_key: str) -> TeachingMode:
    evidence = _observations(await repo.list_learner_evidence(owner, [competency_key]))
    return mode_for_evidence(evidence, competency_key)


async def verification_mode_for(repo: V2Repository, owner: str, change) -> TeachingMode:
    """Apply the verification-specific slowdown floor to normal evidence fading."""

    base_mode = await teaching_mode_for(repo, owner, "testing")
    return verification_mode(base_mode, RiskMode(change.risk.value))


def verification_mode(base_mode: TeachingMode, risk: RiskMode) -> TeachingMode:
    return TeachingMode.TEACH if risk is RiskMode.SLOWDOWN else base_mode


def verification_plan_source(mode: TeachingMode) -> str:
    """New/slowdown learners receive a Check; all faded modes originate one."""

    return "codize" if mode is TeachingMode.TEACH else "student"


def current_risk(change):
    text = risk_relevant_text(
        change.goal_snapshot,
        change.done_condition_snapshot,
        change.boundary_snapshots,
        change.prompt_draft,
    )
    return classify_risk(text), risk_input_fingerprint(
        change.goal_snapshot,
        change.done_condition_snapshot,
        change.boundary_snapshots,
        change.prompt_draft,
    )


def risk_is_fresh(change) -> bool:
    decision, fingerprint = current_risk(change)
    return (
        change.risk_policy_version == RISK_POLICY_VERSION
        and change.risk_input_fingerprint == fingerprint
        and change.risk.value == decision.mode.value
        and change.risk_reason_key == decision.reason_key
    )


def understanding_is_required(change) -> bool:
    """Require one short transfer only for a current consequential reason."""

    return (
        change.risk.value == RiskMode.SLOWDOWN.value
        or bool(change.unresolved_uncertainty_summary)
        or change.teaching_target == "causal_explanation"
    )


async def disclose_help(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: TeachingHelpRequest,
) -> TeachingCommandResponse:
    try:
        change, replayed = await repo.disclose_teaching_help(
            owner, project_id, change_id, request.expected_current_change_version,
            request.command_id, request.context,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The help state changed. Reload before asking again.") from exc
    return TeachingCommandResponse(current_change=current_change_view(change), replayed=replayed)


async def record_response(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: TeachingResponseRequest,
) -> TeachingCommandResponse:
    current = await repo.get_current_change_by_id(owner, project_id, change_id)
    if current is None:
        raise V2NotFoundError("V2 Current Change not found.")
    if (request.response.lower() == "continue"
            and not (request.context == "prebuild"
                     and current.teaching_mode.value == TeachingMode.REMIND.value)):
        raise V2ConflictError("Continue is available only for a reminder.")
    if request.context == "prebuild":
        mode = TeachingMode(current.teaching_mode.value)
    else:
        mode = await teaching_mode_for(repo, owner, "causal_explanation")
    elicitation, support = _evidence_qualification(
        mode, _support_for_context(current, context=request.context)
    )
    try:
        change, replayed = await repo.record_teaching_response(
            owner, project_id, change_id, request.expected_current_change_version,
            request.command_id, request.context, request.response,
            elicitation, support,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The teaching response changed or could not be saved.") from exc
    return TeachingCommandResponse(current_change=current_change_view(change), replayed=replayed)


async def record_effort(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: EffortAttemptRequest,
) -> EffortAttemptResponse:
    change = await repo.get_current_change_by_id(owner, project_id, change_id)
    if change is None:
        raise V2NotFoundError("V2 Current Change not found.")
    recommended = recommend_effort(
        risk_relevant_text(
            change.goal_snapshot,
            change.done_condition_snapshot,
            change.boundary_snapshots,
            change.prompt_draft,
        ),
        RiskMode(change.risk.value),
    )
    appropriate = request.effort is recommended
    try:
        updated, feedback, replayed = await repo.record_effort_attempt(
            owner, project_id, change_id, request.expected_current_change_version,
            request.command_id, request.effort.value, recommended.value, appropriate,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The effort decision changed. Reload before trying again.") from exc
    return EffortAttemptResponse(
        current_change=current_change_view(updated),
        feedback=EffortFeedbackView.model_validate(feedback), replayed=replayed,
    )


async def create_check_plan(
    repo: V2Repository, owner: str, project_id: UUID, change_id: UUID,
    request: CheckPlanRequest,
):
    try:
        prior = await repo.get_student_check_plan_replay(
            owner, project_id, change_id, request.command_id,
            request.check_id, request.check_plan,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The check plan command conflicts with its saved result.") from exc
    if prior is not None:
        from app.schemas.v2 import ManualLoopResponse
        from app.services.v2_manual_loop_service import check_view
        change, check = prior
        return ManualLoopResponse(
            current_change=current_change_view(change), check=check_view(check), replayed=True
        )
    current = await repo.get_current_change_by_id(owner, project_id, change_id)
    if current is None:
        raise V2NotFoundError("V2 Current Change not found.")
    mode = await verification_mode_for(repo, owner, current)
    elicitation, support = _evidence_qualification(
        mode, _support_for_context(current, context="verification", target="testing")
    )
    try:
        change, check, replayed = await repo.create_student_check_plan(
            owner, project_id, change_id, request.expected_current_change_version,
            request.command_id, request.check_id, request.check_plan,
            elicitation, support,
        )
    except (V2RepositoryNotFound, V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise _translate(exc, "The check plan changed or could not be saved.") from exc
    from app.schemas.v2 import ManualLoopResponse
    from app.services.v2_manual_loop_service import check_view
    return ManualLoopResponse(
        current_change=current_change_view(change), check=check_view(check), replayed=replayed
    )
