"""In-memory repository fakes and a scripted LLM — business rules are tested
against these; the live Supabase/LLM paths are verified separately."""

import copy
import itertools
import uuid

from app.services.llm_service import LLMError


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
