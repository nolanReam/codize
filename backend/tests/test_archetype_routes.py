"""Archetype route tests: read-only, auth-enforced, controlled errors.

Auth uses the same offline pattern as test_auth_dependency.py: tokens signed
with a local ES256 key, only the JWKS fetch stubbed.
"""

import time
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import security
from app.main import create_app

_key = ec.generate_private_key(ec.SECP256R1())


def make_token():
    claims = {
        "sub": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return pyjwt.encode(claims, _key, algorithm="ES256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://stub-project.supabase.co")
    monkeypatch.setattr(
        security, "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=_key.public_key())
        ),
    )
    return TestClient(create_app())


def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


def test_routes_require_auth(client):
    for path in ("/archetypes", "/archetypes/1"):
        resp = client.get(path)
        assert resp.status_code == 401
        assert resp.json()["error"]["status"] == 401


def test_list_archetypes_route(client):
    resp = client.get("/archetypes", headers=auth_headers())
    assert resp.status_code == 200
    archetypes = resp.json()["archetypes"]
    assert [a["archetype_id"] for a in archetypes] == [1, 2, 3]
    assert [a["archetype_name"] for a in archetypes] == [
        "AI-Powered App", "REST API Backend", "Full-Stack Web App",
    ]


@pytest.mark.parametrize("archetype_id", [1, 2, 3])
def test_get_archetype_route(client, archetype_id):
    resp = client.get(f"/archetypes/{archetype_id}", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["archetype_id"] == archetype_id
    assert len(body["phases"]) == 7
    assert body["phases"][-1]["phase_title"] == "Pre-Deployment Security Checklist"


def test_unknown_archetype_id_returns_controlled_404(client):
    resp = client.get("/archetypes/4", headers=auth_headers())
    assert resp.status_code == 404
    assert resp.json() == {"error": {"status": 404, "message": "Unknown archetype id."}}


def test_non_integer_archetype_id_returns_controlled_error(client):
    resp = client.get("/archetypes/not-a-number", headers=auth_headers())
    assert resp.status_code == 422
    assert resp.json() == {"error": {"status": 422, "message": "Invalid request."}}


def test_archetype_responses_contain_no_secrets(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key-for-tests")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key-for-tests")
    for path in ("/archetypes", "/archetypes/1"):
        text = client.get(path, headers=auth_headers()).text
        assert "fake-service-role-key-for-tests" not in text
        assert "fake-gemini-key-for-tests" not in text
        assert "fake-openrouter-key-for-tests" not in text
