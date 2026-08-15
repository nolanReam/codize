"""Pure deterministic ProjectRef and Current Change state-machine tests."""

from uuid import UUID

import pytest

from app.domain.v2 import (
    CurrentChangeState,
    IllegalCurrentChangeTransitionError,
    ProjectRef,
    ResumeStep,
    WorkflowVersion,
    WrongWorkflowVersionError,
    allowed_transitions,
    validate_resume_state,
    validate_transition,
)

PROJECT_ID = UUID("10000000-0000-4000-8000-000000000001")


def test_project_refs_keep_v1_and_v2_identity_distinct():
    legacy = ProjectRef(WorkflowVersion.V1, PROJECT_ID)
    current = ProjectRef(WorkflowVersion.V2, PROJECT_ID)
    assert legacy != current
    current.require_v2()
    with pytest.raises(WrongWorkflowVersionError):
        legacy.require_v2()


@pytest.mark.parametrize(
    ("source", "target", "resume_step"),
    [
        (CurrentChangeState.PREPARING, CurrentChangeState.PREPARING, ResumeStep.PROMPT),
        (CurrentChangeState.PREPARING, CurrentChangeState.AWAITING_AGENT, ResumeStep.RETURN_OUTCOME),
        (CurrentChangeState.AWAITING_AGENT, CurrentChangeState.REVIEWING, ResumeStep.CHECK),
        (CurrentChangeState.AWAITING_AGENT, CurrentChangeState.RECOVERING, ResumeStep.RECOVERY_SYMPTOM),
        (CurrentChangeState.REVIEWING, CurrentChangeState.RECOVERING, ResumeStep.RECOVERY_INVESTIGATE),
        (CurrentChangeState.RECOVERING, CurrentChangeState.AWAITING_AGENT, ResumeStep.RETURN_OUTCOME),
        (CurrentChangeState.RECOVERING, CurrentChangeState.REVIEWING, ResumeStep.CHECK),
        (CurrentChangeState.REVIEWING, CurrentChangeState.COMPLETED, None),
        (CurrentChangeState.RECOVERING, CurrentChangeState.COMPLETED, None),
        (CurrentChangeState.PREPARING, CurrentChangeState.CANCELLED, None),
    ],
)
def test_canonical_current_change_transitions_are_legal(source, target, resume_step):
    validate_transition(source, target, resume_step)
    assert target in allowed_transitions(source)


@pytest.mark.parametrize(
    ("source", "target", "resume_step"),
    [
        (CurrentChangeState.PREPARING, CurrentChangeState.COMPLETED, None),
        (CurrentChangeState.AWAITING_AGENT, CurrentChangeState.COMPLETED, None),
        (CurrentChangeState.REVIEWING, CurrentChangeState.PREPARING, ResumeStep.CONFIRM_CHANGE),
        (CurrentChangeState.COMPLETED, CurrentChangeState.REVIEWING, ResumeStep.CHECK),
        (CurrentChangeState.CANCELLED, CurrentChangeState.PREPARING, ResumeStep.CONFIRM_CHANGE),
    ],
)
def test_illegal_current_change_transitions_fail_closed(source, target, resume_step):
    with pytest.raises(IllegalCurrentChangeTransitionError):
        validate_transition(source, target, resume_step)


def test_resume_step_matrix_is_independent_of_lifecycle_transition_choice():
    validate_resume_state(CurrentChangeState.REVIEWING, ResumeStep.INSPECT)
    validate_resume_state(CurrentChangeState.CANCELLED, None)
    with pytest.raises(IllegalCurrentChangeTransitionError):
        validate_resume_state(CurrentChangeState.AWAITING_AGENT, ResumeStep.CHECK)
    with pytest.raises(IllegalCurrentChangeTransitionError):
        validate_resume_state(CurrentChangeState.COMPLETED, ResumeStep.UNDERSTAND)
