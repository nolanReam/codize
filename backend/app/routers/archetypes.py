"""Read-only archetype template routes. All logic lives in the service layer."""

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import require_user
from app.services import template_service

router = APIRouter(dependencies=[Depends(require_user)])


@router.get("/archetypes")
async def list_archetypes() -> dict:
    return {"archetypes": template_service.list_archetypes()}


@router.get("/archetypes/{archetype_id}")
async def get_archetype(archetype_id: int) -> dict:
    try:
        return template_service.get_template(archetype_id)
    except template_service.UnknownArchetypeError:
        raise HTTPException(status_code=404, detail="Unknown archetype id.")
