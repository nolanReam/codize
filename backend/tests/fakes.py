"""In-memory repository fakes and a scripted LLM — business rules are tested
against these; the live Supabase/LLM paths are verified separately."""

import copy
import itertools
import uuid

from app.services.llm_service import LLMError
from app.services.project_repository import RepositoryError


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._seq = itertools.count()

    async def get_project(self, user_id: str) -> dict | None:
        rows = [r for r in self._rows if r["user_id"] == user_id]
        if not rows:
            return None
        return copy.deepcopy(max(rows, key=lambda r: r["created_at"]))

    async def create_project(self, user_id: str, fields: dict) -> dict:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "intake_purpose": None,
            "intake_scope": None,
            "intake_stack": None,
            "intake_self_assessment": None,
            "intake_timeline": None,
            "intake_completed_at": None,
            "archetype_id": None,
            "stack_warning": None,
            "roadmap": None,
            "current_phase": 1,
            "task_progress": {},
            "workflow_artifacts": {},
            "gate_history_summary": None,
            "status": "intake",
            "created_at": next(self._seq),
        }
        row.update(fields)
        self._rows.append(row)
        return copy.deepcopy(row)

    async def update_project(self, user_id: str, project_id: str, fields: dict) -> dict:
        for row in self._rows:
            if row["id"] == project_id and row["user_id"] == user_id:
                row.update(fields)
                return copy.deepcopy(row)
        raise RuntimeError("update matched no owned row")

    async def update_workflow_artifacts_if_current(
        self,
        user_id: str,
        project_id: str,
        expected: dict,
        replacement: dict,
    ) -> dict | None:
        for row in self._rows:
            if row["id"] == project_id and row["user_id"] == user_id:
                if row.get("workflow_artifacts") != expected:
                    return None
                row["workflow_artifacts"] = copy.deepcopy(replacement)
                return copy.deepcopy(row)
        return None


class InMemoryGateSessionRepository:
    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._seq = itertools.count()

    async def list_phase_sessions(self, user_id: str, project_id: str, phase_id: int) -> list[dict]:
        rows = [
            r for r in self._rows
            if r["user_id"] == user_id
            and r["project_id"] == project_id
            and r["phase_id"] == phase_id
        ]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return copy.deepcopy(rows)

    async def list_passed_sessions(self, user_id: str, project_id: str) -> list[dict]:
        rows = [
            r for r in self._rows
            if r["user_id"] == user_id
            and r["project_id"] == project_id
            and r["passed"] is True
        ]
        rows.sort(key=lambda r: r["phase_id"])
        return copy.deepcopy(rows)

    async def get_session(self, user_id: str, session_id: str) -> dict | None:
        for row in self._rows:
            if row["id"] == session_id and row["user_id"] == user_id:
                return copy.deepcopy(row)
        return None

    async def create_session(self, user_id: str, fields: dict) -> dict:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "project_id": None,
            "phase_id": None,
            "anchor_statement": None,
            "turns": [],
            "score": None,
            "passed": None,
            "reason": None,
            "failed_at": None,
            "passed_at": None,
            "created_at": next(self._seq),
        }
        row.update(fields)
        self._rows.append(row)
        return copy.deepcopy(row)

    async def update_session(self, user_id: str, session_id: str, fields: dict) -> dict:
        for row in self._rows:
            if row["id"] == session_id and row["user_id"] == user_id:
                row.update(fields)
                return copy.deepcopy(row)
        raise RuntimeError("update matched no owned row")

    async def update_session_if_current(
        self,
        user_id: str,
        session_id: str,
        expected_turns: list,
        fields: dict,
    ) -> dict | None:
        for row in self._rows:
            if row["id"] == session_id and row["user_id"] == user_id:
                if row["passed"] is not None or row["turns"] != expected_turns:
                    return None
                row.update(fields)
                return copy.deepcopy(row)
        return None


class InMemoryUnlockRepository:
    """Mirrors the unlocks table, including the unique (project_id, unlock_key)
    constraint with PostgREST's ignore-duplicates behavior (returns None)."""

    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._seq = itertools.count()

    async def list_unlocks(self, user_id: str, project_id: str) -> list[dict]:
        rows = [
            r for r in self._rows
            if r["user_id"] == user_id and r["project_id"] == project_id
        ]
        rows.sort(key=lambda r: r["phase_number"])
        return copy.deepcopy(rows)

    async def create_unlock(self, user_id: str, fields: dict) -> dict | None:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "project_id": None,
            "phase_number": None,
            "unlock_key": None,
            "granted_at": f"2026-07-03T00:00:{next(self._seq):02d}+00:00",
        }
        row.update(fields)
        for existing in self._rows:
            if (
                existing["project_id"] == row["project_id"]
                and existing["unlock_key"] == row["unlock_key"]
            ):
                return None
        self._rows.append(row)
        return copy.deepcopy(row)


class RaisingUnlockRepository:
    """Every call fails — verifies unlock storage errors never break a PASS."""

    async def list_unlocks(self, user_id: str, project_id: str) -> list[dict]:
        raise RepositoryError("unlock storage unavailable")

    async def create_unlock(self, user_id: str, fields: dict) -> dict | None:
        raise RepositoryError("unlock storage unavailable")


class InMemoryProfileRepository:
    """Mirrors the profiles table (PK user_id; live rows are auto-created by
    the signup trigger with last_login_at defaulting to now)."""

    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def seed(self, user_id: str, last_login_at: str) -> None:
        """Test helper: what the signup trigger (or an earlier acknowledge)
        would have left behind."""
        self._rows[user_id] = {
            "user_id": user_id,
            "display_name": None,
            "last_login_at": last_login_at,
        }

    async def get_profile(self, user_id: str) -> dict | None:
        row = self._rows.get(user_id)
        return copy.deepcopy(row) if row else None

    async def set_last_login(self, user_id: str, last_login_at: str) -> dict:
        if user_id not in self._rows:
            self.seed(user_id, last_login_at)
        self._rows[user_id]["last_login_at"] = last_login_at
        return copy.deepcopy(self._rows[user_id])


class ScriptedLLM:
    """Returns queued responses in order; an Exception in the queue is raised.
    Records (prompt, temperature) for assertions."""

    def __init__(self, responses=()) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, float]] = []

    async def complete(self, prompt: str, temperature: float) -> str:
        self.calls.append((prompt, temperature))
        if not self.responses:
            raise LLMError("scripted LLM exhausted")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
