"""Repositories — the seam between product logic and Supabase.

The backend talks to Supabase PostgREST with the SERVICE-ROLE/secret key,
which bypasses RLS. Ownership is therefore enforced in every query here: each
read and write filters by user_id (docs/auth.md #4). The key itself is
server-only SecretStr config and never appears in responses or logs. Key
format is opaque to this module — it works with both the legacy JWT-shaped
service_role key and the newer `sb_secret_...` key.

Four repositories share the same PostgREST client base: projects (intake M6,
roadmap M7, phases M8), gate_sessions (Interrogation Gate M9), unlocks
(functional unlocks M10), and profiles (reconnection M11).
"""

import json
from typing import Protocol

import httpx

from app.core.config import Settings, get_settings

_TIMEOUT = 10.0


class ProjectRepository(Protocol):
    """What the intake/roadmap/phase services need from storage — nothing more."""

    async def get_project(self, user_id: str) -> dict | None: ...

    async def create_project(self, user_id: str, fields: dict) -> dict: ...

    async def update_project(self, user_id: str, project_id: str, fields: dict) -> dict: ...


class GateSessionRepository(Protocol):
    """What the gate service needs from storage — nothing more."""

    async def list_phase_sessions(self, user_id: str, project_id: str, phase_id: int) -> list[dict]: ...

    async def list_passed_sessions(self, user_id: str, project_id: str) -> list[dict]: ...

    async def get_session(self, user_id: str, session_id: str) -> dict | None: ...

    async def create_session(self, user_id: str, fields: dict) -> dict: ...

    async def update_session(self, user_id: str, session_id: str, fields: dict) -> dict: ...

    async def update_session_if_current(
        self,
        user_id: str,
        session_id: str,
        expected_turns: list,
        fields: dict,
    ) -> dict | None: ...


class UnlockRepository(Protocol):
    """What the unlock service needs from storage — nothing more."""

    async def list_unlocks(self, user_id: str, project_id: str) -> list[dict]: ...

    async def create_unlock(self, user_id: str, fields: dict) -> dict | None: ...


class ProfileRepository(Protocol):
    """What the reconnection service needs from storage — nothing more."""

    async def get_profile(self, user_id: str) -> dict | None: ...

    async def set_last_login(self, user_id: str, last_login_at: str) -> dict: ...


class RepositoryError(RuntimeError):
    """Storage misbehaved (network error, no row matched an owned update).
    Reaches the client only as a bare 500 — never with internal detail."""


class _SupabaseRest:
    """Shared PostgREST client. Every subclass query must filter by user_id —
    the service-role key bypasses RLS, so the query IS the ownership check."""

    def __init__(self, settings: Settings) -> None:
        self._base = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        key = settings.supabase_service_role_key.get_secret_value()
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "return=representation",
        }

    async def _request(
        self, method: str, path: str, *,
        params: dict, json: dict | None = None, headers: dict | None = None,
    ) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.request(
                    method, f"{self._base}{path}", params=params, json=json,
                    headers={**self._headers, **(headers or {})},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            raise RepositoryError(f"PostgREST {method} {path} failed") from e


class SupabaseProjectRepository(_SupabaseRest):
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


class SupabaseGateSessionRepository(_SupabaseRest):
    async def list_phase_sessions(self, user_id: str, project_id: str, phase_id: int) -> list[dict]:
        return await self._request(
            "GET", "/gate_sessions",
            params={
                "user_id": f"eq.{user_id}",
                "project_id": f"eq.{project_id}",
                "phase_id": f"eq.{phase_id}",
                "order": "created_at.desc",
            },
        )

    async def list_passed_sessions(self, user_id: str, project_id: str) -> list[dict]:
        return await self._request(
            "GET", "/gate_sessions",
            params={
                "user_id": f"eq.{user_id}",
                "project_id": f"eq.{project_id}",
                "passed": "eq.true",
                "order": "phase_id.asc",
            },
        )

    async def get_session(self, user_id: str, session_id: str) -> dict | None:
        rows = await self._request(
            "GET", "/gate_sessions",
            params={"id": f"eq.{session_id}", "user_id": f"eq.{user_id}", "limit": "1"},
        )
        return rows[0] if rows else None

    async def create_session(self, user_id: str, fields: dict) -> dict:
        rows = await self._request(
            "POST", "/gate_sessions", params={}, json={"user_id": user_id, **fields}
        )
        if not rows:
            raise RepositoryError("insert returned no row")
        return rows[0]

    async def update_session(self, user_id: str, session_id: str, fields: dict) -> dict:
        rows = await self._request(
            "PATCH", "/gate_sessions",
            params={"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"},
            json=fields,
        )
        if not rows:
            raise RepositoryError("update matched no owned row")
        return rows[0]

    async def update_session_if_current(
        self,
        user_id: str,
        session_id: str,
        expected_turns: list,
        fields: dict,
    ) -> dict | None:
        """Atomically reject a stale gate write without a new DB object."""
        expected = json.dumps(
            expected_turns, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        rows = await self._request(
            "PATCH",
            "/gate_sessions",
            params={
                "id": f"eq.{session_id}",
                "user_id": f"eq.{user_id}",
                "passed": "is.null",
                "turns": f"eq.{expected}",
            },
            json=fields,
        )
        return rows[0] if rows else None


class SupabaseUnlockRepository(_SupabaseRest):
    async def list_unlocks(self, user_id: str, project_id: str) -> list[dict]:
        return await self._request(
            "GET", "/unlocks",
            params={
                "user_id": f"eq.{user_id}",
                "project_id": f"eq.{project_id}",
                "order": "phase_number.asc",
            },
        )

    async def create_unlock(self, user_id: str, fields: dict) -> dict | None:
        # The unique (project_id, unlock_key) constraint makes grants idempotent
        # at the DB: a duplicate insert is ignored and returns no row.
        rows = await self._request(
            "POST", "/unlocks",
            params={"on_conflict": "project_id,unlock_key"},
            json={"user_id": user_id, **fields},
            headers={"Prefer": "return=representation,resolution=ignore-duplicates"},
        )
        return rows[0] if rows else None


class SupabaseProfileRepository(_SupabaseRest):
    async def get_profile(self, user_id: str) -> dict | None:
        rows = await self._request(
            "GET", "/profiles", params={"user_id": f"eq.{user_id}", "limit": "1"}
        )
        return rows[0] if rows else None

    async def set_last_login(self, user_id: str, last_login_at: str) -> dict:
        # Upsert on the profiles PK: the signup trigger normally guarantees the
        # row exists, but merge-duplicates makes acknowledge safe either way.
        rows = await self._request(
            "POST", "/profiles",
            params={"on_conflict": "user_id"},
            json={"user_id": user_id, "last_login_at": last_login_at},
            headers={"Prefer": "return=representation,resolution=merge-duplicates"},
        )
        if not rows:
            raise RepositoryError("profile upsert returned no row")
        return rows[0]


def get_project_repository() -> ProjectRepository:
    """FastAPI dependency; tests override this with an in-memory fake."""
    return SupabaseProjectRepository(get_settings())


def get_gate_session_repository() -> GateSessionRepository:
    """FastAPI dependency; tests override this with an in-memory fake."""
    return SupabaseGateSessionRepository(get_settings())


def get_unlock_repository() -> UnlockRepository:
    """FastAPI dependency; tests override this with an in-memory fake."""
    return SupabaseUnlockRepository(get_settings())


def get_profile_repository() -> ProfileRepository:
    """FastAPI dependency; tests override this with an in-memory fake."""
    return SupabaseProfileRepository(get_settings())
