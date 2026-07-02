"""Supabase JWT verification (design: docs/auth.md, Milestone 3).

Supabase signs access tokens with ES256; the public keys are served at
{SUPABASE_URL}/auth/v1/.well-known/jwks.json. PyJWT's PyJWKClient fetches and
caches them. Verification requires a valid signature, an unexpired `exp`,
`aud == "authenticated"`, and a `sub` claim (the user id).

Test seam: `_jwks_client()` is the only network touchpoint. Tests replace it
with a stub returning a locally generated ES256 key, which exercises the whole
verification path except the live HTTP fetch (see tests/test_auth_dependency.py).
"""

from functools import lru_cache

import jwt

from app.core.config import get_settings

AUDIENCE = "authenticated"
ALGORITHMS = ["ES256"]


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured; cannot verify JWTs.")
    return jwt.PyJWKClient(settings.jwks_url)


def verify_supabase_jwt(token: str) -> dict:
    """Return verified claims, or raise jwt.InvalidTokenError (any malformed,
    expired, mis-audienced, or wrongly signed token) / RuntimeError (backend
    misconfigured). Callers map InvalidTokenError to 401."""
    # Parse the header first so malformed tokens fail as token errors even
    # when SUPABASE_URL is unset (401, not a config-error 500).
    jwt.get_unverified_header(token)
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=ALGORITHMS,
        audience=AUDIENCE,
        options={"require": ["exp", "sub"]},
    )
