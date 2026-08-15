"""Owner-scoped persistence boundary for the separate Codize V2 domain.

V2 table reads use the backend credential and always constrain both owner and
explicit Project ID. Mutations use only reviewed PostgreSQL RPCs; the backend
credential has no direct V2 table-write grants.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings, get_settings
from app.domain.v2 import (
    CurrentChangeKind,
    CurrentChangeState,
    PlanItemStatus,
    PlanScopeBand,
    ProjectLifecycle,
    ProjectRef,
    ResumeStep,
    SetupResumeStep,
    V2CurrentChange,
    V2Plan,
    V2PlanItem,
    V2Project,
    WorkflowVersion,
    validate_resume_state,
)

_TIMEOUT = 10.0
_PROJECT_SELECT = (
    "id,owner_user_id,workflow_version,display_name,lifecycle_state,"
    "setup_resume_step,coding_agent_key,plan_version,first_version_completed_at,"
    "version,created_at,updated_at"
)
_PLAN_ITEM_SELECT = (
    "id,project_id,owner_user_id,label,intended_outcome,scope_band,status,"
    "order_key,completed_at,terminal_current_change_id,version"
)
_CURRENT_CHANGE_SELECT = (
    "id,project_id,owner_user_id,plan_item_id,change_kind,lifecycle_state,"
    "resume_step,goal_snapshot,done_condition_snapshot,boundary_snapshots,"
    "version,created_at,updated_at,completed_at,cancelled_at,"
    "cancellation_command_id,cancellation_reason_key"
)


class V2RepositoryError(RuntimeError):
    """Unexpected or unavailable persistence behavior; safe details stay server-side."""


class V2RepositoryNotFound(V2RepositoryError):
    """Absent, deleted, and other-owner identifiers share this outcome."""


class V2RepositoryConflict(V2RepositoryError):
    """Optimistic version, uniqueness, or retry identity conflict."""


class V2RepositoryInvalidState(V2RepositoryError):
    """The database rejected a malformed or illegal domain command."""


class _ProjectRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    owner_user_id: UUID
    workflow_version: WorkflowVersion
    display_name: str
    lifecycle_state: ProjectLifecycle
    setup_resume_step: SetupResumeStep
    coding_agent_key: str | None
    plan_version: int = Field(gt=0)
    first_version_completed_at: datetime | None
    version: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime


class _PlanItemRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    project_id: UUID
    owner_user_id: UUID
    label: str
    intended_outcome: str
    scope_band: PlanScopeBand
    status: PlanItemStatus
    order_key: int
    completed_at: datetime | None = None
    terminal_current_change_id: UUID | None = None
    version: int = Field(gt=0)


class _CurrentChangeRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    project_id: UUID
    owner_user_id: UUID
    plan_item_id: UUID | None
    change_kind: CurrentChangeKind
    lifecycle_state: CurrentChangeState
    resume_step: ResumeStep | None
    goal_snapshot: str
    done_condition_snapshot: str | None
    boundary_snapshots: list[str]
    version: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_command_id: UUID | None
    cancellation_reason_key: str | None


class V2Repository(Protocol):
    async def create_project(
        self,
        owner_user_id: str,
        command_id: UUID,
        display_name: str,
        creation_intent: str,
        recovery_context: dict[str, Any] | None,
        current_change_command_id: UUID | None,
    ) -> tuple[V2Project, bool]: ...

    async def get_project(self, owner_user_id: str, project_id: UUID) -> V2Project | None: ...

    async def list_projects(self, owner_user_id: str) -> list[V2Project]: ...

    async def promote_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
    ) -> tuple[V2Project, bool]: ...

    async def purge_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
    ) -> bool: ...

    async def get_plan(self, owner_user_id: str, project_id: UUID) -> V2Plan | None: ...

    async def mutate_plan(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        expected_plan_version: int,
        command_id: UUID,
        operations: list[dict[str, Any]],
        expected_current_change_version: int | None,
        linked_item_action: str | None,
        cancellation_command_id: UUID | None,
        cancellation_reason_key: str | None,
    ) -> V2Plan: ...

    async def start_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
        plan_item_id: UUID | None,
        change_kind: str,
        goal_snapshot: str,
    ) -> tuple[V2CurrentChange, bool]: ...

    async def get_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
    ) -> V2CurrentChange | None: ...

    async def get_current_change_by_id(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
    ) -> V2CurrentChange | None: ...

    async def cancel_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        cancellation_command_id: UUID,
        cancellation_reason_key: str,
    ) -> tuple[V2CurrentChange, bool]: ...


def _project_from_row(raw: Any, *, expected_owner: str | None = None) -> V2Project:
    try:
        row = _ProjectRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Project row") from exc
    if row.workflow_version is not WorkflowVersion.V2:
        raise V2RepositoryError("database returned a non-V2 Project from v2_projects")
    if expected_owner is not None and str(row.owner_user_id) != expected_owner:
        raise V2RepositoryError("database returned a V2 Project for the wrong owner")
    if not row.display_name.strip():
        raise V2RepositoryError("database returned a blank V2 Project name")
    return V2Project(
        ref=ProjectRef(WorkflowVersion.V2, row.id),
        display_name=row.display_name,
        lifecycle_state=row.lifecycle_state,
        setup_resume_step=row.setup_resume_step,
        plan_version=row.plan_version,
        version=row.version,
        coding_agent_key=row.coding_agent_key,
        first_version_completed_at=row.first_version_completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _plan_item_from_row(
    raw: Any,
    *,
    expected_owner: str,
    expected_project_id: UUID,
) -> V2PlanItem:
    try:
        row = _PlanItemRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Plan Item row") from exc
    if str(row.owner_user_id) != expected_owner or row.project_id != expected_project_id:
        raise V2RepositoryError("database returned a V2 Plan Item outside the owned Project")
    if row.status is PlanItemStatus.REMOVED:
        raise V2RepositoryError("ordinary V2 Plan projection included a removed item")
    if row.order_key <= 0:
        raise V2RepositoryError("ordinary V2 Plan projection included an invalid order")
    if (
        row.status is PlanItemStatus.DONE
        and row.completed_at is None
        or row.status is not PlanItemStatus.DONE
        and (row.completed_at is not None or row.terminal_current_change_id is not None)
    ):
        raise V2RepositoryError("database returned inconsistent V2 Plan Item terminal state")
    return V2PlanItem(
        id=row.id,
        project_id=row.project_id,
        label=row.label,
        intended_outcome=row.intended_outcome,
        scope_band=row.scope_band,
        status=row.status,
        order_key=row.order_key,
        version=row.version,
        completed_at=row.completed_at,
        terminal_current_change_id=row.terminal_current_change_id,
    )


def _current_change_from_row(
    raw: Any,
    *,
    expected_owner: str,
    expected_project_id: UUID,
) -> V2CurrentChange:
    try:
        row = _CurrentChangeRow.model_validate(raw)
    except ValidationError as exc:
        raise V2RepositoryError("malformed V2 Current Change row") from exc
    if str(row.owner_user_id) != expected_owner or row.project_id != expected_project_id:
        raise V2RepositoryError("database returned a V2 Current Change outside the owned Project")
    if not row.goal_snapshot.strip() or any(not value.strip() for value in row.boundary_snapshots):
        raise V2RepositoryError("database returned malformed V2 Current Change snapshots")
    try:
        validate_resume_state(row.lifecycle_state, row.resume_step)
    except ValueError as exc:
        raise V2RepositoryError("database returned an illegal V2 Current Change resume state") from exc
    if row.lifecycle_state is CurrentChangeState.COMPLETED:
        timestamps_are_valid = row.completed_at is not None and row.cancelled_at is None
        cancellation_is_valid = (
            row.cancellation_command_id is None and row.cancellation_reason_key is None
        )
    elif row.lifecycle_state is CurrentChangeState.CANCELLED:
        timestamps_are_valid = row.completed_at is None and row.cancelled_at is not None
        cancellation_is_valid = (
            row.cancellation_command_id is not None
            and row.cancellation_reason_key is not None
            and bool(row.cancellation_reason_key.strip())
        )
    else:
        timestamps_are_valid = row.completed_at is None and row.cancelled_at is None
        cancellation_is_valid = (
            row.cancellation_command_id is None and row.cancellation_reason_key is None
        )
    if not timestamps_are_valid or not cancellation_is_valid:
        raise V2RepositoryError("database returned inconsistent V2 Current Change terminal state")
    return V2CurrentChange(
        id=row.id,
        project_ref=ProjectRef(WorkflowVersion.V2, row.project_id),
        plan_item_id=row.plan_item_id,
        change_kind=row.change_kind,
        lifecycle_state=row.lifecycle_state,
        resume_step=row.resume_step,
        goal_snapshot=row.goal_snapshot,
        done_condition_snapshot=row.done_condition_snapshot,
        boundary_snapshots=tuple(row.boundary_snapshots),
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
        cancelled_at=row.cancelled_at,
        cancellation_command_id=row.cancellation_command_id,
        cancellation_reason_key=row.cancellation_reason_key,
    )


class SupabaseV2Repository:
    def __init__(self, settings: Settings) -> None:
        self._base = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        key = settings.supabase_service_role_key.get_secret_value()
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.request(
                    method,
                    f"{self._base}{path}",
                    params=params or {},
                    json=body,
                    headers=self._headers,
                )
        except httpx.RequestError as exc:
            raise V2RepositoryError("V2 persistence request failed") from exc

        if response.is_error:
            code = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    code = payload.get("code")
            except ValueError:
                pass
            if code == "P0002":
                raise V2RepositoryNotFound("owned V2 resource not found")
            if code in {"40001", "23505"}:
                raise V2RepositoryConflict("V2 command conflicted")
            if code in {"22023", "22P02", "23514"}:
                raise V2RepositoryInvalidState("V2 command was invalid for current state")
            raise V2RepositoryError("V2 persistence returned an unexpected error")

        try:
            return response.json()
        except ValueError as exc:
            raise V2RepositoryError("V2 persistence returned malformed JSON") from exc

    async def _rpc(self, name: str, body: dict[str, Any]) -> Any:
        return await self._request("POST", f"/rpc/{name}", body=body)

    @staticmethod
    def _object(value: Any, context: str) -> dict[str, Any]:
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
            value = value[0]
        if not isinstance(value, dict):
            raise V2RepositoryError(f"{context} returned a malformed object")
        return value

    async def create_project(
        self,
        owner_user_id: str,
        command_id: UUID,
        display_name: str,
        creation_intent: str,
        recovery_context: dict[str, Any] | None,
        current_change_command_id: UUID | None,
    ) -> tuple[V2Project, bool]:
        payload = self._object(
            await self._rpc(
                "create_v2_project",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_create_command_id": str(command_id),
                    "p_display_name": display_name,
                    "p_creation_intent": creation_intent,
                    "p_recovery_context": recovery_context,
                    "p_current_change_command_id": (
                        str(current_change_command_id)
                        if current_change_command_id is not None
                        else None
                    ),
                },
            ),
            "create_v2_project",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("create_v2_project omitted replay state")
        return (
            _project_from_row(payload.get("project"), expected_owner=owner_user_id),
            payload["replayed"],
        )

    async def get_project(self, owner_user_id: str, project_id: UUID) -> V2Project | None:
        rows = await self._request(
            "GET",
            "/v2_projects",
            params={
                "select": _PROJECT_SELECT,
                "id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "workflow_version": "eq.v2",
                "lifecycle_state": "neq.deletion_pending",
                "limit": "1",
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 Project read returned malformed rows")
        if not rows:
            return None
        if len(rows) != 1:
            raise V2RepositoryError("explicit V2 Project read returned multiple rows")
        return _project_from_row(rows[0], expected_owner=owner_user_id)

    async def list_projects(self, owner_user_id: str) -> list[V2Project]:
        rows = await self._request(
            "GET",
            "/v2_projects",
            params={
                "select": _PROJECT_SELECT,
                "owner_user_id": f"eq.{owner_user_id}",
                "workflow_version": "eq.v2",
                "lifecycle_state": "neq.deletion_pending",
                "order": "updated_at.desc,id.asc",
            },
        )
        if not isinstance(rows, list):
            raise V2RepositoryError("V2 Project list returned malformed rows")
        return [_project_from_row(row, expected_owner=owner_user_id) for row in rows]

    async def promote_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
    ) -> tuple[V2Project, bool]:
        payload = self._object(
            await self._rpc(
                "promote_v2_temporary_project",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_expected_project_version": expected_project_version,
                    "p_command_id": str(command_id),
                },
            ),
            "promote_v2_temporary_project",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("Project promotion omitted replay state")
        return (
            _project_from_row(payload.get("project"), expected_owner=owner_user_id),
            payload["replayed"],
        )

    async def purge_temporary_project(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
    ) -> bool:
        result = await self._rpc(
            "purge_v2_project",
            {
                "p_owner_user_id": owner_user_id,
                "p_project_id": str(project_id),
                "p_expected_project_version": expected_project_version,
                "p_purge_kind": "temporary_recovery",
                "p_evidence_actions": [],
            },
        )
        if isinstance(result, list) and len(result) == 1:
            result = result[0]
        if result is not True:
            raise V2RepositoryError("temporary V2 Project purge returned malformed success")
        return True

    async def get_plan(self, owner_user_id: str, project_id: UUID) -> V2Plan | None:
        # PostgREST does not give two separate HTTP reads one shared snapshot.
        # Re-read the root version and retry once so a mixed Plan is never
        # returned as current.
        for _ in range(2):
            project = await self.get_project(owner_user_id, project_id)
            if project is None:
                return None
            rows = await self._request(
                "GET",
                "/v2_plan_items",
                params={
                    "select": _PLAN_ITEM_SELECT,
                    "project_id": f"eq.{project_id}",
                    "owner_user_id": f"eq.{owner_user_id}",
                    "status": "neq.removed",
                    "order": "scope_band.asc,order_key.asc,id.asc",
                },
            )
            if not isinstance(rows, list):
                raise V2RepositoryError("V2 Plan read returned malformed rows")
            current = await self.get_project(owner_user_id, project_id)
            if current is None:
                return None
            if (
                current.version == project.version
                and current.plan_version == project.plan_version
            ):
                return V2Plan(
                    project_ref=project.ref,
                    project_version=project.version,
                    plan_version=project.plan_version,
                    items=tuple(
                        _plan_item_from_row(
                            row,
                            expected_owner=owner_user_id,
                            expected_project_id=project_id,
                        )
                        for row in rows
                    ),
                )
        raise V2RepositoryConflict("V2 Plan changed while it was being read")

    async def mutate_plan(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        expected_plan_version: int,
        command_id: UUID,
        operations: list[dict[str, Any]],
        expected_current_change_version: int | None,
        linked_item_action: str | None,
        cancellation_command_id: UUID | None,
        cancellation_reason_key: str | None,
    ) -> V2Plan:
        payload = self._object(
            await self._rpc(
                "mutate_v2_plan",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_expected_project_version": expected_project_version,
                    "p_expected_plan_version": expected_plan_version,
                    "p_command_id": str(command_id),
                    "p_operations": operations,
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_linked_item_action": linked_item_action,
                    "p_cancellation_command_id": (
                        str(cancellation_command_id) if cancellation_command_id else None
                    ),
                    "p_cancellation_reason_key": cancellation_reason_key,
                },
            ),
            "mutate_v2_plan",
        )
        try:
            returned_project_id = UUID(str(payload["project_id"]))
            project_version = int(payload["project_version"])
            plan_version = int(payload["plan_version"])
            replayed = payload["replayed"]
            item_rows = payload["items"]
        except (KeyError, TypeError, ValueError) as exc:
            raise V2RepositoryError("mutate_v2_plan returned a malformed result") from exc
        if (
            returned_project_id != project_id
            or project_version <= 0
            or plan_version <= 0
            or not isinstance(replayed, bool)
            or not isinstance(item_rows, list)
        ):
            raise V2RepositoryError("mutate_v2_plan returned inconsistent identity or shape")
        return V2Plan(
            project_ref=ProjectRef(WorkflowVersion.V2, project_id),
            project_version=project_version,
            plan_version=plan_version,
            items=tuple(
                _plan_item_from_row(
                    row,
                    expected_owner=owner_user_id,
                    expected_project_id=project_id,
                )
                for row in item_rows
            ),
            replayed=replayed,
        )

    async def start_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        expected_project_version: int,
        command_id: UUID,
        plan_item_id: UUID | None,
        change_kind: str,
        goal_snapshot: str,
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(
            await self._rpc(
                "start_v2_current_change",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_expected_project_version": expected_project_version,
                    "p_create_command_id": str(command_id),
                    "p_plan_item_id": str(plan_item_id) if plan_item_id else None,
                    "p_change_kind": change_kind,
                    "p_goal_snapshot": goal_snapshot,
                },
            ),
            "start_v2_current_change",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("Current Change start omitted replay state")
        return (
            _current_change_from_row(
                payload.get("current_change"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            payload["replayed"],
        )

    async def get_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
    ) -> V2CurrentChange | None:
        project = await self.get_project(owner_user_id, project_id)
        if project is None:
            raise V2RepositoryNotFound("owned V2 Project not found")
        rows = await self._request(
            "GET",
            "/v2_current_changes",
            params={
                "select": _CURRENT_CHANGE_SELECT,
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "lifecycle_state": "in.(preparing,awaiting_agent,reviewing,recovering)",
                "limit": "1",
            },
        )
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("current V2 Current Change read returned malformed rows")
        if not rows:
            return None
        return _current_change_from_row(
            rows[0],
            expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def get_current_change_by_id(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
    ) -> V2CurrentChange | None:
        rows = await self._request(
            "GET",
            "/v2_current_changes",
            params={
                "select": _CURRENT_CHANGE_SELECT,
                "id": f"eq.{current_change_id}",
                "project_id": f"eq.{project_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": "1",
            },
        )
        if not isinstance(rows, list) or len(rows) > 1:
            raise V2RepositoryError("explicit V2 Current Change read returned malformed rows")
        if not rows:
            return None
        return _current_change_from_row(
            rows[0],
            expected_owner=owner_user_id,
            expected_project_id=project_id,
        )

    async def cancel_current_change(
        self,
        owner_user_id: str,
        project_id: UUID,
        current_change_id: UUID,
        expected_current_change_version: int,
        cancellation_command_id: UUID,
        cancellation_reason_key: str,
    ) -> tuple[V2CurrentChange, bool]:
        payload = self._object(
            await self._rpc(
                "cancel_v2_current_change",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_project_id": str(project_id),
                    "p_current_change_id": str(current_change_id),
                    "p_expected_current_change_version": expected_current_change_version,
                    "p_cancellation_command_id": str(cancellation_command_id),
                    "p_cancellation_reason_key": cancellation_reason_key,
                },
            ),
            "cancel_v2_current_change",
        )
        if not isinstance(payload.get("replayed"), bool):
            raise V2RepositoryError("Current Change cancellation omitted replay state")
        return (
            _current_change_from_row(
                payload.get("current_change"),
                expected_owner=owner_user_id,
                expected_project_id=project_id,
            ),
            payload["replayed"],
        )


def get_v2_repository() -> V2Repository:
    return SupabaseV2Repository(get_settings())
