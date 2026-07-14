"""Workflow artifact routes (M13B) — thin, auth-required; logic in the service.

The user id comes only from the verified JWT and the repository scopes every
read/write to it, so a user can only ever see or update their own artifacts.
Controlled errors map to the standard shape: workspace not ready → 409,
unknown phase or section → 404, invalid or oversized payload → 422.

M15C.1 adds the Change Map lifecycle under the same prefix:
POST /workflow/{phase}/change-map/generate (the only LLM route here — one
extraction at temperature 0 with bounded retry; failure → 502, nothing
stored), PUT /workflow/{phase}/change-map (student decisions only — no LLM),
POST /workflow/{phase}/change-map/confirm (pure state transition — no LLM).
The change-map PUT is registered BEFORE the generic section PUT so it matches
first; "change_map" is additionally not a section name, so the generic
full-replace path can never write server-owned provenance.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.schemas.change_map import ChangeMapGenerateRequest
from app.schemas.workflow import (
    EvidenceFromVerificationRequest,
    ReviewFromChangeMapRequest,
    VerificationFromReviewRequest,
)
from app.services import (
    change_map_service,
    evidence_service,
    phase_service,
    review_service,
    verification_service,
    workflow_service,
)
from app.services.llm_service import LLMService, get_llm_service
from app.services.project_repository import ProjectRepository, get_project_repository

router = APIRouter(prefix="/workflow")


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, phase_service.PhaseNotFoundError) or isinstance(
        exc, workflow_service.SectionNotFoundError
    ):
        status = 404
    elif isinstance(exc, workflow_service.InvalidArtifactError):
        status = 422
    elif isinstance(exc, review_service.InvalidReviewUpdateError):
        status = 422
    else:  # workspace not ready
        status = 409
    return HTTPException(status_code=status, detail=str(exc))


def _change_map_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, phase_service.PhaseNotFoundError) or isinstance(
        exc, change_map_service.ChangeMapNotFoundError
    ):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, change_map_service.InvalidChangeMapUpdateError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, change_map_service.ChangeMapGenerationError):
        return HTTPException(status_code=502, detail=str(exc))
    # workspace not ready / import required / already exists / stale /
    # pending items / already confirmed
    return HTTPException(status_code=409, detail=str(exc))


def _review_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, phase_service.PhaseNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, review_service.InvalidReviewUpdateError):
        return HTTPException(status_code=422, detail=str(exc))
    # Workspace not ready / no current confirmed map / stale map / existing
    # Review are workflow-state conflicts.
    return HTTPException(status_code=409, detail=str(exc))


def _verification_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, phase_service.PhaseNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, verification_service.InvalidVerificationUpdateError):
        return HTTPException(status_code=422, detail=str(exc))
    # Workspace not ready / missing, manual, incomplete, or stale Review /
    # existing Verification / inconsistent source identity are state conflicts.
    return HTTPException(status_code=409, detail=str(exc))


def _evidence_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, phase_service.PhaseNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(
        exc,
        (
            evidence_service.InvalidEvidenceSelectionError,
            evidence_service.InvalidEvidenceUpdateError,
        ),
    ):
        return HTTPException(status_code=422, detail=str(exc))
    # Missing/manual/stale Verification, existing Evidence, and stale linked
    # Evidence are lifecycle conflicts rather than malformed requests.
    return HTTPException(status_code=409, detail=str(exc))


@router.get("/{phase_number}")
async def get_phase_artifacts(
    phase_number: int,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await workflow_service.get_phase_artifacts(repo, user.user_id, phase_number)
    except (phase_service.PhaseWorkspaceError, workflow_service.WorkflowError) as exc:
        raise _http_error(exc)


@router.post("/{phase_number}/change-map/generate")
async def generate_change_map(
    phase_number: int,
    body: ChangeMapGenerateRequest | None = None,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
    llm: LLMService = Depends(get_llm_service),
) -> dict:
    try:
        return await change_map_service.generate_change_map(
            repo, llm, user.user_id, phase_number,
            replace_existing=bool(body and body.replace_existing),
        )
    except (phase_service.PhaseWorkspaceError, change_map_service.ChangeMapError) as exc:
        raise _change_map_http_error(exc)


@router.put("/{phase_number}/change-map")
async def update_change_map(
    phase_number: int,
    body: dict,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await change_map_service.update_change_map(
            repo, user.user_id, phase_number, body
        )
    except (phase_service.PhaseWorkspaceError, change_map_service.ChangeMapError) as exc:
        raise _change_map_http_error(exc)


@router.post("/{phase_number}/change-map/confirm")
async def confirm_change_map(
    phase_number: int,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await change_map_service.confirm_change_map(
            repo, user.user_id, phase_number
        )
    except (phase_service.PhaseWorkspaceError, change_map_service.ChangeMapError) as exc:
        raise _change_map_http_error(exc)


@router.post("/{phase_number}/review/from-change-map")
async def create_review_from_change_map(
    phase_number: int,
    body: ReviewFromChangeMapRequest | None = None,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Initialize Review deterministically from server-owned Change Map data.

    The request can express replacement intent only; it cannot carry targets,
    source text, provenance, ids, timestamps, or stale state.
    """
    try:
        return await review_service.create_from_change_map(
            repo,
            user.user_id,
            phase_number,
            replace_existing=bool(body and body.replace_existing),
        )
    except (phase_service.PhaseWorkspaceError, review_service.ReviewError) as exc:
        raise _review_http_error(exc)


@router.post("/{phase_number}/verification/from-review")
async def create_verification_from_review(
    phase_number: int,
    body: VerificationFromReviewRequest | None = None,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Initialize proposed checks from the current saved linked Review.

    The request carries replacement intent only. Targets, source snapshots,
    suggestions, ids, bindings, timestamps, results, and stale state are all
    server-derived or left unresolved.
    """
    try:
        return await verification_service.create_from_review(
            repo,
            user.user_id,
            phase_number,
            replace_existing=bool(body and body.replace_existing),
        )
    except (
        phase_service.PhaseWorkspaceError,
        verification_service.VerificationError,
    ) as exc:
        raise _verification_http_error(exc)


@router.get("/{phase_number}/evidence/from-verification")
async def preview_evidence_from_verification(
    phase_number: int,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Read-only, student-safe handoff context; creates no Evidence."""
    try:
        return await evidence_service.handoff_preview(
            repo, user.user_id, phase_number
        )
    except (phase_service.PhaseWorkspaceError, evidence_service.EvidenceError) as exc:
        raise _evidence_http_error(exc)


@router.post("/{phase_number}/evidence/from-verification")
async def create_evidence_from_verification(
    phase_number: int,
    body: EvidenceFromVerificationRequest,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    """Explicitly initialize empty Evidence records for selected results."""
    try:
        return await evidence_service.create_from_verification(
            repo, user.user_id, phase_number, body
        )
    except (phase_service.PhaseWorkspaceError, evidence_service.EvidenceError) as exc:
        raise _evidence_http_error(exc)


@router.put("/{phase_number}/{section}")
async def put_section(
    phase_number: int,
    section: str,
    body: dict,
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await workflow_service.save_section(
            repo, user.user_id, phase_number, section, body
        )
    except (
        phase_service.PhaseWorkspaceError,
        workflow_service.WorkflowError,
        review_service.ReviewError,
        verification_service.VerificationError,
        evidence_service.EvidenceError,
    ) as exc:
        raise _http_error(exc)
