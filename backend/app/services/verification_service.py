"""Saved Review -> Verification suggestion foundation (Milestone 16B.1).

This service deterministically converts only saved linked Review decisions
marked ``needs_verification`` into proposed checks. It never calls an LLM,
executes project code, creates Evidence, or claims that a check was performed.

The semantic boundary is permanent:

* Review decision: "I need to test this."
* Verification suggestion: "Here is a grounded check you could perform."
* Verification result: a later student record of what they actually did.

All source identity, snapshots, suggestions, bindings, timestamps, ids, and
staleness are server-owned. Only check wording, result, and result notes are
student-owned on linked targets.
"""

import hashlib
import json
from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.workflow import (
    LinkedVerificationTarget,
    StoredReviewBoardArtifact,
    StoredVerificationArtifact,
    VerificationArtifact,
    VerificationHandoffTarget,
    VerificationReviewBinding,
    VerificationSaveRequest,
)
from app.services import phase_service, review_service
from app.services.project_repository import ProjectRepository

_MISSING = object()
_LINKED_SERVER_FIELDS = {
    "initialized_at",
    "source_review_binding",
    "verification_targets",
}


class VerificationError(Exception):
    """Base for controlled Verification errors; messages are client-safe."""


class VerificationReviewMissingError(VerificationError):
    """There is no valid saved Review to initialize from."""


class VerificationReviewNotLinkedError(VerificationError):
    """The saved Review is manual/legacy and has no server-owned targets."""


class VerificationReviewIncompleteError(VerificationError):
    """The linked Review still has pending decisions or was not saved."""


class VerificationReviewStaleError(VerificationError):
    """The linked Review no longer matches the current Change Map."""


class VerificationAlreadyExistsError(VerificationError):
    """Verification data exists and replacement was not requested."""


class VerificationSourceConflictError(VerificationError):
    """Defensive refusal for inconsistent/colliding server source identity."""


class InvalidVerificationUpdateError(VerificationError):
    """A student update is invalid or attempts to alter provenance."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _raw_verification(project: dict, phase_number: int):
    artifacts = project.get("workflow_artifacts")
    phase_map = artifacts.get(str(phase_number)) if isinstance(artifacts, dict) else None
    if not isinstance(phase_map, dict) or "verification" not in phase_map:
        return _MISSING
    return phase_map["verification"]


def get_stored_verification(
    project: dict, phase_number: int
) -> StoredVerificationArtifact | None:
    """Typed read from an already-owned project; corrupt data stays hidden."""
    raw = _raw_verification(project, phase_number)
    if not isinstance(raw, dict):
        return None
    try:
        return StoredVerificationArtifact.model_validate(raw)
    except ValidationError:
        return None


def initialized_from_review(verification: StoredVerificationArtifact) -> bool:
    return bool(verification.source_review_binding and verification.initialized_at)


def _review_target_fingerprint(review: StoredReviewBoardArtifact) -> str:
    """Stable Review version identity without source text as the primary key."""
    identity = [
        {
            "review_target_id": target.review_target_id,
            "change_map_item_id": target.change_map_item_id,
            "category": target.change_map_category,
            "decision": target.review_decision,
        }
        for target in review.review_targets
    ]
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _binding_for_review(
    review: StoredReviewBoardArtifact,
) -> VerificationReviewBinding:
    if not (
        review.source_change_map_generated_at
        and review.source_change_map_confirmed_at
        and review.saved_at
    ):
        raise VerificationSourceConflictError(
            "Verification suggestions could not be initialized from this Review."
        )
    return VerificationReviewBinding(
        source_change_map_generated_at=review.source_change_map_generated_at,
        source_change_map_confirmed_at=review.source_change_map_confirmed_at,
        review_saved_at=review.saved_at,
        review_target_fingerprint=_review_target_fingerprint(review),
    )


def verification_is_stale(
    project: dict,
    phase_number: int,
    verification: StoredVerificationArtifact,
) -> bool:
    """Compute linked Verification staleness without rewriting old work."""
    if not initialized_from_review(verification):
        return False

    review = review_service.get_stored_review(project, phase_number)
    if review is None or not review_service.initialized_from_change_map(review):
        return True
    if review_service.review_is_stale(project, phase_number, review):
        return True
    if not review_service.review_complete(review) or not review.saved_at:
        return True

    try:
        current_binding = _binding_for_review(review)
    except VerificationSourceConflictError:
        return True
    if current_binding != verification.source_review_binding:
        return True

    current_ids = [
        target.review_target_id
        for target in review_service.needs_verification_targets(review)
    ]
    stored_ids = [target.review_target_id for target in verification.verification_targets]
    return current_ids != stored_ids


def verification_view(project: dict, phase_number: int) -> dict | None:
    """Additive read contract for ``GET /workflow/{phase}``."""
    raw = _raw_verification(project, phase_number)
    if raw is _MISSING:
        return None
    verification = get_stored_verification(project, phase_number)
    if verification is None:
        return None
    if not initialized_from_review(verification):
        # Preserve the exact legacy/manual response shape.
        legacy = VerificationArtifact.model_validate(
            {
                name: getattr(verification, name)
                for name in VerificationArtifact.model_fields
            }
        ).model_dump(mode="json")
        legacy["saved_at"] = verification.saved_at
        return legacy
    view = verification.model_dump(mode="json")
    view["initialized_from_review"] = True
    view["stale"] = verification_is_stale(project, phase_number, verification)
    return view


def _verification_target_id(review_target_id: str) -> str:
    digest = hashlib.sha256(
        f"codize-verification-target-v1\n{review_target_id}".encode("utf-8")
    ).hexdigest()[:12]
    return f"vt-{digest}"


def _quoted_source(text: str) -> str:
    return f'“{text}”'


def _behavior_suggestion(text: str) -> str:
    return (
        f"Check this reviewed behavior: {_quoted_source(text)} Perform the relevant "
        "action, note what you expected, and record what actually happened."
    )


def _decision_suggestion(text: str) -> str:
    return (
        "Check the behavior affected by this reviewed implementation decision: "
        f"{_quoted_source(text)} Exercise the relevant user-facing or system "
        "behavior and record what happened."
    )


def _scope_suggestion(text: str) -> str:
    return (
        f"Check this reviewed possible out-of-scope change: {_quoted_source(text)} "
        "Confirm whether the described behavior exists, then decide whether it "
        "belongs in the intended project scope. Record what you found."
    )


def _security_suggestion(text: str) -> str:
    return (
        f"Carefully check this reviewed security-sensitive area: {_quoted_source(text)} "
        "Try one intended or authorized case and, where appropriate, one restricted "
        "case. Record what happened without assuming there is a vulnerability."
    )


def _risk_suggestion(text: str) -> str:
    return (
        f"Investigate this reviewed unresolved risk: {_quoted_source(text)} "
        "Reproduce or inspect the uncertain condition and record whether it occurs."
    )


def _unverified_suggestion(text: str) -> str:
    return (
        f"Directly perform this reviewed behavior: {_quoted_source(text)} "
        "Record what you expected and what actually happened."
    )


SUGGESTION_TEMPLATES = {
    "behavior_change": _behavior_suggestion,
    "implementation_decision": _decision_suggestion,
    "out_of_scope_change": _scope_suggestion,
    "security_sensitive_area": _security_suggestion,
    "unresolved_risk": _risk_suggestion,
    "unverified_behavior": _unverified_suggestion,
}


def derive_verification_targets(
    review: StoredReviewBoardArtifact,
) -> list[LinkedVerificationTarget]:
    """Derive suggestions only through the typed M16A handoff helper."""
    source_targets = review_service.needs_verification_targets(review)
    if any(target.change_map_category not in SUGGESTION_TEMPLATES for target in source_targets):
        raise VerificationSourceConflictError(
            "Verification suggestions could not be initialized from this Review."
        )
    targets = [
        LinkedVerificationTarget(
            verification_target_id=_verification_target_id(target.review_target_id),
            review_target_id=target.review_target_id,
            change_map_item_id=target.change_map_item_id,
            category=target.change_map_category,
            source_text=target.reviewed_text,
            source_rationale=target.student_rationale,
            suggested_check=SUGGESTION_TEMPLATES[target.change_map_category](
                target.reviewed_text
            ),
            student_check=None,
            result=None,
            result_notes=None,
        )
        for target in source_targets
    ]
    ids = [target.verification_target_id for target in targets]
    if len(ids) != len(set(ids)):
        raise VerificationSourceConflictError(
            "Verification suggestions could not be initialized from this Review."
        )
    return targets


def pending_targets(
    verification: StoredVerificationArtifact,
) -> list[LinkedVerificationTarget]:
    """Targets with no student-recorded result."""
    return [target for target in verification.verification_targets if target.result is None]


def completed_targets(
    verification: StoredVerificationArtifact,
) -> list[LinkedVerificationTarget]:
    """Targets the student says they performed (pass or fail only)."""
    return [
        target
        for target in verification.verification_targets
        if target.result in ("pass", "fail")
    ]


def failed_targets(
    verification: StoredVerificationArtifact,
) -> list[LinkedVerificationTarget]:
    return [target for target in verification.verification_targets if target.result == "fail"]


def unresolved_targets(
    verification: StoredVerificationArtifact,
) -> list[LinkedVerificationTarget]:
    """Anything not recorded as pass remains unresolved; skipped/N/A are not pass."""
    return [target for target in verification.verification_targets if target.result != "pass"]


def evidence_handoff_targets(
    verification: StoredVerificationArtifact,
) -> list[VerificationHandoffTarget]:
    """Future M16B.3 typed read seam; this function creates no Evidence."""
    return [
        VerificationHandoffTarget(
            verification_target_id=target.verification_target_id,
            review_target_id=target.review_target_id,
            change_map_item_id=target.change_map_item_id,
            category=target.category,
            check_wording=target.student_check or target.suggested_check,
            result=target.result,
            result_notes=target.result_notes,
        )
        for target in verification.verification_targets
    ]


def _safe_validation_message(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first["loc"]) or "body"
    return f"Invalid Verification update ({loc}): {first['msg']}"


async def create_from_review(
    repo: ProjectRepository,
    user_id: str,
    phase_number: int,
    replace_existing: bool = False,
) -> dict:
    """Explicitly initialize linked suggestions from the current saved Review."""
    from app.services import workflow_service

    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)

    review = review_service.get_stored_review(project, phase_number)
    if review is None:
        raise VerificationReviewMissingError(
            "Complete Review before creating Verification suggestions."
        )
    if not review_service.initialized_from_change_map(review):
        raise VerificationReviewNotLinkedError(
            "Create Review from the current Change Map before creating Verification suggestions."
        )
    if review_service.review_is_stale(project, phase_number, review):
        raise VerificationReviewStaleError(
            "Rebuild Review from the current Change Map before creating Verification suggestions."
        )
    if not review.saved_at or not review_service.review_complete(review):
        raise VerificationReviewIncompleteError(
            "Finish and save Review before creating Verification suggestions."
        )

    if _raw_verification(project, phase_number) is not _MISSING and not replace_existing:
        raise VerificationAlreadyExistsError(
            "Verification work already exists for this phase."
        )

    now = _now_iso()
    verification = StoredVerificationArtifact(
        checks=[],
        explanation=None,
        saved_at=now,
        initialized_at=now,
        source_review_binding=_binding_for_review(review),
        verification_targets=derive_verification_targets(review),
    )
    project = await workflow_service.store_verification(
        repo,
        user_id,
        project,
        phase_number,
        verification.model_dump(mode="json"),
    )
    return {
        "phase": phase_number,
        "section": "verification",
        "artifact": verification_view(project, phase_number),
    }


async def save_verification(
    repo: ProjectRepository,
    user_id: str,
    project: dict,
    phase_number: int,
    payload: dict,
) -> dict:
    """Legacy Verification PUT with protected linked-target updates."""
    from app.services import workflow_service

    try:
        request = VerificationSaveRequest.model_validate(payload)
    except ValidationError as exc:
        raise InvalidVerificationUpdateError(_safe_validation_message(exc))

    update_ids = [update.verification_target_id for update in request.target_updates]
    if len(update_ids) != len(set(update_ids)):
        raise InvalidVerificationUpdateError(
            "Invalid Verification update: the same target appears more than once."
        )

    raw = _raw_verification(project, phase_number)
    stored = get_stored_verification(project, phase_number)
    raw_linked = isinstance(raw, dict) and bool(_LINKED_SERVER_FIELDS & set(raw))
    if raw_linked and stored is None:
        raise InvalidVerificationUpdateError(
            "This linked Verification cannot be updated until it is reinitialized."
        )

    manual = VerificationArtifact.model_validate(
        request.model_dump(mode="json", exclude={"target_updates"})
    ).model_dump(mode="json")

    if stored is not None and initialized_from_review(stored):
        targets = {
            target.verification_target_id: target
            for target in stored.verification_targets
        }
        if any(target_id not in targets for target_id in update_ids):
            raise InvalidVerificationUpdateError(
                "Invalid Verification update: a target id does not match this Verification."
            )
        updates = {
            update.verification_target_id: update for update in request.target_updates
        }
        target_data: list[dict] = []
        for target in stored.verification_targets:
            data = target.model_dump(mode="json")
            update = updates.get(target.verification_target_id)
            if update is not None:
                for field in ("student_check", "result", "result_notes"):
                    if field in update.model_fields_set:
                        data[field] = getattr(update, field)
            target_data.append(data)

        data = stored.model_dump(mode="json")
        data.update(manual)
        data["verification_targets"] = target_data
        data["saved_at"] = _now_iso()
        try:
            validated = StoredVerificationArtifact.model_validate(data)
        except ValidationError as exc:
            raise InvalidVerificationUpdateError(_safe_validation_message(exc))
        stored_data = validated.model_dump(mode="json")
    else:
        if request.target_updates:
            raise InvalidVerificationUpdateError(
                "Verification target updates require Verification initialized from Review."
            )
        # Byte-compatible legacy/manual storage: no linked defaults are added.
        stored_data = manual
        stored_data["saved_at"] = _now_iso()

    project = await workflow_service.store_verification(
        repo, user_id, project, phase_number, stored_data
    )
    return {
        "phase": phase_number,
        "section": "verification",
        "artifact": verification_view(project, phase_number),
    }
