"""Verification results -> Evidence handoff foundation (Milestone 16B.3A).

The service preserves the permanent trust boundary: a saved pass/fail result
is eligible context for an explicit student handoff, but it is never Evidence.
Only the student may later add Evidence or record that it is unavailable.

Everything is deterministic. There is no provider, URL fetch, code execution,
automatic initialization, or Defense/Report integration here.
"""

import hashlib
import json
from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.workflow import (
    EvidenceArtifact,
    EvidenceFromVerificationRequest,
    EvidenceSaveRequest,
    EvidenceVerificationBinding,
    LinkedEvidenceTarget,
    StoredEvidenceArtifact,
    StoredVerificationArtifact,
    VerificationHandoffTarget,
)
from app.services import phase_service, verification_service
from app.services.project_repository import ProjectRepository

_MISSING = object()
_LINKED_SERVER_FIELDS = {
    "initialized_at",
    "source_verification_binding",
    "evidence_targets",
}


class EvidenceError(Exception):
    """Base for controlled, student-safe Evidence lifecycle errors."""


class EvidenceVerificationMissingError(EvidenceError):
    """No valid saved Verification is available for a linked handoff."""


class EvidenceVerificationNotLinkedError(EvidenceError):
    """The saved Verification is manual/legacy, not linked Review work."""


class EvidenceVerificationStaleError(EvidenceError):
    """The linked Verification no longer matches its current Review source."""


class EvidenceAlreadyExistsError(EvidenceError):
    """Evidence exists and replacement was not explicitly requested."""


class EvidenceStaleError(EvidenceError):
    """Linked Evidence is readable but cannot be edited until rebuilt."""


class InvalidEvidenceSelectionError(EvidenceError):
    """The explicit target selection is unknown or not performed."""


class InvalidEvidenceUpdateError(EvidenceError):
    """A student update is invalid or attempts to alter provenance."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _raw_evidence(project: dict, phase_number: int):
    artifacts = project.get("workflow_artifacts")
    phase_map = artifacts.get(str(phase_number)) if isinstance(artifacts, dict) else None
    if not isinstance(phase_map, dict) or "evidence" not in phase_map:
        return _MISSING
    return phase_map["evidence"]


def get_stored_evidence(
    project: dict, phase_number: int
) -> StoredEvidenceArtifact | None:
    """Typed read from an already-owned project; corrupt data stays hidden."""
    raw = _raw_evidence(project, phase_number)
    if not isinstance(raw, dict):
        return None
    try:
        return StoredEvidenceArtifact.model_validate(raw)
    except ValidationError:
        return None


def initialized_from_verification(evidence: StoredEvidenceArtifact) -> bool:
    return bool(evidence.source_verification_binding and evidence.initialized_at)


def _review_binding_fingerprint(verification: StoredVerificationArtifact) -> str:
    if verification.source_review_binding is None:
        raise EvidenceVerificationNotLinkedError(
            "Create linked Verification from Review before handing results to Evidence."
        )
    encoded = json.dumps(
        verification.source_review_binding.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _selected_target_fingerprint(
    targets: list[VerificationHandoffTarget],
) -> str:
    """Bind only selected result context; unrelated targets do not stale it."""
    identity = [
        {
            "verification_target_id": target.verification_target_id,
            "review_target_id": target.review_target_id,
            "change_map_item_id": target.change_map_item_id,
            "category": target.category,
            "check_wording": target.check_wording,
            "result": target.result,
            "result_notes": target.result_notes,
        }
        for target in targets
    ]
    encoded = json.dumps(
        identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _binding_for_verification(
    verification: StoredVerificationArtifact,
    selected: list[VerificationHandoffTarget],
) -> EvidenceVerificationBinding:
    if not verification.initialized_at or not verification.source_review_binding:
        raise EvidenceVerificationNotLinkedError(
            "Create linked Verification from Review before handing results to Evidence."
        )
    return EvidenceVerificationBinding(
        verification_initialized_at=verification.initialized_at,
        verification_review_binding_fingerprint=_review_binding_fingerprint(
            verification
        ),
        selected_target_fingerprint=_selected_target_fingerprint(selected),
    )


def _evidence_target_id(verification_target_id: str) -> str:
    digest = hashlib.sha256(
        f"codize-evidence-target-v1\n{verification_target_id}".encode("utf-8")
    ).hexdigest()[:12]
    return f"ev-{digest}"


def _linked_targets(
    selected: list[VerificationHandoffTarget],
) -> list[LinkedEvidenceTarget]:
    return [
        LinkedEvidenceTarget(
            evidence_target_id=_evidence_target_id(target.verification_target_id),
            source_verification_target_id=target.verification_target_id,
            source_review_target_id=target.review_target_id,
            source_change_map_item_id=target.change_map_item_id,
            category=target.category,
            check_snapshot=target.check_wording,
            verification_result_snapshot=target.result,
            verification_result_notes_snapshot=target.result_notes,
            evidence_status="not_addressed",
            entries=[],
            explanation=None,
            unavailable_reason=None,
        )
        for target in selected
        if target.result in ("pass", "fail")
    ]


def evidence_is_stale(
    project: dict,
    phase_number: int,
    evidence: StoredEvidenceArtifact,
) -> bool:
    """Derive selected Verification binding staleness without rewriting work."""
    if not initialized_from_verification(evidence):
        return False

    verification = verification_service.get_stored_verification(
        project, phase_number
    )
    if (
        verification is None
        or not verification_service.initialized_from_review(verification)
        or not verification.saved_at
        or verification_service.verification_is_stale(
            project, phase_number, verification
        )
    ):
        return True

    binding = evidence.source_verification_binding
    if binding is None or verification.initialized_at != binding.verification_initialized_at:
        return True
    try:
        if (
            _review_binding_fingerprint(verification)
            != binding.verification_review_binding_fingerprint
        ):
            return True
    except EvidenceVerificationNotLinkedError:
        return True

    current = {
        target.verification_target_id: target
        for target in verification_service.evidence_handoff_targets(verification)
    }
    try:
        selected = [
            current[target.source_verification_target_id]
            for target in evidence.evidence_targets
        ]
    except KeyError:
        return True
    return _selected_target_fingerprint(selected) != binding.selected_target_fingerprint


def evidence_record_complete(evidence: StoredEvidenceArtifact) -> bool:
    """Completion means every selected record was addressed, not correctness."""
    return bool(evidence.evidence_targets) and all(
        target.evidence_status != "not_addressed"
        for target in evidence.evidence_targets
    )


def evidence_view(project: dict, phase_number: int) -> dict | None:
    """Additive linked read view while preserving exact legacy/manual shape."""
    raw = _raw_evidence(project, phase_number)
    if raw is _MISSING:
        return None
    evidence = get_stored_evidence(project, phase_number)
    if evidence is None:
        return None
    if not initialized_from_verification(evidence):
        legacy = EvidenceArtifact.model_validate(
            {
                name: getattr(evidence, name)
                for name in EvidenceArtifact.model_fields
            }
        ).model_dump(mode="json")
        legacy["saved_at"] = evidence.saved_at
        return legacy
    # Curated client view: the server retains Review/Change Map linkage and
    # binding fingerprints internally, but the Evidence UI needs only its own
    # immutable target id, source Verification id/context, and student fields.
    return {
        "entries": [entry.model_dump(mode="json") for entry in evidence.entries],
        "summary": evidence.summary,
        "saved_at": evidence.saved_at,
        "initialized_from_verification": True,
        "stale": evidence_is_stale(project, phase_number, evidence),
        "evidence_record_complete": evidence_record_complete(evidence),
        "evidence_targets": [
            {
                "evidence_target_id": target.evidence_target_id,
                "source_verification_target_id": target.source_verification_target_id,
                "category": target.category,
                "check_snapshot": target.check_snapshot,
                "verification_result_snapshot": target.verification_result_snapshot,
                "verification_result_notes_snapshot": (
                    target.verification_result_notes_snapshot
                ),
                "evidence_status": target.evidence_status,
                "entries": [
                    entry.model_dump(mode="json") for entry in target.entries
                ],
                "explanation": target.explanation,
                "unavailable_reason": target.unavailable_reason,
            }
            for target in evidence.evidence_targets
        ],
    }


def _preview_target(target: VerificationHandoffTarget, *, stale: bool) -> dict:
    performed = target.result in ("pass", "fail")
    eligible = performed and not stale
    if eligible:
        reason = None
    elif stale:
        reason = "verification_stale"
    else:
        reason = "not_performed"
    return {
        "verification_target_id": target.verification_target_id,
        "category": target.category,
        "check": target.check_wording,
        "result": target.result or "unrecorded",
        "result_notes": target.result_notes,
        "performed": performed,
        "eligibility": "eligible" if eligible else "ineligible",
        "ineligibility_reason": reason,
    }


async def handoff_preview(
    repo: ProjectRepository, user_id: str, phase_number: int
) -> dict:
    """Pure read of student-safe Verification -> Evidence handoff context."""
    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)

    verification = verification_service.get_stored_verification(
        project, phase_number
    )
    if verification is None:
        return {
            "mode": "unavailable",
            "verification_state": "verification_required",
            "eligible_count": 0,
            "targets": [],
            "guidance": "Save linked Verification results before selecting Evidence targets.",
        }
    if not verification_service.initialized_from_review(verification):
        return {
            "mode": "manual_verification",
            "verification_state": "manual_verification",
            "eligible_count": 0,
            "targets": [],
            "guidance": "Manual Verification remains separate from linked Evidence handoff.",
        }
    if not verification.saved_at:
        return {
            "mode": "unavailable",
            "verification_state": "verification_required",
            "eligible_count": 0,
            "targets": [],
            "guidance": "Save linked Verification results before selecting Evidence targets.",
        }

    stale = verification_service.verification_is_stale(
        project, phase_number, verification
    )
    targets = [
        _preview_target(target, stale=stale)
        for target in verification_service.evidence_handoff_targets(verification)
    ]
    return {
        "mode": "linked_verification",
        "verification_state": "stale" if stale else "current",
        "eligible_count": sum(
            target["eligibility"] == "eligible" for target in targets
        ),
        "targets": targets,
        "guidance": (
            "Rebuild Verification before creating new linked Evidence."
            if stale
            else "Select performed results to create empty Evidence records."
        ),
    }


def _safe_validation_message(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first["loc"]) or "body"
    return f"Invalid Evidence update ({loc}): {first['msg']}"


async def create_from_verification(
    repo: ProjectRepository,
    user_id: str,
    phase_number: int,
    request: EvidenceFromVerificationRequest,
) -> dict:
    """Explicitly initialize empty linked Evidence records from selections."""
    from app.services import workflow_service

    project = await phase_service.load_active_project(repo, user_id)
    phase_service.require_phase(project, phase_number)
    verification = verification_service.get_stored_verification(
        project, phase_number
    )
    if verification is None:
        raise EvidenceVerificationMissingError(
            "Save linked Verification results before creating Evidence records."
        )
    if not verification_service.initialized_from_review(verification):
        raise EvidenceVerificationNotLinkedError(
            "Create linked Verification from Review before creating Evidence records."
        )
    if not verification.saved_at:
        raise EvidenceVerificationMissingError(
            "Save linked Verification results before creating Evidence records."
        )
    if verification_service.verification_is_stale(project, phase_number, verification):
        raise EvidenceVerificationStaleError(
            "Rebuild Verification before creating Evidence records."
        )

    handoff = verification_service.evidence_handoff_targets(verification)
    by_id = {target.verification_target_id: target for target in handoff}
    selected_ids = set(request.selected_verification_target_ids)
    if any(target_id not in by_id for target_id in selected_ids):
        raise InvalidEvidenceSelectionError(
            "Invalid Evidence selection: a target does not match this Verification."
        )
    if any(by_id[target_id].result not in ("pass", "fail") for target_id in selected_ids):
        raise InvalidEvidenceSelectionError(
            "Invalid Evidence selection: only performed pass or fail results are eligible."
        )
    selected = [
        target for target in handoff if target.verification_target_id in selected_ids
    ]

    if _raw_evidence(project, phase_number) is not _MISSING and not request.replace_existing:
        raise EvidenceAlreadyExistsError(
            "Evidence work already exists for this phase."
        )

    now = _now_iso()
    evidence = StoredEvidenceArtifact(
        entries=[],
        summary=None,
        saved_at=now,
        initialized_at=now,
        source_verification_binding=_binding_for_verification(
            verification, selected
        ),
        evidence_targets=_linked_targets(selected),
    )
    project = await workflow_service.store_evidence(
        repo,
        user_id,
        project,
        phase_number,
        evidence.model_dump(mode="json"),
    )
    return {
        "phase": phase_number,
        "section": "evidence",
        "artifact": evidence_view(project, phase_number),
    }


async def save_evidence(
    repo: ProjectRepository,
    user_id: str,
    project: dict,
    phase_number: int,
    payload: dict,
) -> dict:
    """Legacy Evidence PUT with protected linked-target updates."""
    from app.services import workflow_service

    try:
        request = EvidenceSaveRequest.model_validate(payload)
    except ValidationError as exc:
        raise InvalidEvidenceUpdateError(_safe_validation_message(exc))

    update_ids = [update.evidence_target_id for update in request.target_updates]
    if len(update_ids) != len(set(update_ids)):
        raise InvalidEvidenceUpdateError(
            "Invalid Evidence update: the same target appears more than once."
        )

    raw = _raw_evidence(project, phase_number)
    stored = get_stored_evidence(project, phase_number)
    raw_linked = isinstance(raw, dict) and bool(_LINKED_SERVER_FIELDS & set(raw))
    if raw_linked and stored is None:
        raise InvalidEvidenceUpdateError(
            "This linked Evidence cannot be updated until it is reinitialized."
        )

    manual = EvidenceArtifact.model_validate(
        request.model_dump(mode="json", exclude={"target_updates"})
    ).model_dump(mode="json")

    if stored is not None and initialized_from_verification(stored):
        if evidence_is_stale(project, phase_number, stored):
            raise EvidenceStaleError(
                "Rebuild linked Evidence from current Verification before editing it."
            )
        legacy_fields = set(EvidenceArtifact.model_fields) & request.model_fields_set
        if legacy_fields:
            raise InvalidEvidenceUpdateError(
                "Invalid Evidence update: linked Evidence accepts target updates only."
            )
        if not request.target_updates:
            raise InvalidEvidenceUpdateError(
                "Invalid Evidence update: linked Evidence needs at least one target update."
            )
        targets = {
            target.evidence_target_id: target for target in stored.evidence_targets
        }
        if any(target_id not in targets for target_id in update_ids):
            raise InvalidEvidenceUpdateError(
                "Invalid Evidence update: a target id does not match this Evidence."
            )
        updates = {
            update.evidence_target_id: update for update in request.target_updates
        }
        target_data: list[dict] = []
        for target in stored.evidence_targets:
            data = target.model_dump(mode="json")
            update = updates.get(target.evidence_target_id)
            if update is not None:
                for field in (
                    "evidence_status",
                    "entries",
                    "explanation",
                    "unavailable_reason",
                ):
                    if field in update.model_fields_set:
                        data[field] = getattr(update, field)
            target_data.append(data)

        data = stored.model_dump(mode="json")
        data["evidence_targets"] = target_data
        data["saved_at"] = _now_iso()
        try:
            validated = StoredEvidenceArtifact.model_validate(data)
        except ValidationError as exc:
            raise InvalidEvidenceUpdateError(_safe_validation_message(exc))
        stored_data = validated.model_dump(mode="json")
    else:
        if request.target_updates:
            raise InvalidEvidenceUpdateError(
                "Evidence target updates require Evidence initialized from Verification."
            )
        stored_data = manual
        stored_data["saved_at"] = _now_iso()

    project = await workflow_service.store_evidence(
        repo, user_id, project, phase_number, stored_data
    )
    return {
        "phase": phase_number,
        "section": "evidence",
        "artifact": evidence_view(project, phase_number),
    }
