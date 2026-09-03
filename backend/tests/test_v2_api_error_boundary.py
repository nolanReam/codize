"""V2 repository failures stay inside the controlled FastAPI/CORS boundary."""

from __future__ import annotations

import logging
import time
import uuid
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import security
from app.main import create_app
from app.services.v2_repository import (
    V2RepositoryConflict,
    V2RepositoryError,
    V2RepositoryNotFound,
    get_v2_repository,
)


USER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
PROJECT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
PREVIEW_ORIGIN = "https://codize-git-ox-v2-beta-staging-spark-codes-projects.vercel.app"
_key = ec.generate_private_key(ec.SECP256R1())


class FailingSetupRepository:
    def __init__(self, error: V2RepositoryError) -> None:
        self.error = error

    async def save_setup_draft(self, *args, **kwargs):
        raise self.error


def _auth_headers() -> dict[str, str]:
    token = pyjwt.encode(
        {"sub": USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        _key,
        algorithm="ES256",
    )
    return {"Authorization": f"Bearer {token}", "Origin": PREVIEW_ORIGIN}


def _client(monkeypatch: pytest.MonkeyPatch, error: V2RepositoryError) -> TestClient:
    monkeypatch.setenv("SUPABASE_URL", "https://stub-project.supabase.co")
    monkeypatch.setenv("CORS_ORIGINS", PREVIEW_ORIGIN)
    monkeypatch.setattr(
        security,
        "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=_key.public_key())
        ),
    )
    app = create_app()
    app.dependency_overrides[get_v2_repository] = lambda: FailingSetupRepository(error)
    return TestClient(app, raise_server_exceptions=False)


def _setup_payload() -> dict[str, object]:
    return {
        "workflow_version": "v2",
        "command_id": str(uuid.uuid4()),
        "expected_project_version": 1,
        "project_context": "A small tracker",
        "initial_change_label": "Show one total",
        "done_condition": "The total is visible",
    }


def test_unexpected_repository_error_is_sanitized_logged_and_keeps_cors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    leaked_detail = "sensitive persistence diagnostic"
    caplog.set_level(logging.ERROR, logger="app.core.errors")
    client = _client(monkeypatch, V2RepositoryError(leaked_detail))

    response = client.put(
        f"/v2/projects/{PROJECT_ID}/setup-draft",
        headers=_auth_headers(),
        json=_setup_payload(),
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {"status": 500, "message": "Internal server error."}
    }
    assert response.headers["access-control-allow-origin"] == PREVIEW_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert leaked_detail not in response.text
    assert leaked_detail not in caplog.text
    assert "route=/v2/projects/{project_id}/setup-draft" in caplog.text
    assert "type=V2RepositoryError" in caplog.text


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_message"),
    [
        (V2RepositoryNotFound("database detail"), 404, "V2 Project not found."),
        (
            V2RepositoryConflict("database detail"),
            409,
            "The Project setup draft changed or cannot be saved.",
        ),
    ],
)
def test_expected_repository_errors_keep_domain_statuses(
    monkeypatch: pytest.MonkeyPatch,
    error: V2RepositoryError,
    expected_status: int,
    expected_message: str,
) -> None:
    client = _client(monkeypatch, error)

    response = client.put(
        f"/v2/projects/{PROJECT_ID}/setup-draft",
        headers=_auth_headers(),
        json=_setup_payload(),
    )

    assert response.status_code == expected_status
    assert response.json() == {
        "error": {"status": expected_status, "message": expected_message}
    }


def test_request_validation_keeps_controlled_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch, V2RepositoryError("should not run"))
    payload = _setup_payload()
    payload["expected_project_version"] = 0

    response = client.put(
        f"/v2/projects/{PROJECT_ID}/setup-draft",
        headers=_auth_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"status": 422, "message": "Invalid request."}
    }
