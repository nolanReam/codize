"""In-memory ProjectRepository fake — business rules are tested against this
because live Supabase writes need env vars this environment doesn't have."""

import copy
import itertools
import uuid


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
