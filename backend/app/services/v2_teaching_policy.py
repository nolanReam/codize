"""Versioned, deterministic Phase 5 teaching policy.

The canonical architecture intentionally left exact fading and risk thresholds open.
Phase 5 adopts this small conservative beta policy so support can adapt without
claiming permanent mastery.  The policy is application logic: model output never
selects any value returned here.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Iterable

from app.domain.v2 import EffortCategory


TEACHING_POLICY_VERSION = "phase5-beta-teaching-v1"
RISK_POLICY_VERSION = "phase5-beta-risk-v1"
EVIDENCE_POLICY_VERSION = "phase5-beta-evidence-v1"


class TeachingMode(StrEnum):
    SKIP = "skip"
    ASK = "ask"
    REMIND = "remind"
    TEACH = "teach"


class RiskMode(StrEnum):
    NORMAL = "normal"
    SLOWDOWN = "slowdown"


class LearnerStatus(StrEnum):
    NEW = "new"
    GUIDED = "guided"
    PRACTICED = "practiced"
    RECENTLY_INDEPENDENT = "recently_independent"


class SupportLevel(StrEnum):
    NONE = "none"
    NUDGE = "nudge"
    CLUE = "clue"
    TEACH = "teach"


class Elicitation(StrEnum):
    SPONTANEOUS = "spontaneous"
    ASKED = "asked"
    AFTER_HINT = "after_hint"
    TAUGHT = "taught"


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    competency_key: str
    elicitation: Elicitation
    support_level: SupportLevel
    observed_at: datetime
    source_current_change_id: str | None
    status: str = "active"

    @property
    def independent(self) -> bool:
        return (
            self.support_level is SupportLevel.NONE
            and self.elicitation in {Elicitation.SPONTANEOUS, Elicitation.ASKED}
        )


@dataclass(frozen=True, slots=True)
class RiskDecision:
    mode: RiskMode
    reason_key: str | None


@dataclass(frozen=True, slots=True)
class TeachingDecision:
    mode: TeachingMode
    target: str | None
    reason_key: str
    learner_status: LearnerStatus | None
    risk: RiskMode
    risk_reason_key: str | None
    check_requirement: str


_RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("authentication", re.compile(
        r"\b(?:change|add|build|implement|modify|replace|secure|rotate|store|validate|"
        r"invalidate|refresh|issue|revoke)\b[^.\n]{0,64}\b(?:authentication|auth|"
        r"log[ -]?in|sign[ -]?in|session (?:token|cookie|id)|password reset)\b|"
        r"\b(?:authentication|auth|log[ -]?in|sign[ -]?in|session (?:token|cookie|id))\b"
        r"[^.\n]{0,64}\b(?:flow|logic|handler|token|cookie|security|validation)\b", re.I)),
    ("authorization", re.compile(
        r"\b(?:change|add|build|implement|modify|enforce|grant|revoke)\b[^.\n]{0,64}"
        r"\b(?:authori[sz]ation|user roles?|permissions?|access control|rls|row level security)\b|"
        r"\b(?:authori[sz]ation|permissions?|access control|rls|row level security)\b"
        r"[^.\n]{0,64}\b(?:policy|rule|logic|check|access)\b", re.I)),
    ("destructive_data", re.compile(
        r"\b(?:delete|remove|erase|wipe|purge)\b[^.\n]{0,48}\b(?:stored|saved|user|"
        r"customer|production|database|table|records?|rows?|data|files?)\b|"
        r"\b(?:drop (?:a |the )?(?:table|column|database)|truncate (?:a |the )?(?:table|database))\b",
        re.I)),
    ("sensitive_data", re.compile(
        r"\b(?:store|log|send|expose|read|write|handle|encrypt|decrypt|rotate|validate)\b"
        r"[^.\n]{0,64}\b(?:secrets?|api keys?|passwords?|private data|sensitive data|"
        r"personal data|pii|credit card numbers?)\b", re.I)),
    ("database_migration", re.compile(
        r"\b(?:create|run|apply|push|deploy|change|edit|modify)\b[^.\n]{0,48}"
        r"\b(?:database|schema|data) migrations?\b|\bmigrate (?:the )?(?:database|schema|data)\b",
        re.I)),
    ("deployment_impact", re.compile(
        r"\b(?:push|deploy|release|roll out|apply)\b[^.\n]{0,48}\b(?:to )?production\b|"
        r"\b(?:change|edit|modify|rotate|remove|add)\b[^.\n]{0,48}"
        r"\b(?:production (?:configuration|environment|deployment)|environment variables?)\b",
        re.I)),
    ("payment", re.compile(
        r"\b(?:charge|refund|bill)\b[^.\n]{0,32}\b(?:a |the )?(?:customer|user|card|payment)\b|"
        r"\b(?:add|build|implement|change|modify|process)\b[^.\n]{0,64}"
        r"\b(?:payments?|billing|checkout|stripe|credit card transactions?)\b", re.I)),
)

_QUICK_PATTERN = re.compile(
    r"\b(copy|label|typo|wording|text|color|colour|spacing|icon|rename)\b", re.I
)
_DEEP_PATTERN = re.compile(
    r"\b(architecture|major refactor|multi[- ]?service|race condition|security|"
    r"unfamiliar system|complex debugging)\b",
    re.I,
)


def classify_risk(change_text: str) -> RiskDecision:
    """Return the first narrow canonical risk category matched by the change."""

    for reason, pattern in _RISK_PATTERNS:
        if pattern.search(change_text):
            return RiskDecision(RiskMode.SLOWDOWN, reason)
    return RiskDecision(RiskMode.NORMAL, None)


def risk_relevant_text(
    goal: str,
    done_condition: str | None,
    boundaries: Iterable[str],
    prompt_draft: str | None,
) -> str:
    """Join only durable fields that can change what the student hands off."""

    return "\n".join(
        value for value in (goal, done_condition, *boundaries, prompt_draft) if value
    )


def _fingerprint_part(value: str | None) -> str:
    if value is None:
        return "N"
    return f"V{len(value.encode('utf-8'))}:{value}"


def risk_input_fingerprint(
    goal: str,
    done_condition: str | None,
    boundaries: Iterable[str],
    prompt_draft: str | None,
) -> str:
    """Stable, non-secret freshness identity mirrored by the PostgreSQL guard."""

    boundary_values = tuple(boundaries)
    canonical = "risk-v1|" + "|".join(
        (
            _fingerprint_part(goal),
            _fingerprint_part(done_condition),
            f"A{len(boundary_values)}:" + "".join(
                _fingerprint_part(value) for value in boundary_values
            ),
            _fingerprint_part(prompt_draft),
        )
    )
    return hashlib.md5(canonical.encode("utf-8"), usedforsecurity=False).hexdigest()


def derive_learner_status(
    evidence: Iterable[EvidenceObservation],
    competency_key: str,
    *,
    now: datetime | None = None,
) -> LearnerStatus:
    """Derive a conservative descriptor for one competency.

    Beta thresholds:
    - no active evidence -> New;
    - one or more assisted observations -> Guided;
    - two qualifying observations, or any unsupported observation -> Practiced;
    - Recently independent requires two unsupported observations from distinct
      Current Changes within 60 days, including one within 30 days.

    A later assisted/teaching observation returns the descriptor to Guided. This
    makes support recover after struggle and prevents a permanent mastery label.
    """

    current = now or datetime.now(UTC)
    relevant = sorted(
        (
            item
            for item in evidence
            if item.status == "active" and item.competency_key == competency_key
        ),
        key=lambda item: item.observed_at,
    )
    if not relevant:
        return LearnerStatus.NEW

    latest = relevant[-1]
    if not latest.independent:
        return LearnerStatus.GUIDED

    recent_independent = [
        item
        for item in relevant
        if item.independent and item.observed_at >= current - timedelta(days=60)
    ]
    contexts = {item.source_current_change_id for item in recent_independent if item.source_current_change_id}
    has_fresh = any(
        item.observed_at >= current - timedelta(days=30) for item in recent_independent
    )
    if len(recent_independent) >= 2 and len(contexts) >= 2 and has_fresh:
        return LearnerStatus.RECENTLY_INDEPENDENT
    if len(relevant) >= 2 or any(item.independent for item in relevant):
        return LearnerStatus.PRACTICED
    return LearnerStatus.GUIDED


def mode_for_status(status: LearnerStatus) -> TeachingMode:
    return {
        LearnerStatus.NEW: TeachingMode.TEACH,
        # The first supported encounter must lead to an ordinary independent
        # opportunity on the next Current Change, not a permanent reminder.
        LearnerStatus.GUIDED: TeachingMode.ASK,
        LearnerStatus.PRACTICED: TeachingMode.ASK,
        LearnerStatus.RECENTLY_INDEPENDENT: TeachingMode.SKIP,
    }[status]


def mode_for_evidence(
    evidence: Iterable[EvidenceObservation], competency_key: str, *, now: datetime | None = None
) -> TeachingMode:
    relevant = [
        item for item in evidence
        if item.status == "active" and item.competency_key == competency_key
    ]
    status = derive_learner_status(relevant, competency_key, now=now)
    # After a previously independent behavior needs help, a brief reminder is
    # useful. A learner whose only encounter was supported gets ASK instead.
    if status is LearnerStatus.GUIDED and any(item.independent for item in relevant):
        return TeachingMode.REMIND
    return mode_for_status(status)


def choose_teaching_target(
    *, goal: str, done_condition: str | None, boundaries: tuple[str, ...]
) -> tuple[str, str]:
    """Choose one highest-value competency for this pre-handoff moment."""

    risk = classify_risk(goal)
    if not done_condition:
        return "define_done", "observable_done_missing"
    if risk.reason_key in {"authentication", "authorization", "sensitive_data", "payment"}:
        return "data_ownership", f"risk_{risk.reason_key}"
    if boundaries:
        return "effort_selection", "done_and_boundary_already_present"
    return "protect_working_behavior", "working_boundary_not_supplied"


def resolve_teaching_decision(
    *,
    goal: str,
    done_condition: str | None,
    boundaries: tuple[str, ...],
    evidence: Iterable[EvidenceObservation],
    prompt_draft: str | None = None,
    now: datetime | None = None,
) -> TeachingDecision:
    target, reason = choose_teaching_target(
        goal=goal, done_condition=done_condition, boundaries=boundaries
    )
    observations = tuple(evidence)
    status = derive_learner_status(observations, target, now=now)
    mode = mode_for_evidence(observations, target, now=now)
    risk = classify_risk(risk_relevant_text(goal, done_condition, boundaries, prompt_draft))
    # Prior skill evidence cannot supply the Current Change's missing scope.
    # A recently independent learner answers briefly instead of receiving a
    # lesson, but the observable outcome still has to exist before prompting.
    if target == "define_done" and not done_condition and mode is TeachingMode.SKIP:
        mode = TeachingMode.ASK
        reason = "current_change_done_still_required"
    # Familiarity cannot remove the minimum student judgment on consequential work.
    if risk.mode is RiskMode.SLOWDOWN and mode is TeachingMode.SKIP:
        mode = TeachingMode.ASK
        reason = f"slowdown_reintroduces_{target}"
    return TeachingDecision(
        mode=mode,
        target=target if mode is not TeachingMode.SKIP else None,
        reason_key=reason,
        learner_status=status,
        risk=risk.mode,
        risk_reason_key=risk.reason_key,
        check_requirement="required",
    )


_OBSERVABLE_DONE = re.compile(
    r"\b(?:see|show|display|appear|receive|save|load|view|hear|visible|update|updates|"
    r"change|changes|message|result)\b", re.I
)
_PROTECT_BOUNDARY = re.compile(
    r"\b(?:leave|keep|preserve|remain|unchanged|not change|do not change|must still|"
    r"without changing)\b", re.I
)
_ALLOW_ACCESS = re.compile(r"\b(?:allow|may|can|access|only the intended|owner)\b", re.I)
_DENY_ACCESS = re.compile(r"\b(?:prevent|deny|cannot|can't|must not|no other|only)\b", re.I)
_CHECK_ACTION = re.compile(
    r"\b(?:add|click|type|enter|submit|open|select|save|load|refresh|run|try|visit|request)\b",
    re.I,
)
_CHECK_OBSERVATION = re.compile(
    r"\b(?:see|show|display|appear|receive|observe|confirm|verify|expect|result|message|"
    r"status|changes?|remains?)\b", re.I
)


def qualifies_structured_response(target: str, response: str) -> bool:
    """Qualify only behavior whose meaning is objectively constrained by the prompt."""

    text = response.strip()
    if len(text.split()) < 4:
        return False
    if target == "define_done":
        return bool(_OBSERVABLE_DONE.search(text))
    if target == "protect_working_behavior":
        return bool(_PROTECT_BOUNDARY.search(text))
    if target == "data_ownership":
        return bool(_ALLOW_ACCESS.search(text) and _DENY_ACCESS.search(text))
    # Causal correctness cannot be established from free text without a grader.
    return False


def qualifies_check_plan(check_plan: str) -> bool:
    text = check_plan.strip()
    return bool(
        len(text.split()) >= 5
        and _CHECK_ACTION.search(text)
        and _CHECK_OBSERVATION.search(text)
    )


def recommend_effort(goal: str, risk: RiskMode) -> EffortCategory:
    if risk is RiskMode.SLOWDOWN or _DEEP_PATTERN.search(goal):
        return EffortCategory.DEEP
    if _QUICK_PATTERN.search(goal) and len(goal.split()) <= 18:
        return EffortCategory.QUICK
    return EffortCategory.STANDARD


def next_support_level(current: SupportLevel) -> SupportLevel:
    return {
        SupportLevel.NONE: SupportLevel.NUDGE,
        SupportLevel.NUDGE: SupportLevel.CLUE,
        SupportLevel.CLUE: SupportLevel.TEACH,
        SupportLevel.TEACH: SupportLevel.TEACH,
    }[current]


def evidence_qualification(support: SupportLevel) -> tuple[Elicitation, bool]:
    """Return canonical elicitation and whether the behavior was unsupported."""

    if support is SupportLevel.NONE:
        return Elicitation.ASKED, True
    if support in {SupportLevel.NUDGE, SupportLevel.CLUE}:
        return Elicitation.AFTER_HINT, False
    return Elicitation.TAUGHT, False
