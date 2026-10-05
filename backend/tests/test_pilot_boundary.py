"""Deployment boundary tests: no network, database, or paid provider calls."""

import asyncio
import re
import time
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services import llm_service
from tests import test_v2_backend_routes as v2
from tests.test_v2_backend_routes import client  # noqa: F401 — reuse signed-JWT/fake-repository fixture


@pytest.fixture(params=[False, True], autouse=True)
def pilot_mode(request, monkeypatch):
    monkeypatch.setenv("CODIZE_PILOT_V2_ONLY", str(request.param).lower())
    # Fake keys ensure the exclusion works even with live providers configured.
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key-for-tests")
    get_settings.cache_clear()
    return request.param


@pytest.fixture(autouse=True)
def no_provider_calls(monkeypatch):
    complete = AsyncMock(side_effect=AssertionError("Legacy LLM invoked"))
    monkeypatch.setattr(llm_service.LLMService, "complete", complete)
    monkeypatch.setattr(llm_service.GeminiProvider, "complete", complete)
    monkeypatch.setattr(llm_service.OpenRouterProvider, "complete", complete)
    outbound = AsyncMock(side_effect=AssertionError("Provider HTTP invoked"))
    monkeypatch.setattr(llm_service, "_post_json", outbound)
    yield
    complete.assert_not_called()
    outbound.assert_not_called()


def test_mode_health_and_auth(client, pilot_mode):
    mode = client.get("/deployment-mode?pilot_v2_only=false", headers={"X-Pilot-V2-Only": "false"})
    assert mode.json() == {"pilot_v2_only": pilot_mode}
    assert mode.headers["cache-control"] == "no-store"
    assert client.get("/health").status_code == 200
    assert client.get("/v2/project-refs").status_code == 401
    assert client.get("/v2/project-refs", headers=v2.auth_headers()).status_code == 200
    assert client.get("/intake/questions", headers=v2.auth_headers()).status_code == (404 if pilot_mode else 200)
    preflight = client.options("/v2/projects", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_complete_legacy_route_set_is_absent(client, pilot_mode, monkeypatch):
    # Discover every actual legacy endpoint from the ordinary application,
    # including endpoints with methods other than GET/POST.
    monkeypatch.setenv("CODIZE_PILOT_V2_ONLY", "false")
    get_settings.cache_clear()
    ordinary = create_app()
    ordinary_paths = ordinary.openapi()["paths"]
    legacy = {path: operations for path, operations in ordinary_paths.items()
              if path not in {"/health", "/deployment-mode"} and not path.startswith("/v2/")}
    assert {path.split("/")[1] for path in legacy} == {
        "archetypes", "intake", "roadmap", "phases", "report", "gate",
        "unlocks", "reconnection", "evaluation", "workflow",
    }
    actual = client.app.openapi()["paths"]
    if not pilot_mode:
        assert all(actual[path] == operations for path, operations in legacy.items())
        return
    assert not set(legacy).intersection(actual)
    assert set(actual) == {path for path in ordinary_paths if path not in legacy}
    token = v2.pyjwt.encode({
        "sub": v2.USER_A, "aud": "authenticated", "exp": int(time.time()) + 3600,
        "pilot_v2_only": False, "app_metadata": {"pilot_v2_only": False},
    }, v2._key, algorithm="ES256")
    for route in legacy:
        path = re.sub(r"\{[^}]+\}", "1", route)
        for method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"}:
            for suffix in ("", "/"):
                response = client.request(method, path + suffix + "?pilot_v2_only=false&workflow_version=v2",
                    headers={"Authorization": f"Bearer {token}", "X-Pilot-V2-Only": "false", "X-HTTP-Method-Override": "POST"},
                    json={"pilot_v2_only": False, "user_id": v2.USER_A, "workflow_version": "v2"})
                assert response.status_code == 404, (method, path, response.text)


def test_project_picker_mode_and_no_legacy_read(client, pilot_mode, monkeypatch):
    legacy = client.app.state.test_legacy_repo
    asyncio.run(legacy.create_project(v2.USER_A, {}))
    project = v2.create_project(client)["project"]
    if pilot_mode:
        monkeypatch.setattr(legacy, "get_project", AsyncMock(side_effect=AssertionError("V1 read")))
    refs = client.get("/v2/project-refs", headers=v2.auth_headers()).json()["projects"]
    assert [r["workflow_version"] for r in refs] == (["v2"] if pilot_mode else ["v1", "v2"])
    assert refs[-1]["project_id"] == project["project_id"]


def test_v2_manual_build_loop_in_both_modes(client):
    # Covers setup, plan, teaching, prompt, agent choice, handoff, return,
    # performed check, completion, replay, and ownership in both deployments.
    v2.test_phase4_manual_loop_completes_only_after_student_check(client)


def test_default_and_invalid_setting(monkeypatch):
    monkeypatch.delenv("CODIZE_PILOT_V2_ONLY")
    assert Settings(_env_file=None).codize_pilot_v2_only is False
    monkeypatch.setenv("CODIZE_PILOT_V2_ONLY", "invalid")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
