from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    # Public config only — no keys, no secrets.
    return {"status": "ok", "service": "codize-backend", "environment": settings.app_env}
