"""Auth dependency tests.

Tokens are signed locally with a generated ES256 key and verified through the
real verification path; only the JWKS network fetch is stubbed (the seam noted
in app/core/security.py). Live JWKS verification against Supabase remains
unverified until backend env vars are available.
"""

import time
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.core import security
from app.deps.auth import CurrentUser, require_user
from app.main import create_app

USER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

_private_key = ec.generate_private_key(ec.SECP256R1())
_other_key = ec.generate_private_key(ec.SECP256R1())


class StubJWKSClient:
    """Stands in for jwt.PyJWKClient: same interface, no network."""

    def __init__(self, public_key):
        self._key = public_key

    def get_signing_key_from_jwt(self, token):
        pyjwt.get_unverified_header(token)  # malformed tokens raise, like the real client
        return SimpleNamespace(key=self._key)


def make_token(key=_private_key, **overrides):
    claims = {
        "sub": USER_ID,
        "aud": "authenticated",
        "email": "gate-test@codize.local",
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return pyjwt.encode(claims, key, algorithm="ES256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://stub-project.supabase.co")
    monkeypatch.setattr(
        security, "_jwks_client", lambda: StubJWKSClient(_private_key.public_key())
    )
    app = create_app()
    router = APIRouter()

    @router.get("/protected")  # test-only route; no product routes exist yet
    async def protected(user: CurrentUser = Depends(require_user)):
        return {"user_id": user.user_id}

    app.include_router(router)
    return TestClient(app)


def assert_401(resp):
    assert resp.status_code == 401
    assert resp.json()["error"]["status"] == 401
    assert resp.headers["WWW-Authenticate"] == "Bearer"


def test_missing_token_returns_401(client):
    assert_401(client.get("/protected"))


def test_wrong_scheme_returns_401(client):
    assert_401(client.get("/protected", headers={"Authorization": "Basic abc123"}))


def test_malformed_token_returns_401(client):
    assert_401(client.get("/protected", headers={"Authorization": "Bearer not-a-jwt"}))


def test_expired_token_returns_401(client):
    token = make_token(exp=int(time.time()) - 60)
    assert_401(client.get("/protected", headers={"Authorization": f"Bearer {token}"}))


def test_wrong_audience_returns_401(client):
    token = make_token(aud="anon")
    assert_401(client.get("/protected", headers={"Authorization": f"Bearer {token}"}))


def test_wrong_signing_key_returns_401(client):
    token = make_token(key=_other_key)
    assert_401(client.get("/protected", headers={"Authorization": f"Bearer {token}"}))


def test_missing_sub_returns_401(client):
    token = make_token(sub=None)
    assert_401(client.get("/protected", headers={"Authorization": f"Bearer {token}"}))


def test_valid_token_yields_current_user(client):
    resp = client.get("/protected", headers={"Authorization": f"Bearer {make_token()}"})
    assert resp.status_code == 200
    assert resp.json() == {"user_id": USER_ID}


def test_malformed_token_is_401_even_when_unconfigured(client, monkeypatch):
    # Header parsing fails before the JWKS client is touched, so a garbage
    # token is a token error (401), not a config error (500).
    def unconfigured():
        raise RuntimeError("SUPABASE_URL is not configured; cannot verify JWTs.")

    monkeypatch.setattr(security, "_jwks_client", unconfigured)
    assert_401(client.get("/protected", headers={"Authorization": "Bearer garbage"}))
