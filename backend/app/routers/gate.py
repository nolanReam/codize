"""Interrogation Gate routes — thin, auth-required; all logic in gate_service.

The user id comes only from the verified JWT (require_user); the repositories
scope every read/write to it, so another user's gate session id is a plain
404. Controlled errors use the standard error shape: not ready / in progress /
already passed / out of order / cooldown → 409 (cooldown adds a Retry-After
header), unknown session → 404, invalid anchor → 422, LLM failure or
malformed evaluator output → 502 with nothing stored.

Responses never contain the quality score or any unlock-threshold data.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.schemas.gate import AnchorRequest, AnswerRequest
from app.services import gate_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.project_repository import (
    GateSessionRepository,
    ProjectRepository,
    get_gate_session_repository,
    get_project_repository,
)

router = APIRouter(prefix="/gate")


def _http_error(exc: gate_service.GateError) -> HTTPException:
    if isinstance(exc, gate_service.GateSessionNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, gate_service.AnchorInvalidError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, gate_service.GateGenerationError):
        return HTTPException(status_code=502, detail=str(exc))
    if isinstance(exc, gate_service.GateCooldownError):
        return HTTPException(
            status_code=409, detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )
    # not ready / already passed / in progress / out of order
    return HTTPException(status_code=409, detail=str(exc))


@router.post("/start")
async def start_gate(
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
) -> dict:
    try:
        return await gate_service.start_gate(project_repo, gate_repo, user.user_id)
    except gate_service.GateError as exc:
        raise _http_error(exc)


@router.get("/current")
async def get_current_gate(
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
) -> dict:
    try:
        return await gate_service.get_current_gate(project_repo, gate_repo, user.user_id)
    except gate_service.GateError as exc:
        raise _http_error(exc)


@router.post("/{gate_session_id}/turn1")
async def submit_anchor(
    gate_session_id: str,
    body: AnchorRequest,
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
    llm: LLMService = Depends(get_llm_service),
) -> dict:
    try:
        return await gate_service.submit_anchor(
            project_repo, gate_repo, llm, user.user_id, gate_session_id,
            body.anchor_statement,
        )
    except gate_service.GateError as exc:
        raise _http_error(exc)


@router.post("/{gate_session_id}/turn2")
async def generate_turn2(
    gate_session_id: str,
    body: AnswerRequest,
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
    llm: LLMService = Depends(get_llm_service),
) -> dict:
    try:
        return await gate_service.generate_followup(
            project_repo, gate_repo, llm, user.user_id, gate_session_id, 2, body.answer
        )
    except gate_service.GateError as exc:
        raise _http_error(exc)


@router.post("/{gate_session_id}/turn3")
async def generate_turn3(
    gate_session_id: str,
    body: AnswerRequest,
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
    llm: LLMService = Depends(get_llm_service),
) -> dict:
    try:
        return await gate_service.generate_followup(
            project_repo, gate_repo, llm, user.user_id, gate_session_id, 3, body.answer
        )
    except gate_service.GateError as exc:
        raise _http_error(exc)


@router.post("/{gate_session_id}/evaluate")
async def evaluate_gate(
    gate_session_id: str,
    body: AnswerRequest,
    user: CurrentUser = Depends(require_user),
    project_repo: ProjectRepository = Depends(get_project_repository),
    gate_repo: GateSessionRepository = Depends(get_gate_session_repository),
    llm: LLMService = Depends(get_llm_service),
) -> dict:
    try:
        return await gate_service.evaluate_gate(
            project_repo, gate_repo, llm, user.user_id, gate_session_id, body.answer
        )
    except gate_service.GateError as exc:
        raise _http_error(exc)
