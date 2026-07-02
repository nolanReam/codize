"""Project repository — the seam between intake logic and Supabase.

The backend talks to Supabase PostgREST with the SERVICE-ROLE key, which
bypasses RLS. Ownership is therefore enforced in every query here: each read
and write filters by user_id (docs/auth.md #4). The key itself is server-only
SecretStr config and never appears in responses or logs.

LIVE WRITES UNVERIFIED: this implementation was built in a session without
Supabase env vars. Business rules are tested against an in-memory fake
(tests/fakes.py); run the live path once SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY are available.
"""

from typing import Protocol

import httpx

from app.core.config import Settings, get_settings

_TIMEOUT = 10.0


class ProjectRepository(Protocol):
    """What the intake service needs from storage — nothing more."""

    async def get_project(self, user_id: str) -> dict | None: ...

    async def create_project(self, user_id: str, fields: dict) -> dict: ...

    async def update_project(self, user_id: str, project_id: str, fields: dict) -> dict: ...


class RepositoryError(RuntimeError):
    """Storage misbehaved (network error, no row matched an owned update).
    Reaches the client only as a bare 500 — never with internal detail."""


class SupabaseProjectRepository:
    def __init__(self, settings: Settings) -> None:
        self._base = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        key = settings.supabase_service_role_key.get_secret_value()
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "return=representation",
        }

    async def _request(self, method: str, path: str, *, params: dict, json: dict | None = None) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.request(
                    method, f"{self._base}{path}", params=params, json=json, headers=self._headers
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            raise RepositoryError(f"PostgREST {method} {path} failed") from e

    async def get_project(self, user_id: str) -> dict | None:
        rows = await self._request(
            "GET", "/projects",
            params={"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": "1"},
        )
        return rows[0] if rows else None

    async def create_project(self, user_id: str, fields: dict) -> dict:
        rows = await self._request("POST", "/projects", params={}, json={"user_id": user_id, **fields})
        if not rows:
            raise RepositoryError("insert returned no row")
        return rows[0]

    async def update_project(self, user_id: str, project_id: str, fields: dict) -> dict:
        # user_id in the filter, not just the id: with the service-role key the
        # query itself is the ownership check.
        rows = await self._request(
            "PATCH", "/projects",
            params={"id": f"eq.{project_id}", "user_id": f"eq.{user_id}"},
            json=fields,
        )
        if not rows:
            raise RepositoryError("update matched no owned row")
        return rows[0]


def get_project_repository() -> ProjectRepository:
    """FastAPI dependency; tests override this with an in-memory fake."""
    return SupabaseProjectRepository(get_settings())
