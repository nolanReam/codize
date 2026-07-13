"""Confirmed Change Map -> Review integration (Milestone 16A.1).

This service deterministically initializes the existing Review Board section
from a student-reviewed, confirmed Change Map. It does not call an LLM, read
raw Implementation Import material, execute code, create Verification or
Evidence records, or alter any gate/report behavior.

The semantic boundary is permanent:

* Change Map: "Is this an accurate description of what appears to have changed?"
* Review: "What do I think about that implementation, and what happens next?"

Source identity/snapshots are server-owned. Only Review decisions, rationale,
revision text, and the legacy manual Review fields are student-owned.
"""

import hashlib
from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.workflow import (
    NeedsVerificationReviewTarget,
    ReviewBoardArtifact,
    ReviewBoardSaveRequest,
    ReviewTarget,
    StoredReviewBoardArtifact,
)
from app.services import phase_service
from app.services.project_repository import ProjectRepository

# Exact inclusion/priority rule for M16A.1. `changed_file` is context rather
# than a decision by itself; `question_to_understand` remains a Change Map
# prompt. Confirmed AND unresolved items in these six implementation-relevant
# categories become targets, preserving their source resolution honestly.
REVIEW_TARGET_CATEGORIES = (
    "behavior_change",
    "implementation_decision",
    "out_of_scope_change",
    "security_sensitive_area",
    "unresolved_risk",
    "unverified_behavior",
)
_CATEGORY_PRIORITY = {
    category: position for position, category in enumerate(REVIEW_TARGET_CATEGORIES)
}

_MISSING = object()
_LINKED_SERVER_FIELDS = {
    "source_change_map_confirmed_at",
    "source_change_map_generated_at",
    "review_targets",
}


class ReviewError(Exception):
    """Base for controlled Review errors; every message is safe for clients."""


class ReviewChangeMapMissingError(ReviewError):
    """There is no valid Change Map to initialize from."""


class ReviewChangeMapDraftError(ReviewError):
    """The Change Map has not been confirmed."""


class ReviewChangeMapStaleError(ReviewError):
    """The Change Map no longer matches the saved implementation import."""


class ReviewChangeMapPendingError(ReviewError):
    """Defensive refusal when a reviewed map still contains a pending item."""


class ReviewAlreadyExistsError(ReviewError):
    """Review data exists and explicit replacement was not requested."""


class InvalidReviewUpdateError(ReviewError):
    """A student Review update is invalid or attempts to alter provenance."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _raw_review_board(project: dict, phase_number: int):
    artifacts = project.get("workflow_artifacts")
    phase_map = artifacts.get(str(phase_number)) if isinstance(artifacts, dict) else None
    if not isinstance(phase_map, dict) or "review_board" not in phase_map:
        return _MISSING
    return phase_map["review_board"]


def get_stored_review(
    project: dict, phase_number: int
) -> StoredReviewBoardArtifact | None:
    """Typed read from an already-owned project. Legacy Review artifacts are
    accepted through additive defaults; corrupt data never surfaces raw."""
    raw = _raw_review_board(project, phase_number)
    if not isinstance(raw, dict):
        return None
    try:
        return StoredReviewBoardArtifact.model_validate(raw)
    except ValidationError:
        return None


def initialized_from_change_map(review: StoredReviewBoardArtifact) -> bool:
    return bool(
        review.source_change_map_confirmed_at
        and review.source_change_map_generated_at
    )


def review_is_stale(
    project: dict, phase_number: int, review: StoredReviewBoardArtifact
) -> bool:
    """Server-derived linked-Review staleness; manual/legacy Review artifacts
    are not linked and therefore are never labeled stale."""
    if not initialized_from_change_map(review):
        return False

    # Local imports avoid a module cycle: change_map_service already imports
    # workflow_service, which delegates Review reads/writes to this service.
    from app.services import workflow_service

    change_map = workflow_service.get_change_map(project, phase_number)
    if change_map is None or change_map.status != "confirmed":
        return True
    if workflow_service.change_map_is_stale(project, phase_number, change_map):
        return True
    return bool(
        review.source_change_map_confirmed_at != change_map.confirmed_at
        or review.source_change_map_generated_at != change_map.generated_at
    )


def review_board_view(project: dict, phase_number: int) -> dict | None:
    """Additive Review read contract used by GET /workflow/{phase}.

    The source snapshots are intentionally small and already part of the
    Review record. Raw import material, Change Map references/excerpts,
    provider output, and computed stale state are never persisted here.
    """
    raw = _raw_review_board(project, phase_number)
    if raw is _MISSING:
        return None
    review = get_stored_review(project, phase_number)
    if review is None:
        return None
    if not initialized_from_change_map(review):
        # Preserve the exact M13B manual Review read shape. The future frontend
        # treats absent linked fields as initialized=false/stale=false.
        legacy = ReviewBoardArtifact.model_validate({
            name: getattr(review, name) for name in ReviewBoardArtifact.model_fields
        }).model_dump(mode="json")
        legacy["saved_at"] = review.saved_at
        return legacy
    view = review.model_dump(mode="json")
    view["initialized_from_change_map"] = True
    view["stale"] = review_is_stale(project, phase_number, review)
    return view


def _review_target_id(change_map_item_id: str) -> str:
    digest = hashlib.sha256(
        f"codize-review-target-v1\n{change_map_item_id}".encode("utf-8")
    ).hexdigest()[:12]
    return f"rv-{digest}"


def derive_review_targets(change_map) -> list[ReviewTarget]:
    """Deterministically derive bounded targets through the typed M15C seams.

    Category priority is REVIEW_TARGET_CATEGORIES; original Change Map order
    breaks ties. Rejected and pending items never enter either M15C helper.
    Uncertain/needs-inspection items enter through unresolved_items and retain
    `source_resolution=unresolved` plus their exact student-decision snapshot.
    """
    from app.services import change_map_service

    positions = {item.item_id: index for index, item in enumerate(change_map.items)}
    candidates = [
        (item, "confirmed")
        for item in change_map_service.confirmed_items(change_map)
    ]
    candidates.extend(
        (item, "unresolved")
        for item in change_map_service.unresolved_items(change_map)
    )
    candidates = [
        candidate
        for candidate in candidates
        if candidate[0].category in _CATEGORY_PRIORITY
    ]
    candidates.sort(
        key=lambda candidate: (
            _CATEGORY_PRIORITY[candidate[0].category],
            positions[candidate[0].item_id],
        )
    )

    return [
        ReviewTarget(
            review_target_id=_review_target_id(item.item_id),
            change_map_item_id=item.item_id,
            change_map_category=item.category,
            change_map_origin=item.origin,
            change_map_student_decision=item.student_decision,
            change_text=item.text,
            source_resolution=resolution,
            review_decision="pending",
            student_rationale=None,
            student_revision=None,
        )
        for item, resolution in candidates
    ]


def pending_review_targets(review: StoredReviewBoardArtifact) -> list[ReviewTarget]:
    """Review-specific pending targets; unrelated to build/workflow/gate progress."""
    return [target for target in review.review_targets if target.review_decision == "pending"]


def reviewed_target_count(review: StoredReviewBoardArtifact) -> int:
    return sum(
        target.review_decision != "pending" for target in review.review_targets
    )


def review_complete(review: StoredReviewBoardArtifact) -> bool:
    """A linked Review is complete only when it has targets and none is pending."""
    return bool(review.review_targets) and not pending_review_targets(review)


def needs_verification_targets(
    review: StoredReviewBoardArtifact,
) -> list[NeedsVerificationReviewTarget]:
    """Typed future M16B seam. This function creates no Verification checks."""
    return [
        NeedsVerificationReviewTarget(
            review_target_id=target.review_target_id,
            change_map_item_id=target.change_map_item_id,
            reviewed_text=target.change_text,
            student_rationale=target.student_rationale,
            change_map_category=target.change_map_category,
        )
        for target in review.review_targets
        if target.review_decision == "needs_verification"
    ]


def _safe_validation_message(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first["loc"]) or "body"
    return f"Invalid Review update ({loc}): {first['msg']}"


async def create_from_change_map(
    repo: ProjectRepository,
    user_id: str,
    phase_number: int,
    replace_existing: bool = False,
) -> dict:
    """Create one linked Review draft from the owned phase's current map.

    No source fields are accepted from the client; all targets, snapshots,
    ids, provenance, and version bindings are server-derived.
    """
    from app.services import workflow_service

    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)

    change_map = workflow_service.get_change_map(project, phase_number)
    if change_map is None:
        raise ReviewChangeMapMissingError(
            "Create and review a Change Map before starting Review from it."
        )
    if change_map.status != "confirmed":
        raise ReviewChangeMapDraftError(
            "Confirm the reviewed Change Map before using it to start Review."
        )
    if workflow_service.change_map_is_stale(project, phase_number, change_map):
        raise ReviewChangeMapStaleError(
            "Regenerate and review the current Change Map before starting Review."
        )
    if any(
        item.student_decision == "pending_review" for item in change_map.items
    ):
        raise ReviewChangeMapPendingError(
            "Confirm the reviewed Change Map before using it to start Review."
        )

    if _raw_review_board(project, phase_number) is not _MISSING and not replace_existing:
        raise ReviewAlreadyExistsError("Review work already exists for this phase.")

    review = StoredReviewBoardArtifact(
        source_change_map_confirmed_at=change_map.confirmed_at,
        source_change_map_generated_at=change_map.generated_at,
        review_targets=derive_review_targets(change_map),
        saved_at=_now_iso(),
    )
    project = await workflow_service.store_review_board(
        repo, user_id, project, phase_number, review.model_dump(mode="json")
    )
    return {
        "phase": phase_number,
        "section": "review_board",
        "artifact": review_board_view(project, phase_number),
    }


async def save_review_board(
    repo: ProjectRepository,
    user_id: str,
    project: dict,
    phase_number: int,
    payload: dict,
) -> dict:
    """Existing Review PUT with protected linked-target updates.

    Legacy/manual fields keep their full-replace behavior. When a linked
    Review exists, `target_updates` patch only the three student-owned target
    fields; every server-owned snapshot/provenance field is copied unchanged.
    """
    from app.services import workflow_service

    try:
        request = ReviewBoardSaveRequest.model_validate(payload)
    except ValidationError as exc:
        raise InvalidReviewUpdateError(_safe_validation_message(exc))

    update_ids = [update.review_target_id for update in request.target_updates]
    if len(update_ids) != len(set(update_ids)):
        raise InvalidReviewUpdateError(
            "Invalid Review update: the same target appears more than once."
        )

    raw = _raw_review_board(project, phase_number)
    stored = get_stored_review(project, phase_number)
    raw_linked = isinstance(raw, dict) and bool(_LINKED_SERVER_FIELDS & set(raw))
    if raw_linked and stored is None:
        raise InvalidReviewUpdateError(
            "This linked Review cannot be updated until it is reinitialized."
        )

    manual = ReviewBoardArtifact.model_validate(
        request.model_dump(mode="json", exclude={"target_updates"})
    ).model_dump(mode="json")

    if stored is not None and initialized_from_change_map(stored):
        targets = {target.review_target_id: target for target in stored.review_targets}
        if any(target_id not in targets for target_id in update_ids):
            raise InvalidReviewUpdateError(
                "Invalid Review update: a target id does not match this Review."
            )
        updates = {update.review_target_id: update for update in request.target_updates}
        target_data: list[dict] = []
        for target in stored.review_targets:
            data = target.model_dump(mode="json")
            update = updates.get(target.review_target_id)
            if update is not None:
                data["review_decision"] = update.review_decision
                data["student_rationale"] = update.student_rationale
                data["student_revision"] = update.student_revision
            target_data.append(data)

        data = stored.model_dump(mode="json")
        data.update(manual)  # legacy fields retain full-section replacement
        data["review_targets"] = target_data
        data["saved_at"] = _now_iso()
        validated = StoredReviewBoardArtifact.model_validate(data)
        stored_data = validated.model_dump(mode="json")
    else:
        if request.target_updates:
            raise InvalidReviewUpdateError(
                "Review target updates require a Review initialized from a Change Map."
            )
        # Byte-compatible manual Review storage: no linked defaults are added.
        stored_data = manual
        stored_data["saved_at"] = _now_iso()

    project = await workflow_service.store_review_board(
        repo, user_id, project, phase_number, stored_data
    )
    return {
        "phase": phase_number,
        "section": "review_board",
        "artifact": review_board_view(project, phase_number),
    }
