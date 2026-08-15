"""In-memory repository fakes and a scripted LLM — business rules are tested
against these; the live Supabase/LLM paths are verified separately."""

import copy
import itertools
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

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
)
from app.services.llm_service import LLMError
from app.services.project_repository import RepositoryError
from app.services.v2_repository import (
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


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

    async def update_task_progress_if_current(
        self,
        user_id: str,
        project_id: str,
        expected: dict,
        replacement: dict,
    ) -> dict | None:
        for row in self._rows:
            if row["id"] == project_id and row["user_id"] == user_id:
                if row.get("task_progress") != expected:
                    return None
                row["task_progress"] = copy.deepcopy(replacement)
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


class InMemoryV2Repository:
    """Behavioral fake for the owner-scoped V2 repository/RPC boundary."""

    def __init__(self) -> None:
        self._projects: dict[uuid.UUID, tuple[str, V2Project]] = {}
        self._project_commands: dict[tuple[str, uuid.UUID], uuid.UUID] = {}
        self._promotion_commands: dict[uuid.UUID, uuid.UUID] = {}
        self._plans: dict[uuid.UUID, dict[uuid.UUID, V2PlanItem]] = {}
        self._last_plan_commands: dict[uuid.UUID, uuid.UUID] = {}
        self._changes: dict[uuid.UUID, tuple[str, V2CurrentChange]] = {}
        self._change_commands: dict[tuple[str, uuid.UUID], uuid.UUID] = {}
        self._recovery_case_statuses: dict[uuid.UUID, list[str]] = {}
        self._tick = itertools.count()

    def _now(self) -> datetime:
        return datetime(2026, 8, 13, tzinfo=UTC) + timedelta(seconds=next(self._tick))

    def _owned_project(self, owner_user_id: str, project_id: uuid.UUID) -> V2Project:
        entry = self._projects.get(project_id)
        if entry is None or entry[0] != owner_user_id:
            raise V2RepositoryNotFound("owned V2 Project not found")
        return entry[1]

    def _store_project(self, owner_user_id: str, project: V2Project) -> None:
        self._projects[project.ref.project_id] = (owner_user_id, project)

    def activate_project_for_test(self, owner_user_id: str, project_id: uuid.UUID) -> None:
        """Test-only seam standing in for the later accepted setup command."""
        project = self._owned_project(owner_user_id, project_id)
        if project.lifecycle_state is not ProjectLifecycle.DRAFT:
            raise V2RepositoryInvalidState("only a draft Project can finish setup")
        self._store_project(
            owner_user_id,
            replace(
                project,
                lifecycle_state=ProjectLifecycle.ACTIVE,
                setup_resume_step=SetupResumeStep.READY,
            ),
        )

    async def create_project(
        self,
        owner_user_id: str,
        command_id: uuid.UUID,
        display_name: str,
        creation_intent: str,
        recovery_context: dict | None,
        current_change_command_id: uuid.UUID | None,
    ) -> tuple[V2Project, bool]:
        key = (owner_user_id, command_id)
        project_id = self._project_commands.get(key)
        if project_id is not None:
            return self._projects[project_id][1], True

        project_id = uuid.uuid4()
        now = self._now()
        if creation_intent not in {"new_idea", "already_building", "recovery_first"}:
            raise V2RepositoryInvalidState("invalid Project creation intent")
        temporary = creation_intent == "recovery_first"
        if temporary:
            required = {
                "project_context",
                "intended_behavior",
                "observed_symptom",
                "last_known_working_certainty",
                "candidate_change_summary",
            }
            if (
                recovery_context is None
                or current_change_command_id is None
                or not required.issubset(recovery_context)
                or (owner_user_id, current_change_command_id) in self._change_commands
            ):
                raise V2RepositoryInvalidState("Recovery-first context is incomplete")
        elif recovery_context is not None or current_change_command_id is not None:
            raise V2RepositoryInvalidState("non-Recovery creation included Recovery context")

        setup_step = {
            "new_idea": SetupResumeStep.IDEA_CAPTURE,
            "already_building": SetupResumeStep.EXISTING_PROJECT_CONTEXT,
            "recovery_first": SetupResumeStep.RECOVERY_CONTEXT,
        }[creation_intent]
        project = V2Project(
            ref=ProjectRef(WorkflowVersion.V2, project_id),
            display_name=display_name,
            lifecycle_state=(
                ProjectLifecycle.TEMPORARY_RECOVERY if temporary else ProjectLifecycle.DRAFT
            ),
            setup_resume_step=setup_step,
            plan_version=1,
            version=1,
            coding_agent_key=None,
            first_version_completed_at=None,
            created_at=now,
            updated_at=now,
        )
        self._store_project(owner_user_id, project)
        self._plans[project_id] = {}
        self._project_commands[key] = project_id
        self._recovery_case_statuses[project_id] = []
        if temporary:
            assert recovery_context is not None
            assert current_change_command_id is not None
            change_id = uuid.uuid4()
            change = V2CurrentChange(
                id=change_id,
                project_ref=project.ref,
                plan_item_id=None,
                change_kind=CurrentChangeKind.RECOVERY,
                lifecycle_state=CurrentChangeState.PREPARING,
                resume_step=ResumeStep.CONFIRM_CHANGE,
                goal_snapshot=recovery_context["intended_behavior"],
                done_condition_snapshot=None,
                boundary_snapshots=(),
                version=1,
                created_at=now,
                updated_at=now,
                completed_at=None,
                cancelled_at=None,
                cancellation_command_id=None,
                cancellation_reason_key=None,
            )
            self._changes[change_id] = (owner_user_id, change)
            self._change_commands[(owner_user_id, current_change_command_id)] = change_id
        return project, False

    async def get_project(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
    ) -> V2Project | None:
        entry = self._projects.get(project_id)
        if entry is None or entry[0] != owner_user_id:
            return None
        if entry[1].lifecycle_state is ProjectLifecycle.DELETION_PENDING:
            return None
        return entry[1]

    async def list_projects(self, owner_user_id: str) -> list[V2Project]:
        projects = [
            project
            for owner, project in self._projects.values()
            if owner == owner_user_id
            and project.lifecycle_state is not ProjectLifecycle.DELETION_PENDING
        ]
        return sorted(projects, key=lambda project: (project.updated_at, project.ref.project_id), reverse=True)

    async def promote_temporary_project(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        expected_project_version: int,
        command_id: uuid.UUID,
    ) -> tuple[V2Project, bool]:
        project = self._owned_project(owner_user_id, project_id)
        if self._promotion_commands.get(project_id) == command_id:
            return project, True
        if project.lifecycle_state is not ProjectLifecycle.TEMPORARY_RECOVERY:
            raise V2RepositoryInvalidState("Project cannot be promoted")
        if project.version != expected_project_version:
            raise V2RepositoryConflict("stale Project")
        recovery_changes = [
            change
            for owner, change in self._changes.values()
            if owner == owner_user_id
            and change.project_ref.project_id == project_id
            and change.change_kind is CurrentChangeKind.RECOVERY
        ]
        recovery_statuses = self._recovery_case_statuses.get(project_id, [])
        if (
            not recovery_changes
            or not recovery_statuses
            or any(change.lifecycle_state is not CurrentChangeState.COMPLETED for change in recovery_changes)
            or any(status != "resolved" for status in recovery_statuses)
        ):
            raise V2RepositoryInvalidState("Project lacks a resolved Recovery flow")
        promoted = replace(
            project,
            lifecycle_state=ProjectLifecycle.ACTIVE,
            setup_resume_step=SetupResumeStep.EXISTING_PROJECT_CONTEXT,
            version=project.version + 1,
            updated_at=self._now(),
        )
        self._store_project(owner_user_id, promoted)
        self._promotion_commands[project_id] = command_id
        return promoted, False

    def set_recovery_flow_for_test(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        *,
        case_statuses: list[str],
        change_state: CurrentChangeState,
    ) -> None:
        """Test-only fixture seam for later-slice Recovery state."""
        self._owned_project(owner_user_id, project_id)
        self._recovery_case_statuses[project_id] = list(case_statuses)
        for change_id, (owner, change) in list(self._changes.items()):
            if (
                owner == owner_user_id
                and change.project_ref.project_id == project_id
                and change.change_kind is CurrentChangeKind.RECOVERY
            ):
                terminal = change_state in {
                    CurrentChangeState.COMPLETED,
                    CurrentChangeState.CANCELLED,
                }
                self._changes[change_id] = (
                    owner,
                    replace(
                        change,
                        lifecycle_state=change_state,
                        resume_step=None if terminal else ResumeStep.RECOVERY_INVESTIGATE,
                        completed_at=(
                            self._now()
                            if change_state is CurrentChangeState.COMPLETED
                            else None
                        ),
                        cancelled_at=(
                            self._now()
                            if change_state is CurrentChangeState.CANCELLED
                            else None
                        ),
                        version=change.version + 1,
                        updated_at=self._now(),
                    ),
                )

    async def purge_temporary_project(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        expected_project_version: int,
    ) -> bool:
        entry = self._projects.get(project_id)
        if entry is None or entry[0] != owner_user_id:
            return True
        project = entry[1]
        if project.version != expected_project_version:
            raise V2RepositoryConflict("stale Project")
        if project.lifecycle_state is not ProjectLifecycle.TEMPORARY_RECOVERY:
            raise V2RepositoryInvalidState("Project is not temporary")
        del self._projects[project_id]
        self._plans.pop(project_id, None)
        self._last_plan_commands.pop(project_id, None)
        self._promotion_commands.pop(project_id, None)
        self._recovery_case_statuses.pop(project_id, None)
        for command_key, command_project_id in list(self._project_commands.items()):
            if command_project_id == project_id:
                del self._project_commands[command_key]
        for change_id, (_, change) in list(self._changes.items()):
            if change.project_ref.project_id == project_id:
                del self._changes[change_id]
                for command_key, command_change_id in list(self._change_commands.items()):
                    if command_change_id == change_id:
                        del self._change_commands[command_key]
        return True

    async def get_plan(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
    ) -> V2Plan | None:
        project = await self.get_project(owner_user_id, project_id)
        if project is None:
            return None
        items = [
            item
            for item in self._plans.get(project_id, {}).values()
            if item.status is not PlanItemStatus.REMOVED
        ]
        items.sort(key=lambda item: (item.scope_band.value, item.order_key, item.id))
        return V2Plan(
            project_ref=project.ref,
            project_version=project.version,
            plan_version=project.plan_version,
            items=tuple(items),
        )

    async def mutate_plan(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        expected_project_version: int,
        expected_plan_version: int,
        command_id: uuid.UUID,
        operations: list[dict],
        expected_current_change_version: int | None,
        linked_item_action: str | None,
        cancellation_command_id: uuid.UUID | None,
        cancellation_reason_key: str | None,
    ) -> V2Plan:
        project = self._owned_project(owner_user_id, project_id)
        if self._last_plan_commands.get(project_id) == command_id:
            current = await self.get_plan(owner_user_id, project_id)
            assert current is not None
            return replace(current, replayed=True)
        if (
            project.version != expected_project_version
            or project.plan_version != expected_plan_version
        ):
            raise V2RepositoryConflict("stale Plan")

        plan = dict(self._plans.get(project_id, {}))
        active = next(
            (
                change
                for owner, change in self._changes.values()
                if owner == owner_user_id
                and change.project_ref.project_id == project_id
                and change.lifecycle_state
                in {
                    CurrentChangeState.PREPARING,
                    CurrentChangeState.AWAITING_AGENT,
                    CurrentChangeState.REVIEWING,
                    CurrentChangeState.RECOVERING,
                }
            ),
            None,
        )
        linked_removal = any(
            operation["action"] == "remove"
            and active is not None
            and active.plan_item_id == uuid.UUID(str(operation["plan_item_id"]))
            for operation in operations
        )
        if linked_removal:
            if (
                linked_item_action not in {"detach", "cancel"}
                or active is None
                or active.version != expected_current_change_version
            ):
                raise V2RepositoryConflict("linked item action required")
            if linked_item_action == "detach":
                if cancellation_command_id is not None or cancellation_reason_key is not None:
                    raise V2RepositoryInvalidState("detach has cancellation fields")
                updated_change = replace(
                    active,
                    plan_item_id=None,
                    version=active.version + 1,
                    updated_at=self._now(),
                )
            else:
                if cancellation_command_id is None or cancellation_reason_key is None:
                    raise V2RepositoryInvalidState("cancel missing identity")
                updated_change = replace(
                    active,
                    lifecycle_state=CurrentChangeState.CANCELLED,
                    resume_step=None,
                    version=active.version + 1,
                    updated_at=self._now(),
                    cancelled_at=self._now(),
                    cancellation_command_id=cancellation_command_id,
                    cancellation_reason_key=cancellation_reason_key,
                )
        elif any(
            value is not None
            for value in (
                linked_item_action,
                expected_current_change_version,
                cancellation_command_id,
                cancellation_reason_key,
            )
        ):
            raise V2RepositoryInvalidState("linked action without linked removal")

        seen: set[uuid.UUID] = set()
        for operation in operations:
            item_id = uuid.UUID(str(operation["plan_item_id"]))
            if item_id in seen:
                raise V2RepositoryInvalidState("duplicate Plan Item operation")
            seen.add(item_id)
            action = operation["action"]
            if action == "add":
                if item_id in plan:
                    raise V2RepositoryConflict("Plan Item exists")
                plan[item_id] = V2PlanItem(
                    id=item_id,
                    project_id=project_id,
                    label=operation["label"],
                    intended_outcome=operation["intended_outcome"],
                    scope_band=PlanScopeBand(operation["scope_band"]),
                    status=PlanItemStatus(operation["status"]),
                    order_key=operation["order_key"],
                    version=1,
                    completed_at=None,
                    terminal_current_change_id=None,
                )
                continue
            item = plan.get(item_id)
            if item is None:
                raise V2RepositoryNotFound("Plan Item not found")
            if item.version != operation["expected_version"]:
                raise V2RepositoryConflict("stale Plan Item")
            if action == "edit":
                item = replace(
                    item,
                    label=operation["label"],
                    intended_outcome=operation["intended_outcome"],
                    status=PlanItemStatus(operation["status"]),
                    version=item.version + 1,
                )
            elif action == "reorder":
                item = replace(
                    item,
                    order_key=operation["order_key"],
                    version=item.version + 1,
                )
            elif action == "move":
                item = replace(
                    item,
                    scope_band=PlanScopeBand(operation["scope_band"]),
                    order_key=operation["order_key"],
                    version=item.version + 1,
                )
            elif action == "remove":
                item = replace(
                    item,
                    status=PlanItemStatus.REMOVED,
                    order_key=-item.version,
                    version=item.version + 1,
                    completed_at=None,
                    terminal_current_change_id=None,
                )
            else:
                raise V2RepositoryInvalidState("unknown Plan action")
            plan[item_id] = item

        visible_order = [
            (item.scope_band, item.order_key)
            for item in plan.values()
            if item.status is not PlanItemStatus.REMOVED
        ]
        if len(visible_order) != len(set(visible_order)):
            raise V2RepositoryConflict("duplicate Plan order")

        updated_project = replace(
            project,
            plan_version=project.plan_version + 1,
            version=project.version + 1,
            updated_at=self._now(),
        )
        self._plans[project_id] = plan
        if linked_removal:
            self._changes[active.id] = (owner_user_id, updated_change)
        self._store_project(owner_user_id, updated_project)
        self._last_plan_commands[project_id] = command_id
        current = await self.get_plan(owner_user_id, project_id)
        assert current is not None
        return current

    async def start_current_change(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        expected_project_version: int,
        command_id: uuid.UUID,
        plan_item_id: uuid.UUID | None,
        change_kind: str,
        goal_snapshot: str,
    ) -> tuple[V2CurrentChange, bool]:
        project = self._owned_project(owner_user_id, project_id)
        command_key = (owner_user_id, command_id)
        existing_id = self._change_commands.get(command_key)
        if existing_id is not None:
            existing = self._changes[existing_id][1]
            if (
                existing.project_ref.project_id != project_id
                or existing.change_kind.value != change_kind
                or existing.goal_snapshot != goal_snapshot
            ):
                raise V2RepositoryConflict("Current Change command reused")
            return existing, True
        if project.version != expected_project_version:
            raise V2RepositoryConflict("stale Project")
        if project.lifecycle_state not in {
            ProjectLifecycle.ACTIVE,
            ProjectLifecycle.TEMPORARY_RECOVERY,
        }:
            raise V2RepositoryInvalidState("Project cannot start work")
        if (
            project.lifecycle_state is ProjectLifecycle.TEMPORARY_RECOVERY
            and change_kind != "recovery"
        ):
            raise V2RepositoryInvalidState("temporary Project requires recovery")
        if plan_item_id is not None:
            item = self._plans.get(project_id, {}).get(plan_item_id)
            if item is None:
                raise V2RepositoryNotFound("Plan Item not found")
            if item.status in {PlanItemStatus.DONE, PlanItemStatus.REMOVED}:
                raise V2RepositoryInvalidState("terminal Plan Item")
        if any(
            owner == owner_user_id
            and change.project_ref.project_id == project_id
            and change.lifecycle_state
            in {
                CurrentChangeState.PREPARING,
                CurrentChangeState.AWAITING_AGENT,
                CurrentChangeState.REVIEWING,
                CurrentChangeState.RECOVERING,
            }
            for owner, change in self._changes.values()
        ):
            raise V2RepositoryConflict("Current Change already exists")
        now = self._now()
        change = V2CurrentChange(
            id=uuid.uuid4(),
            project_ref=project.ref,
            plan_item_id=plan_item_id,
            change_kind=CurrentChangeKind(change_kind),
            lifecycle_state=CurrentChangeState.PREPARING,
            resume_step=ResumeStep.CONFIRM_CHANGE,
            goal_snapshot=goal_snapshot,
            done_condition_snapshot=None,
            boundary_snapshots=(),
            version=1,
            created_at=now,
            updated_at=now,
            completed_at=None,
            cancelled_at=None,
            cancellation_command_id=None,
            cancellation_reason_key=None,
        )
        self._changes[change.id] = (owner_user_id, change)
        self._change_commands[command_key] = change.id
        return change, False

    async def get_current_change(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
    ) -> V2CurrentChange | None:
        self._owned_project(owner_user_id, project_id)
        for owner, change in self._changes.values():
            if (
                owner == owner_user_id
                and change.project_ref.project_id == project_id
                and change.lifecycle_state
                in {
                    CurrentChangeState.PREPARING,
                    CurrentChangeState.AWAITING_AGENT,
                    CurrentChangeState.REVIEWING,
                    CurrentChangeState.RECOVERING,
                }
            ):
                return change
        return None

    async def get_current_change_by_id(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        current_change_id: uuid.UUID,
    ) -> V2CurrentChange | None:
        entry = self._changes.get(current_change_id)
        if (
            entry is None
            or entry[0] != owner_user_id
            or entry[1].project_ref.project_id != project_id
        ):
            return None
        return entry[1]

    async def cancel_current_change(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        current_change_id: uuid.UUID,
        expected_current_change_version: int,
        cancellation_command_id: uuid.UUID,
        cancellation_reason_key: str,
    ) -> tuple[V2CurrentChange, bool]:
        self._owned_project(owner_user_id, project_id)
        change = await self.get_current_change_by_id(
            owner_user_id,
            project_id,
            current_change_id,
        )
        if change is None:
            raise V2RepositoryNotFound("Current Change not found")
        if (
            change.lifecycle_state is CurrentChangeState.CANCELLED
            and change.cancellation_command_id == cancellation_command_id
        ):
            return change, True
        if change.lifecycle_state in {
            CurrentChangeState.COMPLETED,
            CurrentChangeState.CANCELLED,
        }:
            raise V2RepositoryInvalidState("terminal Current Change")
        if change.version != expected_current_change_version:
            raise V2RepositoryConflict("stale Current Change")
        now = self._now()
        cancelled = replace(
            change,
            lifecycle_state=CurrentChangeState.CANCELLED,
            resume_step=None,
            version=change.version + 1,
            updated_at=now,
            cancelled_at=now,
            cancellation_command_id=cancellation_command_id,
            cancellation_reason_key=cancellation_reason_key,
        )
        self._changes[current_change_id] = (owner_user_id, cancelled)
        return cancelled, False


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
