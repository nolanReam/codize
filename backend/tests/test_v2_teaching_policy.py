"""Focused tests for the versioned Phase 5 deterministic teaching policy."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.domain.v2 import EffortCategory
from app.services.v2_teaching_policy import (
    EVIDENCE_POLICY_VERSION,
    RISK_POLICY_VERSION,
    TEACHING_POLICY_VERSION,
    Elicitation,
    EvidenceObservation,
    LearnerStatus,
    RiskMode,
    SupportLevel,
    TeachingMode,
    classify_risk,
    derive_learner_status,
    mode_for_status,
    mode_for_evidence,
    next_support_level,
    qualifies_check_plan,
    qualifies_structured_response,
    recommend_effort,
    resolve_teaching_decision,
    risk_input_fingerprint,
)
from app.services import v2_teaching_service

NOW = datetime(2026, 8, 23, 12, tzinfo=UTC)


def observation(
    competency: str,
    *,
    days_ago: int,
    change: str,
    elicitation: Elicitation = Elicitation.ASKED,
    support: SupportLevel = SupportLevel.NONE,
) -> EvidenceObservation:
    return EvidenceObservation(
        competency_key=competency,
        elicitation=elicitation,
        support_level=support,
        observed_at=NOW - timedelta(days=days_ago),
        source_current_change_id=change,
    )


@pytest.mark.parametrize(
    ("evidence", "expected_status", "expected_mode"),
    [
        ([], LearnerStatus.NEW, TeachingMode.TEACH),
        ([observation("define_done", days_ago=2, change="a", support=SupportLevel.NUDGE,
                      elicitation=Elicitation.AFTER_HINT)], LearnerStatus.GUIDED, TeachingMode.ASK),
        ([observation("define_done", days_ago=2, change="a")], LearnerStatus.PRACTICED, TeachingMode.ASK),
        ([observation("define_done", days_ago=20, change="a"),
          observation("define_done", days_ago=2, change="b")],
         LearnerStatus.RECENTLY_INDEPENDENT, TeachingMode.SKIP),
    ],
)
def test_statuses_map_to_skip_ask_remind_teach(evidence, expected_status, expected_mode):
    status = derive_learner_status(evidence, "define_done", now=NOW)
    assert status is expected_status
    assert mode_for_status(status) is expected_mode


def test_fading_is_competency_specific_and_support_can_return():
    evidence = [
        observation("define_done", days_ago=20, change="a"),
        observation("define_done", days_ago=2, change="b"),
    ]
    assert derive_learner_status(evidence, "define_done", now=NOW) is LearnerStatus.RECENTLY_INDEPENDENT
    assert derive_learner_status(evidence, "testing", now=NOW) is LearnerStatus.NEW

    evidence.append(observation(
        "define_done", days_ago=0, change="c",
        elicitation=Elicitation.TAUGHT, support=SupportLevel.TEACH,
    ))
    assert derive_learner_status(evidence, "define_done", now=NOW) is LearnerStatus.GUIDED
    assert mode_for_evidence(evidence, "define_done", now=NOW) is TeachingMode.REMIND


def test_assisted_or_same_change_evidence_never_claims_recent_independence():
    assisted = [
        observation("testing", days_ago=4, change="a", elicitation=Elicitation.AFTER_HINT,
                    support=SupportLevel.CLUE),
        observation("testing", days_ago=1, change="b", elicitation=Elicitation.TAUGHT,
                    support=SupportLevel.TEACH),
    ]
    assert derive_learner_status(assisted, "testing", now=NOW) is LearnerStatus.GUIDED
    same_change = [
        observation("testing", days_ago=4, change="a"),
        observation("testing", days_ago=1, change="a"),
    ]
    assert derive_learner_status(same_change, "testing", now=NOW) is LearnerStatus.PRACTICED


def test_normal_change_can_skip_but_experience_never_bypasses_slowdown():
    evidence = [
        observation("data_ownership", days_ago=10, change="a"),
        observation("data_ownership", days_ago=1, change="b"),
        observation("protect_working_behavior", days_ago=10, change="a"),
        observation("protect_working_behavior", days_ago=1, change="b"),
    ]
    ordinary = resolve_teaching_decision(
        goal="Add a score summary", done_condition="The summary is visible",
        boundaries=(), evidence=evidence, now=NOW,
    )
    assert ordinary.risk is RiskMode.NORMAL
    assert ordinary.mode is TeachingMode.SKIP
    assert ordinary.target is None

    risky = resolve_teaching_decision(
        goal="Add login session authorization", done_condition="The member can sign in",
        boundaries=(), evidence=evidence, now=NOW,
    )
    assert risky.risk is RiskMode.SLOWDOWN
    assert risky.risk_reason_key == "authentication"
    assert risky.mode is TeachingMode.ASK
    assert risky.target == "data_ownership"
    assert risky.check_requirement == "required"


def test_recent_skill_evidence_cannot_supply_a_missing_current_done_condition():
    evidence = [
        observation("define_done", days_ago=10, change="a"),
        observation("define_done", days_ago=1, change="b"),
    ]
    decision = resolve_teaching_decision(
        goal="Add a score summary", done_condition=None, boundaries=(),
        evidence=evidence, now=NOW,
    )
    assert decision.learner_status is LearnerStatus.RECENTLY_INDEPENDENT
    assert decision.mode is TeachingMode.ASK
    assert decision.target == "define_done"


def test_risk_classifier_is_narrow_and_effort_is_deterministic():
    assert classify_risk("Change button spacing").mode is RiskMode.NORMAL
    assert classify_risk("Drop table after the migration").reason_key == "destructive_data"
    assert recommend_effort("Fix the button label", RiskMode.NORMAL) is EffortCategory.QUICK
    assert recommend_effort("Add a normal score summary", RiskMode.NORMAL) is EffortCategory.STANDARD
    assert recommend_effort("Change authorization rules", RiskMode.SLOWDOWN) is EffortCategory.DEEP


@pytest.mark.parametrize(
    "text",
    ["production quality styling", "role-playing character", "session notes"],
)
def test_risk_classifier_avoids_broad_standalone_word_false_positives(text):
    decision = classify_risk(text)
    assert decision.mode is RiskMode.NORMAL
    assert decision.reason_key is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("change login session tokens", "authentication"),
        ("modify user roles and permissions", "authorization"),
        ("push this migration to production", "deployment_impact"),
        ("delete stored user data", "destructive_data"),
        ("charge a customer card", "payment"),
        ("change authentication logic", "authentication"),
    ],
)
def test_risk_classifier_detects_narrow_consequential_actions(text, reason):
    assert classify_risk(text).reason_key == reason


def test_risk_fingerprint_tracks_prompt_relevant_state_only():
    safe = risk_input_fingerprint(
        "Add notes", "Click Save and see the note", ["Keep search unchanged"],
        "Add a note form",
    )
    risky = risk_input_fingerprint(
        "Add notes", "Click Save and see the note", ["Keep search unchanged"],
        "Add authentication logic to the note form",
    )
    removed = risk_input_fingerprint(
        "Add notes", "Click Save and see the note", ["Keep search unchanged"],
        "Add a note form",
    )
    assert safe != risky
    assert removed == safe


def test_evidence_qualification_is_semantic_and_open_ended_prose_is_not_graded():
    assert not qualifies_structured_response("define_done", "Looks good")
    assert qualifies_structured_response(
        "define_done", "Click Save and see the confirmation message"
    )
    assert qualifies_structured_response(
        "protect_working_behavior", "Keep the current scoring controls unchanged"
    )
    assert not qualifies_structured_response(
        "causal_explanation", "The button probably changes state"
    )
    assert not qualifies_check_plan("Looks good")
    assert qualifies_check_plan("Click Save and verify the message appears")


def test_help_level_is_scoped_to_the_active_interaction():
    change = SimpleNamespace(
        teaching_target="protect_working_behavior",
        teaching_mode=TeachingMode.ASK,
        support_level_disclosed=SupportLevel.CLUE,
        help_context_key="testing",
        risk=RiskMode.NORMAL,
        risk_reason_key=None,
    )
    verification = v2_teaching_service.intervention_view(
        change, SimpleNamespace(), context="verification",
        mode=TeachingMode.ASK, target="testing",
    )
    understanding = v2_teaching_service.intervention_view(
        change, SimpleNamespace(), context="understanding",
        mode=TeachingMode.ASK, target="causal_explanation",
    )
    assert verification.hint_level.value == "clue"
    assert understanding.hint_level.value == "none"
    assert understanding.hint_text is None


@pytest.mark.parametrize(
    ("support", "expected_elicitation", "expected_support"),
    [
        (SupportLevel.NONE, "asked", "none"),
        (SupportLevel.NUDGE, "after_hint", "nudge"),
        (SupportLevel.CLUE, "after_hint", "clue"),
        (SupportLevel.TEACH, "taught", "teach"),
    ],
)
def test_remind_evidence_uses_consumed_support_not_policy_mode(
    support, expected_elicitation, expected_support
):
    elicitation, classified_support = v2_teaching_service._evidence_qualification(
        TeachingMode.REMIND, support
    )
    assert elicitation == expected_elicitation
    assert classified_support == expected_support


def test_understanding_gate_uses_consequence_or_confusion_not_effort():
    ordinary = SimpleNamespace(
        risk=RiskMode.NORMAL, unresolved_uncertainty_summary=None,
        teaching_target="protect_working_behavior", effort_category=EffortCategory.DEEP,
    )
    risky = SimpleNamespace(
        risk=RiskMode.SLOWDOWN, unresolved_uncertainty_summary=None,
        teaching_target="protect_working_behavior", effort_category=EffortCategory.QUICK,
    )
    confused = SimpleNamespace(
        risk=RiskMode.NORMAL, unresolved_uncertainty_summary="Student was unsure.",
        teaching_target="protect_working_behavior", effort_category=EffortCategory.QUICK,
    )
    assert not v2_teaching_service.understanding_is_required(ordinary)
    assert v2_teaching_service.understanding_is_required(risky)
    assert v2_teaching_service.understanding_is_required(confused)


def test_beta_flow_teaches_then_offers_independence_fades_and_can_return():
    competency_a = "define_done"
    evidence = [observation(
        competency_a, days_ago=20, change="change-1",
        elicitation=Elicitation.TAUGHT, support=SupportLevel.TEACH,
    )]
    assert derive_learner_status(evidence, competency_a, now=NOW) is LearnerStatus.GUIDED
    assert mode_for_evidence(evidence, competency_a, now=NOW) is TeachingMode.ASK

    evidence.append(observation(competency_a, days_ago=10, change="change-2"))
    assert derive_learner_status(evidence, competency_a, now=NOW) is LearnerStatus.PRACTICED
    assert mode_for_evidence(evidence, competency_a, now=NOW) is TeachingMode.ASK

    evidence.append(observation(competency_a, days_ago=1, change="change-3"))
    assert derive_learner_status(
        evidence, competency_a, now=NOW
    ) is LearnerStatus.RECENTLY_INDEPENDENT
    assert mode_for_evidence(evidence, competency_a, now=NOW) is TeachingMode.SKIP
    assert mode_for_evidence(evidence, "testing", now=NOW) is TeachingMode.TEACH

    evidence.append(observation(
        competency_a, days_ago=0, change="change-4",
        elicitation=Elicitation.AFTER_HINT, support=SupportLevel.CLUE,
    ))
    assert derive_learner_status(evidence, competency_a, now=NOW) is LearnerStatus.GUIDED
    assert mode_for_evidence(evidence, competency_a, now=NOW) is TeachingMode.REMIND


def test_verification_fading_supplies_new_check_then_fades_and_returns():
    evidence: list[EvidenceObservation] = []
    new_mode = mode_for_evidence(evidence, "testing", now=NOW)
    assert new_mode is TeachingMode.TEACH
    assert v2_teaching_service.verification_plan_source(new_mode) == "codize"

    evidence.append(observation(
        "testing", days_ago=20, change="change-1",
        elicitation=Elicitation.TAUGHT, support=SupportLevel.TEACH,
    ))
    guided_mode = mode_for_evidence(evidence, "testing", now=NOW)
    assert derive_learner_status(evidence, "testing", now=NOW) is LearnerStatus.GUIDED
    assert guided_mode is TeachingMode.ASK
    assert v2_teaching_service.verification_plan_source(guided_mode) == "student"

    evidence.append(observation("testing", days_ago=10, change="change-2"))
    practiced_mode = mode_for_evidence(evidence, "testing", now=NOW)
    assert derive_learner_status(evidence, "testing", now=NOW) is LearnerStatus.PRACTICED
    assert practiced_mode is TeachingMode.ASK
    assert v2_teaching_service.verification_plan_source(practiced_mode) == "student"

    evidence.append(observation("testing", days_ago=1, change="change-3"))
    independent_mode = mode_for_evidence(evidence, "testing", now=NOW)
    assert derive_learner_status(
        evidence, "testing", now=NOW
    ) is LearnerStatus.RECENTLY_INDEPENDENT
    assert independent_mode is TeachingMode.SKIP
    assert v2_teaching_service.verification_plan_source(independent_mode) == "student"
    assert mode_for_evidence(evidence, "data_ownership", now=NOW) is TeachingMode.TEACH

    assert v2_teaching_service.verification_mode(
        independent_mode, RiskMode.SLOWDOWN
    ) is TeachingMode.TEACH

    evidence.append(observation(
        "testing", days_ago=0, change="change-4",
        elicitation=Elicitation.AFTER_HINT, support=SupportLevel.CLUE,
    ))
    return_mode = mode_for_evidence(evidence, "testing", now=NOW)
    assert derive_learner_status(evidence, "testing", now=NOW) is LearnerStatus.GUIDED
    assert return_mode is TeachingMode.REMIND


def test_hint_ladder_is_progressive_and_capped_without_penalty_state():
    assert next_support_level(SupportLevel.NONE) is SupportLevel.NUDGE
    assert next_support_level(SupportLevel.NUDGE) is SupportLevel.CLUE
    assert next_support_level(SupportLevel.CLUE) is SupportLevel.TEACH
    assert next_support_level(SupportLevel.TEACH) is SupportLevel.TEACH


def test_policy_versions_are_resolved_and_versioned():
    assert all(
        value and value != "unresolved-v0"
        for value in (TEACHING_POLICY_VERSION, RISK_POLICY_VERSION, EVIDENCE_POLICY_VERSION)
    )
