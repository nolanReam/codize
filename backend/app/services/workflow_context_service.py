"""One bounded, typed workflow normalizer for Defense and Report.

Consumers must use this service instead of parsing workflow_artifacts.  The
input project has already been loaded through an owner-filtered repository;
the output is deterministic, phase-scoped, provider-neutral plain text.
"""

import json
from dataclasses import dataclass, field

from app.schemas.workflow_context import (
    WORKFLOW_CONTEXT_SCHEMA_VERSION,
    CuratedWorkflowContext,
    WorkflowContextChangeItem,
    WorkflowContextChangeMap,
    WorkflowContextEvidence,
    WorkflowContextEvidenceEntry,
    WorkflowContextEvidenceRecord,
    WorkflowContextManualReview,
    WorkflowContextReview,
    WorkflowContextReviewItem,
    WorkflowContextVerification,
    WorkflowContextVerificationCheck,
)
from app.services import (
    evidence_service,
    review_service,
    verification_service,
    workflow_service,
)
from app.services.content_safety_service import (
    has_unsafe_control_chars,
    redact_secrets,
)

MAX_CHANGE_MAP_ITEMS = 30
MAX_REVIEW_ITEMS = 30
MAX_VERIFICATION_CHECKS = 30
MAX_EVIDENCE_TARGETS = 20
MAX_EVIDENCE_ENTRIES = 20
MAX_TEXT_CHARS = 1_000
MAX_ENTRY_CHARS = 2_000
MAX_TOTAL_TEXT_CHARS = 10_000
MAX_SERIALIZED_CONTEXT_CHARS = 24_000
MAX_PROMPT_CONTEXT_CHARS = 9_000
TRUNCATION_MARKER = " …[TRUNCATED]"

_MISSING = object()


@dataclass
class _Bounds:
    remaining: int = MAX_TOTAL_TEXT_CHARS
    truncated_sources: set[str] = field(default_factory=set)
    redacted: bool = False

    def text(
        self,
        value,
        source: str,
        *,
        limit: int = MAX_TEXT_CHARS,
        required: bool = False,
    ) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        if has_unsafe_control_chars(value):
            raise ValueError("unsafe workflow control character")
        cleaned, redacted = redact_secrets(value)
        self.redacted = self.redacted or redacted
        allowed = min(limit, self.remaining)
        if allowed <= len(TRUNCATION_MARKER):
            self.truncated_sources.add(source)
            return None
        if len(cleaned) > allowed:
            keep = allowed - len(TRUNCATION_MARKER)
            cleaned = cleaned[:keep] + TRUNCATION_MARKER
            self.truncated_sources.add(source)
        self.remaining -= len(cleaned)
        if required and not cleaned:
            return None
        return cleaned


def _phase_map(project: dict, phase_number: int) -> dict | None:
    artifacts = project.get("workflow_artifacts")
    phase_map = artifacts.get(str(phase_number)) if isinstance(artifacts, dict) else None
    return phase_map if isinstance(phase_map, dict) else None


def _raw_state(project: dict, phase_number: int, key: str):
    phase_map = _phase_map(project, phase_number)
    if phase_map is None or key not in phase_map:
        return _MISSING
    return phase_map[key]


def _source_state(states: list[str]) -> str:
    if all(state == "missing" for state in states):
        return "missing"
    if "malformed" in states or "incomplete" in states:
        return "incomplete"
    if "stale" in states:
        return "stale"
    if all(state in ("missing", "manual") for state in states):
        return "manual"
    return "current"


def _malformed_change_map() -> WorkflowContextChangeMap:
    return WorkflowContextChangeMap(state="malformed")


def _change_map(project: dict, phase_number: int, bounds: _Bounds) -> WorkflowContextChangeMap:
    raw = _raw_state(project, phase_number, workflow_service.CHANGE_MAP_KEY)
    if raw is _MISSING:
        return WorkflowContextChangeMap(state="missing")
    change_map = workflow_service.get_change_map(project, phase_number)
    if change_map is None:
        return _malformed_change_map()
    stale = workflow_service.change_map_is_stale(project, phase_number, change_map)
    state = "stale" if stale else ("current" if change_map.status == "confirmed" else "incomplete")
    if change_map.status != "confirmed":
        # A draft is still AI inference under active student review.  Its
        # content is not downstream-safe until the student explicitly
        # confirms the whole Change Map.
        return WorkflowContextChangeMap(state=state)
    items: list[WorkflowContextChangeItem] = []
    capped = change_map.items[:MAX_CHANGE_MAP_ITEMS]
    if len(change_map.items) > len(capped):
        bounds.truncated_sources.add("change_map")
    try:
        for item in capped:
            if item.student_decision == "edited" or item.origin == "student_added":
                raw_text = item.student_text
            else:
                raw_text = item.draft_text
            text = bounds.text(raw_text, "change_map", required=True)
            if text is None:
                bounds.truncated_sources.add("change_map")
                break
            if item.origin == "student_added":
                provenance = "Student-authored Change Map item"
            elif item.student_decision == "edited":
                provenance = "Student-edited AI-inferred Change Map item"
            elif item.student_decision == "confirmed":
                provenance = "Student-confirmed AI-inferred Change Map item"
            elif item.student_decision == "rejected":
                provenance = "AI-inferred Change Map item rejected by the student"
            else:
                provenance = "Unresolved AI-inferred Change Map item"
            items.append(
                WorkflowContextChangeItem(
                    category=item.category,
                    origin=item.origin,
                    student_decision=item.student_decision,
                    text=text,
                    provenance=provenance,
                    ai_uncertainty=item.ai_uncertainty,
                    uncertainty_reason=bounds.text(
                        item.uncertainty_reason, "change_map"
                    ),
                    student_note=bounds.text(item.student_note, "change_map"),
                )
            )
    except ValueError:
        return _malformed_change_map()
    return WorkflowContextChangeMap(
        state=state,
        items=items,
        truncated="change_map" in bounds.truncated_sources,
    )


def _review(project: dict, phase_number: int, bounds: _Bounds) -> WorkflowContextReview:
    raw = _raw_state(project, phase_number, "review_board")
    if raw is _MISSING:
        return WorkflowContextReview(state="missing")
    review = review_service.get_stored_review(project, phase_number)
    if review is None:
        return WorkflowContextReview(state="malformed")
    try:
        if not review_service.initialized_from_change_map(review):
            files = []
            for value in review.files_changed[:50]:
                text = bounds.text(value, "review", limit=300)
                if text is not None:
                    files.append(text)
            manual = WorkflowContextManualReview(
                files_changed=files,
                ai_generated=bounds.text(review.ai_generated, "review"),
                accepted=bounds.text(review.accepted, "review"),
                rejected=bounds.text(review.rejected, "review"),
                edited_manually=bounds.text(review.edited_manually, "review"),
                ai_assumptions=bounds.text(review.ai_assumptions, "review"),
                least_confident=bounds.text(review.least_confident, "review"),
                out_of_scope_changes=bounds.text(review.out_of_scope_changes, "review"),
            )
            return WorkflowContextReview(
                state="manual",
                manual=manual,
                truncated="review" in bounds.truncated_sources,
            )

        stale = review_service.review_is_stale(project, phase_number, review)
        incomplete = not review_service.review_complete(review) or not review.saved_at
        state = "stale" if stale else ("incomplete" if incomplete else "current")
        capped = review.review_targets[:MAX_REVIEW_ITEMS]
        if len(review.review_targets) > len(capped):
            bounds.truncated_sources.add("review")
        items: list[WorkflowContextReviewItem] = []
        for target in capped:
            text = bounds.text(target.change_text, "review", required=True)
            if text is None:
                bounds.truncated_sources.add("review")
                break
            items.append(
                WorkflowContextReviewItem(
                    category=target.change_map_category,
                    source_origin=target.change_map_origin,
                    source_student_decision=target.change_map_student_decision,
                    source_resolution=target.source_resolution,
                    reviewed_text=text,
                    review_decision=target.review_decision,
                    student_rationale=bounds.text(target.student_rationale, "review"),
                    student_revision=bounds.text(target.student_revision, "review"),
                )
            )
        return WorkflowContextReview(
            state=state,
            items=items,
            truncated="review" in bounds.truncated_sources,
        )
    except ValueError:
        return WorkflowContextReview(state="malformed")


def _verification(
    project: dict, phase_number: int, bounds: _Bounds
) -> WorkflowContextVerification:
    raw = _raw_state(project, phase_number, "verification")
    if raw is _MISSING:
        return WorkflowContextVerification(state="missing")
    verification = verification_service.get_stored_verification(project, phase_number)
    if verification is None:
        return WorkflowContextVerification(state="malformed")
    try:
        checks: list[WorkflowContextVerificationCheck] = []
        if not verification_service.initialized_from_review(verification):
            for check in verification.checks[:8]:
                checks.append(
                    WorkflowContextVerificationCheck(
                        check=check.check,
                        result=check.result,
                        result_notes=bounds.text(check.note, "verification"),
                        provenance="student_recorded",
                    )
                )
            return WorkflowContextVerification(
                state="manual",
                checks=checks,
                student_explanation=bounds.text(
                    verification.explanation, "verification"
                ),
                truncated="verification" in bounds.truncated_sources,
            )

        stale = verification_service.verification_is_stale(
            project, phase_number, verification
        )
        targets = verification.verification_targets[:MAX_VERIFICATION_CHECKS]
        if len(verification.verification_targets) > len(targets):
            bounds.truncated_sources.add("verification")
        for target in targets:
            wording = bounds.text(
                target.student_check or target.suggested_check,
                "verification",
                required=True,
            )
            if wording is None:
                bounds.truncated_sources.add("verification")
                break
            result = target.result or "unrecorded"
            checks.append(
                WorkflowContextVerificationCheck(
                    check=wording,
                    result=result,
                    result_notes=bounds.text(target.result_notes, "verification"),
                    category=target.category,
                    provenance=(
                        "student_unrecorded" if result == "unrecorded" else "student_recorded"
                    ),
                )
            )
        # Currency is derived from the complete stored source, not only the
        # bounded prefix exposed downstream. Otherwise an unrecorded target
        # beyond MAX_VERIFICATION_CHECKS could be silently presented as a
        # current/complete Verification record.
        incomplete = bool(
            verification_service.pending_targets(verification)
        ) or not verification.saved_at
        return WorkflowContextVerification(
            state="stale" if stale else ("incomplete" if incomplete else "current"),
            checks=checks,
            student_explanation=bounds.text(
                verification.explanation, "verification"
            ),
            truncated="verification" in bounds.truncated_sources,
        )
    except ValueError:
        return WorkflowContextVerification(state="malformed")


def _evidence(project: dict, phase_number: int, bounds: _Bounds) -> WorkflowContextEvidence:
    raw = _raw_state(project, phase_number, "evidence")
    if raw is _MISSING:
        return WorkflowContextEvidence(state="missing")
    evidence = evidence_service.get_stored_evidence(project, phase_number)
    if evidence is None:
        return WorkflowContextEvidence(state="malformed")
    try:
        if not evidence_service.initialized_from_verification(evidence):
            entries: list[WorkflowContextEvidenceEntry] = []
            for entry in evidence.entries[:MAX_EVIDENCE_ENTRIES]:
                content = bounds.text(
                    entry.content, "evidence", limit=MAX_ENTRY_CHARS, required=True
                )
                if content is None:
                    bounds.truncated_sources.add("evidence")
                    break
                entries.append(
                    WorkflowContextEvidenceEntry(kind=entry.kind, content=content)
                )
            return WorkflowContextEvidence(
                state="manual",
                manual_entries=entries,
                manual_summary=bounds.text(evidence.summary, "evidence"),
                truncated="evidence" in bounds.truncated_sources,
            )

        stale = evidence_service.evidence_is_stale(project, phase_number, evidence)
        targets = evidence.evidence_targets[:MAX_EVIDENCE_TARGETS]
        if len(evidence.evidence_targets) > len(targets):
            bounds.truncated_sources.add("evidence")
        entry_count = 0
        records: list[WorkflowContextEvidenceRecord] = []
        for target in targets:
            check_context = bounds.text(
                target.check_snapshot, "evidence", required=True
            )
            if check_context is None:
                bounds.truncated_sources.add("evidence")
                break
            entries: list[WorkflowContextEvidenceEntry] = []
            if not stale:
                for entry in target.entries:
                    if entry_count >= MAX_EVIDENCE_ENTRIES:
                        bounds.truncated_sources.add("evidence")
                        break
                    content = bounds.text(
                        entry.content,
                        "evidence",
                        limit=MAX_ENTRY_CHARS,
                        required=True,
                    )
                    if content is None:
                        bounds.truncated_sources.add("evidence")
                        break
                    entries.append(
                        WorkflowContextEvidenceEntry(kind=entry.kind, content=content)
                    )
                    entry_count += 1
            records.append(
                WorkflowContextEvidenceRecord(
                    category=target.category,
                    check_context=check_context,
                    verification_result=target.verification_result_snapshot,
                    verification_notes=bounds.text(
                        target.verification_result_notes_snapshot,
                        "evidence",
                    ),
                    evidence_status=target.evidence_status,
                    entries=entries,
                    student_explanation=(
                        None
                        if stale
                        else bounds.text(target.explanation, "evidence")
                    ),
                    unavailable_reason=(
                        None
                        if stale
                        else bounds.text(target.unavailable_reason, "evidence")
                    ),
                    stale_support_omitted=stale and target.evidence_status != "not_addressed",
                )
            )
        incomplete = not evidence_service.evidence_record_complete(evidence)
        return WorkflowContextEvidence(
            state="stale" if stale else ("incomplete" if incomplete else "current"),
            records=records,
            truncated="evidence" in bounds.truncated_sources,
        )
    except ValueError:
        return WorkflowContextEvidence(state="malformed")


def build_workflow_context(project: dict, phase_number: int) -> CuratedWorkflowContext:
    """Normalize one already-owned project's phase without I/O or provider use."""
    bounds = _Bounds()
    change_map = _change_map(project, phase_number, bounds)
    review = _review(project, phase_number, bounds)
    verification = _verification(project, phase_number, bounds)
    evidence = _evidence(project, phase_number, bounds)
    context = CuratedWorkflowContext(
        phase_number=phase_number,
        state=_source_state(
            [change_map.state, review.state, verification.state, evidence.state]
        ),
        change_map=change_map,
        review=review,
        verification=verification,
        evidence=evidence,
        content_truncated=bool(bounds.truncated_sources),
        content_redacted=bounds.redacted,
    )
    # A programming-error backstop over list/field budgets.  User data is
    # already bounded before this point; never put an oversized context into a
    # provider prompt or attempt snapshot.
    if len(json.dumps(context.model_dump(mode="json"), ensure_ascii=False)) > MAX_SERIALIZED_CONTEXT_CHARS:
        # Drop lowest-priority tail items deterministically until the belt fits.
        for source, collection in (
            (context.change_map, context.change_map.items),
            (context.review, context.review.items),
            (context.verification, context.verification.checks),
            (context.evidence, context.evidence.records),
        ):
            while collection and len(
                json.dumps(context.model_dump(mode="json"), ensure_ascii=False)
            ) > MAX_SERIALIZED_CONTEXT_CHARS:
                collection.pop()
                context.content_truncated = True
                source.truncated = True
        if len(json.dumps(context.model_dump(mode="json"), ensure_ascii=False)) > MAX_SERIALIZED_CONTEXT_CHARS:
            # Fixed schema overhead cannot reach this with the declared caps.
            raise RuntimeError("bounded workflow context exceeded its fixed belt")
    context.change_map.truncated |= "change_map" in bounds.truncated_sources
    context.review.truncated |= "review" in bounds.truncated_sources
    context.verification.truncated |= "verification" in bounds.truncated_sources
    context.evidence.truncated |= "evidence" in bounds.truncated_sources
    return context


def context_from_snapshot(session: dict) -> CuratedWorkflowContext | None:
    """Read a server-owned attempt snapshot; malformed legacy metadata is ignored."""
    turns = session.get("turns")
    if not isinstance(turns, list) or not turns or not isinstance(turns[0], dict):
        return None
    raw = turns[0].get("workflow_context_snapshot")
    if not isinstance(raw, dict):
        return None
    try:
        context = CuratedWorkflowContext.model_validate(raw)
    except Exception:
        return None
    session_phase = session.get("phase_id")
    if (
        context.schema_version != WORKFLOW_CONTEXT_SCHEMA_VERSION
        or type(session_phase) is not int
        or context.phase_number != session_phase
    ):
        return None
    return context


def snapshot_payload(context: CuratedWorkflowContext) -> dict:
    """The exact server-owned JSON stored with the attempt's first question."""
    return context.model_dump(mode="json")


def prompt_context(
    context: CuratedWorkflowContext,
    max_chars: int = MAX_PROMPT_CONTEXT_CHARS,
) -> CuratedWorkflowContext:
    """Return a whole, schema-valid prompt projection within ``max_chars``.

    The attempt snapshot and Report retain the fuller curated context. Defense
    question prompts need a smaller belt, but must never receive a string cut
    through the middle of an item where a claim could be separated from its
    provenance or stale/uncertain state. This projection therefore removes
    complete tail records deterministically and marks their source truncated.
    """
    projected = context.model_copy(deep=True)

    def serialized_len() -> int:
        return len(
            json.dumps(
                projected.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    collections = (
        (projected.change_map, projected.change_map.items),
        (projected.review, projected.review.items),
        (projected.verification, projected.verification.checks),
        (projected.evidence, projected.evidence.records),
        (projected.evidence, projected.evidence.manual_entries),
    )
    while serialized_len() > max_chars:
        candidates = [
            (len(json.dumps(items[-1].model_dump(mode="json"), ensure_ascii=False)), index)
            for index, (_, items) in enumerate(collections)
            if items
        ]
        if not candidates:
            break
        _, index = max(candidates)
        source, items = collections[index]
        items.pop()
        source.truncated = True
        projected.content_truncated = True

    # A context containing only manual optional prose can still exceed the
    # prompt belt after all list records are removed. Omit optional fields as
    # whole values, keeping source state/provenance intact and marking the
    # affected source truncated.
    optional_fields = (
        (projected.evidence, "manual_summary"),
        (projected.verification, "student_explanation"),
    )
    for source, field_name in optional_fields:
        if serialized_len() <= max_chars:
            break
        if getattr(source, field_name) is not None:
            setattr(source, field_name, None)
            source.truncated = True
            projected.content_truncated = True

    manual = projected.review.manual
    if manual is not None:
        for field_name in (
            "out_of_scope_changes",
            "least_confident",
            "ai_assumptions",
            "edited_manually",
            "rejected",
            "accepted",
            "ai_generated",
        ):
            if serialized_len() <= max_chars:
                break
            if getattr(manual, field_name) is not None:
                setattr(manual, field_name, None)
                projected.review.truncated = True
                projected.content_truncated = True
        while manual.files_changed and serialized_len() > max_chars:
            manual.files_changed.pop()
            projected.review.truncated = True
            projected.content_truncated = True

    if serialized_len() > max_chars:
        raise RuntimeError("workflow prompt context exceeded its fixed belt")
    return projected
