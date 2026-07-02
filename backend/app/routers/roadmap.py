"""Roadmap routes — thin, auth-required; generation logic lives in the service.

The user id comes only from the verified JWT (require_user) and the repository
scopes every read/write to it, so a user can only ever generate or read their
own roadmap. Controlled errors map to the standard error shape; an LLM/
validation failure is a 502 with a generic message — no provider detail leaks.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, require_user
from app.services import roadmap_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.project_repository import ProjectRepository, get_project_repository

router = APIRouter(prefix="/roadmap")


def _http_error(exc: roadmap_service.RoadmapError) -> HTTPException:
    if isinstance(exc, roadmap_service.RoadmapNotFoundError):
        status = 404
    elif isinstance(exc, roadmap_service.RoadmapGenerationError):
        status = 502
    else:  # not ready / already generated
        status = 409
    return HTTPException(status_code=status, detail=str(exc))


@router.get("")
async def get_roadmap(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> dict:
    try:
        return await roadmap_service.get_roadmap(repo, user.user_id)
    except roadmap_service.RoadmapError as exc:
        raise _http_error(exc)


@router.post("/generate")
async def generate_roadmap(
    user: CurrentUser = Depends(require_user),
    repo: ProjectRepository = Depends(get_project_repository),
    llm: LLMService = Depends(get_llm_service),
) -> dict:
    try:
        return await roadmap_service.generate_roadmap(repo, llm, user.user_id)
    except roadmap_service.RoadmapError as exc:
        raise _http_error(exc)
