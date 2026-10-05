"""Codize API entrypoint.

Run from backend/:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI, Response
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
    report,
    reconnection,
    roadmap,
    unlocks,
    v2_projects,
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
        expose_headers=["Retry-After", "X-Codize-Error-Code"],
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.state.pilot_v2_only = settings.codize_pilot_v2_only

    @app.get("/deployment-mode")
    async def deployment_mode(response: Response) -> dict[str, bool]:
        """Only the nonsecret, startup-selected mode; never expose settings."""
        response.headers["Cache-Control"] = "no-store"
        return {"pilot_v2_only": app.state.pilot_v2_only}

    # Auth/security and V2 repositories are shared infrastructure, not V1
    # features. Omit the complete legacy route set before serving requests.
    if not settings.codize_pilot_v2_only:
        app.include_router(archetypes.router)
        app.include_router(intake.router)
        app.include_router(roadmap.router)
        app.include_router(phases.router)
        app.include_router(report.router)
        app.include_router(gate.router)
        app.include_router(unlocks.router)
        app.include_router(reconnection.router)
        app.include_router(evaluation.router)
        app.include_router(workflow.router)
    app.include_router(v2_projects.router)
    return app


app = create_app()
