"""Codize API entrypoint.

Run from backend/:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.routers import (
    archetypes,
    evaluation,
    gate,
    health,
    intake,
    phases,
    reconnection,
    roadmap,
    unlocks,
    workflow,
)
from app.services import template_service


def create_app() -> FastAPI:
    settings = get_settings()
    template_service.validate_at_startup()  # broken templates must fail here, not at first request
    app = FastAPI(
        title="Codize API",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,  # explicit origins only, never "*"
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(archetypes.router)
    app.include_router(intake.router)
    app.include_router(roadmap.router)
    app.include_router(phases.router)
    app.include_router(gate.router)
    app.include_router(unlocks.router)
    app.include_router(reconnection.router)
    app.include_router(evaluation.router)
    app.include_router(workflow.router)
    return app


app = create_app()
