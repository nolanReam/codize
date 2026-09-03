"""Consistent JSON error shape for every non-2xx response:

    {"error": {"status": <int>, "message": <str>}}

Unhandled exceptions become a bare 500 — internal details (exception text,
stack traces) never reach the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.v2_repository import V2RepositoryError


logger = logging.getLogger(__name__)


def error_response(status_code: int, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"status": status_code, "message": message}},
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(exc.status_code, str(exc.detail), getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "Invalid request.")

    @app.exception_handler(V2RepositoryError)
    async def v2_repository_exception_handler(
        request: Request, exc: V2RepositoryError,
    ) -> JSONResponse:
        route = request.scope.get("route")
        route_template = getattr(route, "path", "unmatched")
        logger.error(
            "Unexpected V2 persistence failure: method=%s route=%s type=%s",
            request.method,
            route_template,
            type(exc).__name__,
        )
        return error_response(500, "Internal server error.")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return error_response(500, "Internal server error.")
