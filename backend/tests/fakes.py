"""In-memory repository fakes and a scripted LLM — business rules are tested
against these; the live Supabase/LLM paths are verified separately."""

import copy
import hashlib
import itertools
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.domain.v2 import (
    CheckResult,
    CodingAgentKey,
    CurrentChangeKind,
    CurrentChangeState,
    EffortCategory,
    GenerationPurpose,
    GenerationStatus,
    PlanItemStatus,
    PlanScopeBand,
    ProjectLifecycle,
    ProjectRef,
    PromptPurpose,
    RecoveryStatus,
    RiskMode,
    ResumeStep,
    SetupResumeStep,
    SupportLevel,
    TeachingMode,
    V2CurrentChange,
    V2Check,
    V2GenerationAttempt,
    V2LearnerEvidence,
    V2Plan,
    V2PlanItem,
    V2Project,
    V2RecentChange,
    V2PromptVersion,
    V2RecoveryCase,
    V2TeachingProgress,
    V2UserPreferences,
    WorkflowVersion,
)
from app.services.llm_service import LLMError
from app.services.project_repository import RepositoryError
from app.services.v2_repository import (
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)
from app.services.v2_teaching_policy import (
    RISK_POLICY_VERSION,
    qualifies_check_plan,
    qualifies_structured_response,
    risk_input_fingerprint as compute_risk_input_fingerprint,
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
        self._prompt_versions: dict[uuid.UUID, tuple[str, V2PromptVersion]] = {}
        self._acceptance_commands: dict[tuple[str, uuid.UUID], uuid.UUID] = {}
        self._handoff_commands: dict[tuple[str, uuid.UUID], uuid.UUID] = {}
        self._generation_attempts: dict[uuid.UUID, tuple[str, V2GenerationAttempt]] = {}
        self._generation_commands: dict[tuple[str, uuid.UUID], uuid.UUID] = {}
        self._recovery_case_statuses: dict[uuid.UUID, list[str]] = {}
        self._recovery_cases: dict[uuid.UUID, tuple[str, V2RecoveryCase]] = {}
        self._recovery_commands: dict[uuid.UUID, tuple[str, uuid.UUID]] = {}
        self._checks: dict[uuid.UUID, tuple[str, V2Check]] = {}
        self._manual_commands: dict[uuid.UUID, tuple[str, uuid.UUID]] = {}
        self._effort_command_results: dict[uuid.UUID, tuple[uuid.UUID, str, bool, dict]] = {}
        self._check_plan_command_payloads: dict[
            uuid.UUID, tuple[uuid.UUID, uuid.UUID, str, str, str]
        ] = {}
        self._teaching_response_qualifications: dict[
            uuid.UUID, tuple[str, str, SupportLevel]
        ] = {}
        self._manual_setup_payloads: dict[
            uuid.UUID, tuple[str, str, str, uuid.UUID]
        ] = {}
        self._preferences: dict[str, V2UserPreferences] = {}
        self._learner_evidence: dict[uuid.UUID, tuple[str, V2LearnerEvidence]] = {}
        self._teaching_progress: dict[uuid.UUID, V2TeachingProgress] = {}
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

    async def establish_manual_project(
        self, owner_user_id: str, project_id: uuid.UUID, expected_project_version: int,
        command_id: uuid.UUID, project_context: str, plan_item_id: uuid.UUID,
        change_label: str, done_condition: str,
    ) -> tuple[V2Project, V2PlanItem, bool]:
        project = self._owned_project(owner_user_id, project_id)
        existing = self._manual_commands.get(command_id)
        if existing:
            prior_setup = self._manual_setup_payloads.get(project_id)
            if (
                existing != ("setup", plan_item_id)
                or prior_setup is None
                or prior_setup != (
                    project_context.strip(), change_label.strip(), done_condition.strip(), plan_item_id
                )
            ):
                raise V2RepositoryConflict("manual setup command reused")
            return project, self._plans[project_id][plan_item_id], True
        prior_setup = self._manual_setup_payloads.get(project_id)
        if (
            project.lifecycle_state is ProjectLifecycle.ACTIVE
            and project.setup_resume_step is SetupResumeStep.READY
            and project.version == 2
            and project.plan_version == 2
            and prior_setup is not None
            and prior_setup[:3] == (
                project_context.strip(), change_label.strip(), done_condition.strip()
            )
            and len(self._plans.get(project_id, {})) == 1
        ):
            return project, self._plans[project_id][prior_setup[3]], True
        if project.version != expected_project_version or project.lifecycle_state is not ProjectLifecycle.DRAFT:
            raise V2RepositoryConflict("stale setup")
        if self._plans.get(project_id):
            raise V2RepositoryInvalidState("setup requires empty plan")
        item = V2PlanItem(
            id=plan_item_id, project_id=project_id, label=change_label,
            intended_outcome=done_condition, scope_band=PlanScopeBand.FIRST_VERSION,
            status=PlanItemStatus.READY, order_key=1024, version=1,
            completed_at=None, terminal_current_change_id=None,
        )
        project = replace(project, lifecycle_state=ProjectLifecycle.ACTIVE,
            setup_resume_step=SetupResumeStep.READY, plan_version=project.plan_version + 1,
            version=project.version + 1, updated_at=self._now())
        self._plans[project_id] = {plan_item_id: item}
        self._store_project(owner_user_id, project)
        self._manual_commands[command_id] = ("setup", plan_item_id)
        self._manual_setup_payloads[project_id] = (
            project_context.strip(), change_label.strip(), done_condition.strip(), plan_item_id
        )
        return project, item, False

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

    def resolve_policy_for_test(
        self, owner_user_id: str, project_id: uuid.UUID, current_change_id: uuid.UUID
    ) -> V2CurrentChange:
        """Test seam for the accepted policy resolver that V2.3B consumes."""
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        resolved = replace(
            change,
            teaching_policy_version="test-teaching-v1",
            risk_policy_version=RISK_POLICY_VERSION,
            risk_input_fingerprint=compute_risk_input_fingerprint(
                change.goal_snapshot,
                change.done_condition_snapshot,
                change.boundary_snapshots,
                change.prompt_draft,
            ),
            resume_step=ResumeStep.CHOOSE_AGENT,
            version=change.version + 1,
            updated_at=self._now(),
        )
        self._changes[current_change_id] = (owner_user_id, resolved)
        return resolved

    async def list_learner_evidence(
        self, owner_user_id: str, competency_keys: list[str] | None = None,
    ) -> list[V2LearnerEvidence]:
        return [
            item for owner, item in self._learner_evidence.values()
            if owner == owner_user_id
            and (not competency_keys or item.competency_key in competency_keys)
        ]

    def seed_learner_evidence(
        self, owner_user_id: str, competency_key: str, *, elicitation: str = "asked",
        support_level: SupportLevel = SupportLevel.NONE,
        current_change_id: uuid.UUID | None = None,
        observed_at: datetime | None = None,
    ) -> V2LearnerEvidence:
        item = V2LearnerEvidence(
            id=uuid.uuid4(), competency_key=competency_key,
            observed_behavior="Observed test behavior.", elicitation=elicitation,
            support_level=support_level, context_key="build",
            source_current_change_id=current_change_id,
            observed_at=observed_at or self._now(), status="active",
        )
        self._learner_evidence[item.id] = (owner_user_id, item)
        return item

    async def resolve_teaching_policy(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, expected_current_change_version: int,
        command_id: uuid.UUID, decision: dict,
    ) -> tuple[V2CurrentChange, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        existing = self._manual_commands.get(command_id)
        if existing:
            if existing != ("policy", current_change_id):
                raise V2RepositoryConflict("policy command reused")
            return change, True
        if change.version != expected_current_change_version or change.resume_step is not ResumeStep.CONFIRM_CHANGE:
            raise V2RepositoryConflict("stale policy")
        mode = TeachingMode(decision["mode"])
        target = decision.get("target")
        done = change.done_condition_snapshot
        if change.plan_item_id and not (target == "define_done" and mode is not TeachingMode.SKIP):
            done = self._plans[project_id][change.plan_item_id].intended_outcome
        change = replace(
            change, teaching_mode=mode, teaching_target=target,
            teaching_policy_version=decision["teaching_policy_version"],
            risk=RiskMode(decision["risk"]), risk_reason_key=decision.get("risk_reason_key"),
            risk_policy_version=decision["risk_policy_version"],
            risk_input_fingerprint=decision["risk_input_fingerprint"],
            check_requirement=decision["check_requirement"],
            done_condition_snapshot=done,
            help_context_key=None if mode is TeachingMode.SKIP else target,
            support_level_disclosed=SupportLevel.NONE,
            resume_step=(ResumeStep.CHOOSE_AGENT if mode is TeachingMode.SKIP else ResumeStep.INTERVENTION),
            version=change.version + 1, updated_at=self._now(),
        )
        self._changes[current_change_id] = (owner_user_id, change)
        self._manual_commands[command_id] = ("policy", current_change_id)
        self._teaching_progress.setdefault(current_change_id, V2TeachingProgress())
        return change, False

    async def get_teaching_progress(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID,
    ) -> V2TeachingProgress:
        self._owned_change(owner_user_id, project_id, current_change_id)
        return self._teaching_progress.get(current_change_id, V2TeachingProgress())

    async def disclose_teaching_help(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, expected_current_change_version: int,
        command_id: uuid.UUID, context: str,
    ) -> tuple[V2CurrentChange, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        if self._manual_commands.get(command_id):
            return change, True
        if change.version != expected_current_change_version:
            raise V2RepositoryConflict("stale help")
        target = change.teaching_target if context == "prebuild" else (
            "testing" if context in {"verification", "recovery_recheck"}
            else "debugging" if context.startswith("recovery_")
            else "causal_explanation")
        current = (
            change.support_level_disclosed
            if change.help_context_key == target
            else SupportLevel.NONE
        )
        if current is SupportLevel.TEACH:
            raise V2RepositoryInvalidState("final help is already disclosed")
        support = {SupportLevel.NONE: SupportLevel.NUDGE, SupportLevel.NUDGE: SupportLevel.CLUE,
                   SupportLevel.CLUE: SupportLevel.TEACH, SupportLevel.TEACH: SupportLevel.TEACH}[current]
        change = replace(change, help_context_key=target, support_level_disclosed=support,
                         version=change.version + 1, updated_at=self._now())
        self._changes[current_change_id] = (owner_user_id, change)
        progress = self._teaching_progress.get(current_change_id, V2TeachingProgress())
        self._teaching_progress[current_change_id] = replace(progress, hint_level=support)
        self.seed_learner_evidence(owner_user_id, target or "define_done",
            elicitation="after_hint", support_level=support,
            current_change_id=current_change_id)
        self._manual_commands[command_id] = ("help", current_change_id)
        return change, False

    async def record_teaching_response(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, expected_current_change_version: int,
        command_id: uuid.UUID, context: str, response: str,
        elicitation: str, support_level: str,
    ) -> tuple[V2CurrentChange, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        if self._manual_commands.get(command_id):
            return change, True
        if change.version != expected_current_change_version or not response.strip():
            raise V2RepositoryConflict("stale response")
        target = change.teaching_target if context == "prebuild" else "causal_explanation"
        active_support = (
            change.support_level_disclosed
            if change.help_context_key == target
            else SupportLevel.NONE
        )
        if SupportLevel(support_level) is not active_support and elicitation == "after_hint":
            raise V2RepositoryInvalidState("response support belongs to another interaction")
        kwargs = {}
        if context == "prebuild" and target == "define_done":
            kwargs["done_condition_snapshot"] = response.strip()
        if context == "prebuild" and target in {"protect_working_behavior", "data_ownership"}:
            kwargs["boundary_snapshots"] = (response.strip(),)
        change = replace(change, **kwargs,
            resume_step=ResumeStep.CHOOSE_AGENT if context == "prebuild" else ResumeStep.UNDERSTAND,
            help_context_key=None if context == "prebuild" else "understanding_complete",
            support_level_disclosed=SupportLevel.NONE,
            version=change.version + 1, updated_at=self._now())
        self._changes[current_change_id] = (owner_user_id, change)
        progress = self._teaching_progress.get(current_change_id, V2TeachingProgress())
        self._teaching_progress[current_change_id] = replace(progress,
            intervention_answered=progress.intervention_answered or context == "prebuild",
            understanding_answered=progress.understanding_answered or context == "understanding")
        if (not (context == "prebuild" and change.teaching_mode is TeachingMode.REMIND
                and response == "continue")
                and context == "prebuild"
                and qualifies_structured_response(target or "", response)):
            self.seed_learner_evidence(owner_user_id, target or "define_done",
                elicitation=elicitation, support_level=SupportLevel(support_level),
                current_change_id=current_change_id)
        self._manual_commands[command_id] = ("teaching", current_change_id)
        self._teaching_response_qualifications[command_id] = (
            context, elicitation, SupportLevel(support_level)
        )
        return change, False

    async def record_effort_attempt(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, expected_current_change_version: int,
        command_id: uuid.UUID, selected: str, recommended: str, appropriate: bool,
    ) -> tuple[V2CurrentChange, dict, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        if self._manual_commands.get(command_id):
            stored = self._effort_command_results.get(command_id)
            if (stored is None or stored[0] != current_change_id
                    or stored[1] != selected or stored[2] is not appropriate):
                raise V2RepositoryConflict("effort command reused")
            return change, stored[3], True
        if change.version != expected_current_change_version or change.resume_step is not ResumeStep.EFFORT:
            raise V2RepositoryConflict("stale effort")
        progress = self._teaching_progress.get(current_change_id, V2TeachingProgress())
        second = len(progress.effort_attempts) >= 1
        retry = not appropriate and not second
        revealed = not appropriate and second
        final_effort = EffortCategory(selected if appropriate else recommended) if (appropriate or revealed) else None
        message = (f"{selected.title()} fits the size and consequence of this change."
                   if appropriate else "Look at the connected pieces and risk, then try once more."
                   if retry else f"{recommended.title()} is the recommended level for this change.")
        support = (
            SupportLevel.NONE if appropriate and not second
            else SupportLevel.NUDGE if appropriate or retry
            else SupportLevel.TEACH
        )
        elicitation = (
            "asked" if appropriate and not second
            else "after_hint" if appropriate or retry
            else "taught"
        )
        change = replace(change, effort_category=final_effort,
            resume_step=ResumeStep.PROMPT if final_effort else ResumeStep.EFFORT,
            help_context_key="effort_selection",
            support_level_disclosed=support,
            version=change.version + 1, updated_at=self._now())
        self._changes[current_change_id] = (owner_user_id, change)
        self._teaching_progress[current_change_id] = replace(progress,
            effort_attempts=(*progress.effort_attempts, selected), effort_feedback=message)
        self.seed_learner_evidence(owner_user_id, "effort_selection",
            elicitation=elicitation, support_level=support,
            current_change_id=current_change_id)
        self._manual_commands[command_id] = ("effort", current_change_id)
        feedback = {"selected": selected,
            "recommended": recommended if (appropriate or revealed) else None,
            "appropriate": appropriate, "retry_allowed": retry,
            "revealed": revealed, "message": message}
        self._effort_command_results[command_id] = (
            current_change_id, selected, appropriate, feedback
        )
        return change, feedback, False

    async def get_student_check_plan_replay(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, command_id: uuid.UUID,
        check_id: uuid.UUID, check_plan: str,
    ) -> tuple[V2CurrentChange, V2Check] | None:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        existing = self._manual_commands.get(command_id)
        if existing is None:
            return None
        stored = self._check_plan_command_payloads.get(command_id)
        if (
            existing != ("check_plan", check_id)
            or stored is None
            or stored[0] != current_change_id
            or stored[1] != check_id
            or stored[2] != check_plan.strip()
        ):
            raise V2RepositoryConflict("student Check command id already used")
        check_entry = self._checks.get(check_id)
        if check_entry is None or check_entry[0] != owner_user_id:
            raise V2RepositoryInvalidState("student Check replay source is missing")
        return change, check_entry[1]

    async def create_student_check_plan(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, expected_current_change_version: int,
        command_id: uuid.UUID, check_id: uuid.UUID, check_plan: str,
        elicitation: str, support_level: str,
    ) -> tuple[V2CurrentChange, V2Check, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        existing = self._manual_commands.get(command_id)
        if existing:
            stored = self._check_plan_command_payloads.get(command_id)
            if (
                existing != ("check_plan", check_id)
                or stored is None
                or stored != (
                    current_change_id, check_id, check_plan.strip(), elicitation, support_level
                )
            ):
                raise V2RepositoryConflict("student Check replay classification changed")
            return change, self._checks[check_id][1], True
        if change.version != expected_current_change_version or change.resume_step is not ResumeStep.CHECK:
            raise V2RepositoryConflict("stale Check plan")
        if (elicitation == "after_hint"
                and (change.help_context_key != "testing"
                     or change.support_level_disclosed.value != support_level)):
            raise V2RepositoryInvalidState("Check support belongs to another interaction")
        check = V2Check(id=check_id, project_id=project_id,
            current_change_id=current_change_id, check_plan=check_plan.strip(),
            plan_source="student", status="proposed", result=None,
            student_observation=None, performed_at=None, version=1)
        self._checks[check_id] = (owner_user_id, check)
        change = replace(change, help_context_key="testing_complete",
            support_level_disclosed=SupportLevel.NONE, version=change.version + 1,
            updated_at=self._now())
        self._changes[current_change_id] = (owner_user_id, change)
        progress = self._teaching_progress.get(current_change_id, V2TeachingProgress())
        self._teaching_progress[current_change_id] = replace(progress, check_plan_answered=True)
        if qualifies_check_plan(check_plan):
            self.seed_learner_evidence(owner_user_id, "testing", elicitation=elicitation,
                support_level=SupportLevel(support_level), current_change_id=current_change_id)
        self._manual_commands[command_id] = ("check_plan", check_id)
        self._check_plan_command_payloads[command_id] = (
            current_change_id, check_id, check_plan.strip(), elicitation, support_level
        )
        return change, check, False

    def _owned_change(
        self, owner_user_id: str, project_id: uuid.UUID, current_change_id: uuid.UUID
    ) -> V2CurrentChange:
        self._owned_project(owner_user_id, project_id)
        entry = self._changes.get(current_change_id)
        if (
            entry is None
            or entry[0] != owner_user_id
            or entry[1].project_ref.project_id != project_id
        ):
            raise V2RepositoryNotFound("Current Change not found")
        return entry[1]

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

    async def list_recent_changes(self, owner_user_id: str,
                                  project_id: uuid.UUID) -> list[V2RecentChange]:
        self._owned_project(owner_user_id, project_id)
        recent: list[V2RecentChange] = []
        changes = sorted((change for owner, change in self._changes.values()
            if owner == owner_user_id and change.project_ref.project_id == project_id
            and change.lifecycle_state is CurrentChangeState.COMPLETED),
            key=lambda value: value.completed_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        for change in changes[:3]:
            checks = [check for owner, check in self._checks.values()
                      if owner == owner_user_id and check.current_change_id == change.id
                      and check.status == "performed" and check.student_observation]
            if checks and change.completed_at:
                check = checks[-1]
                recent.append(V2RecentChange(change.id, change.goal_snapshot,
                    change.completed_at, check.check_plan, check.student_observation or ""))
        return recent

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

    async def update_coding_agent(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        current_change_id: uuid.UUID,
        expected_project_version: int,
        expected_current_change_version: int,
        coding_agent_key: str,
    ) -> tuple[V2Project, V2CurrentChange]:
        project = self._owned_project(owner_user_id, project_id)
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        try:
            agent = CodingAgentKey(coding_agent_key)
        except ValueError as exc:
            raise V2RepositoryInvalidState("unsupported coding agent") from exc
        if not change.policy_is_resolved:
            raise V2RepositoryInvalidState("policy is unresolved")
        if (change.lifecycle_state is not CurrentChangeState.PREPARING
                or change.resume_step not in {
                    ResumeStep.CHOOSE_AGENT, ResumeStep.PROMPT, ResumeStep.EFFORT
                }
                or change.handoff_command_id):
            raise V2RepositoryInvalidState("agent cannot change after handoff")
        if (
            project.version != expected_project_version
            or change.version != expected_current_change_version
        ):
            raise V2RepositoryConflict("stale Build state")
        if project.coding_agent_key != agent.value:
            project = replace(
                project,
                coding_agent_key=agent.value,
                version=project.version + 1,
                updated_at=self._now(),
            )
            self._store_project(owner_user_id, project)
        if change.coding_agent_key != agent:
            change = replace(
                change,
                coding_agent_key=agent,
                resume_step=ResumeStep.PROMPT,
                version=change.version + 1,
                updated_at=self._now(),
            )
            self._changes[current_change_id] = (owner_user_id, change)
        return project, change

    async def update_prompt_draft(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        current_change_id: uuid.UUID,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        prompt_text: str,
        done_condition: str | None,
        boundaries: list[str],
        risk: str,
        risk_reason_key: str | None,
        risk_policy_version: str,
        risk_input_fingerprint: str,
    ) -> V2CurrentChange:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        if not change.policy_is_resolved:
            raise V2RepositoryInvalidState("policy is unresolved")
        if (
            change.lifecycle_state is not CurrentChangeState.PREPARING
            or change.handoff_command_id
            or change.coding_agent_key is None
        ):
            raise V2RepositoryInvalidState("prompt cannot be edited")
        if (
            change.version != expected_current_change_version
            or change.prompt_draft_version != expected_prompt_draft_version
        ):
            raise V2RepositoryConflict("stale prompt draft")
        values_changed = (
            change.prompt_draft != prompt_text
            or change.done_condition_snapshot != done_condition
            or change.boundary_snapshots != tuple(boundaries)
        )
        expected_fingerprint = compute_risk_input_fingerprint(
            change.goal_snapshot, done_condition, boundaries, prompt_text
        )
        if risk_input_fingerprint != expected_fingerprint:
            raise V2RepositoryInvalidState("risk input fingerprint mismatch")
        if values_changed:
            text_changed = change.prompt_draft != prompt_text
            risk_changed = (
                change.risk.value != risk or change.risk_reason_key != risk_reason_key
            )
            change = replace(
                change,
                prompt_draft=prompt_text,
                prompt_draft_version=change.prompt_draft_version + (1 if text_changed else 0),
                done_condition_snapshot=done_condition,
                boundary_snapshots=tuple(boundaries),
                risk=RiskMode(risk),
                risk_reason_key=risk_reason_key,
                risk_policy_version=risk_policy_version,
                risk_input_fingerprint=risk_input_fingerprint,
                effort_category=None if risk_changed else change.effort_category,
                resume_step=(ResumeStep.EFFORT if risk_changed or change.effort_category is None
                             else ResumeStep.PROMPT),
                version=change.version + 1,
                updated_at=self._now(),
            )
            self._changes[current_change_id] = (owner_user_id, change)
        return change

    async def update_effort(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        current_change_id: uuid.UUID,
        expected_current_change_version: int,
        effort_category: str,
    ) -> V2CurrentChange:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        try:
            effort = EffortCategory(effort_category)
        except ValueError as exc:
            raise V2RepositoryInvalidState("unsupported effort") from exc
        if change.teaching_policy_version.startswith("phase5-"):
            raise V2RepositoryInvalidState("legacy effort mutation is disabled")
        if not change.policy_is_resolved:
            raise V2RepositoryInvalidState("policy is unresolved")
        if (
            change.lifecycle_state is not CurrentChangeState.PREPARING
            or change.handoff_command_id
            or change.coding_agent_key is None
            or change.prompt_draft is None
        ):
            raise V2RepositoryInvalidState("effort cannot be selected")
        if change.version != expected_current_change_version:
            raise V2RepositoryConflict("stale Build state")
        if change.effort_category != effort:
            change = replace(
                change,
                effort_category=effort,
                resume_step=ResumeStep.EFFORT,
                version=change.version + 1,
                updated_at=self._now(),
            )
            self._changes[current_change_id] = (owner_user_id, change)
        return change

    async def list_prompt_versions(
        self, owner_user_id: str, project_id: uuid.UUID, current_change_id: uuid.UUID
    ) -> list[V2PromptVersion]:
        self._owned_change(owner_user_id, project_id, current_change_id)
        return sorted(
            (
                prompt
                for owner, prompt in self._prompt_versions.values()
                if owner == owner_user_id
                and prompt.project_ref.project_id == project_id
                and prompt.current_change_id == current_change_id
            ),
            key=lambda prompt: (prompt.ordinal, prompt.id),
        )

    async def accept_prompt_version(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        current_change_id: uuid.UUID,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        acceptance_command_id: uuid.UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        command_key = (owner_user_id, acceptance_command_id)
        existing_id = self._acceptance_commands.get(command_key)
        if existing_id is not None:
            prompt = self._prompt_versions[existing_id][1]
            if prompt.current_change_id != current_change_id:
                raise V2RepositoryConflict("acceptance command reused")
            return change, prompt, True
        if (
            not change.policy_is_resolved
            or change.risk_input_fingerprint != compute_risk_input_fingerprint(
                change.goal_snapshot,
                change.done_condition_snapshot,
                change.boundary_snapshots,
                change.prompt_draft,
            )
            or change.lifecycle_state is not CurrentChangeState.PREPARING
            or change.handoff_command_id
            or change.prompt_draft is None
            or change.coding_agent_key is None
            or change.effort_category is None
        ):
            raise V2RepositoryInvalidState("prompt is not ready")
        if (
            change.version != expected_current_change_version
            or change.prompt_draft_version != expected_prompt_draft_version
        ):
            raise V2RepositoryConflict("stale prompt")
        prompt_id = uuid.uuid4()
        now = self._now()
        prior = await self.list_prompt_versions(owner_user_id, project_id, current_change_id)
        prompt = V2PromptVersion(
            id=prompt_id,
            project_ref=change.project_ref,
            current_change_id=current_change_id,
            ordinal=len(prior) + 1,
            purpose=PromptPurpose.FEATURE,
            content=change.prompt_draft,
            content_sha256=hashlib.sha256(change.prompt_draft.encode()).hexdigest(),
            input_current_change_version=change.version,
            input_goal_snapshot=change.goal_snapshot,
            input_done_condition_snapshot=change.done_condition_snapshot,
            input_boundary_snapshots=change.boundary_snapshots,
            generation_attempt_id=None,
            coding_agent_key=change.coding_agent_key,
            effort_category=change.effort_category,
            provider_mapping_key=None,
            provider_mapping_version=None,
            accepted_at=now,
            handed_off_at=None,
            version=1,
        )
        change = replace(
            change,
            latest_prompt_version_id=prompt_id,
            resume_step=ResumeStep.PROMPT,
            version=change.version + 1,
            updated_at=now,
        )
        self._prompt_versions[prompt_id] = (owner_user_id, prompt)
        self._acceptance_commands[command_key] = prompt_id
        self._changes[current_change_id] = (owner_user_id, change)
        return change, prompt, False

    async def handoff_prompt_version(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        current_change_id: uuid.UUID,
        prompt_version_id: uuid.UUID,
        expected_current_change_version: int,
        expected_prompt_version: int,
        handoff_command_id: uuid.UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        if (not change.policy_is_resolved
                or change.risk_input_fingerprint != compute_risk_input_fingerprint(
                    change.goal_snapshot,
                    change.done_condition_snapshot,
                    change.boundary_snapshots,
                    change.prompt_draft,
                )):
            raise V2RepositoryInvalidState("policy is unresolved")
        command_key = (owner_user_id, handoff_command_id)
        existing_id = self._handoff_commands.get(command_key)
        if existing_id is not None:
            if existing_id != prompt_version_id:
                raise V2RepositoryConflict("handoff command reused")
            return change, self._prompt_versions[existing_id][1], True
        entry = self._prompt_versions.get(prompt_version_id)
        if entry is None or entry[0] != owner_user_id:
            raise V2RepositoryNotFound("Prompt Version not found")
        prompt = entry[1]
        if (
            prompt.project_ref.project_id != project_id
            or prompt.current_change_id != current_change_id
        ):
            raise V2RepositoryNotFound("Prompt Version not found")
        if (
            change.lifecycle_state is not CurrentChangeState.PREPARING
            or change.latest_prompt_version_id != prompt.id
            or change.version != expected_current_change_version
            or prompt.version != expected_prompt_version
            or prompt.handed_off_at is not None
            or prompt.content != change.prompt_draft
            or prompt.coding_agent_key != change.coding_agent_key
            or prompt.effort_category != change.effort_category
            or prompt.input_goal_snapshot != change.goal_snapshot
            or prompt.input_done_condition_snapshot != change.done_condition_snapshot
            or prompt.input_boundary_snapshots != change.boundary_snapshots
        ):
            raise V2RepositoryConflict("prompt is stale or already handed off")
        now = self._now()
        prompt = replace(prompt, handed_off_at=now, version=prompt.version + 1)
        change = replace(
            change,
            lifecycle_state=CurrentChangeState.AWAITING_AGENT,
            resume_step=ResumeStep.RETURN_OUTCOME,
            handoff_command_id=handoff_command_id,
            version=change.version + 1,
            updated_at=now,
        )
        self._prompt_versions[prompt.id] = (owner_user_id, prompt)
        self._changes[current_change_id] = (owner_user_id, change)
        self._handoff_commands[command_key] = prompt.id
        return change, prompt, False

    async def confirm_manual_current_change(
        self, owner_user_id: str, project_id: uuid.UUID, current_change_id: uuid.UUID,
        expected_current_change_version: int, command_id: uuid.UUID,
    ) -> tuple[V2CurrentChange, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        existing = self._manual_commands.get(command_id)
        if existing:
            if existing != ("confirm", current_change_id):
                raise V2RepositoryConflict("manual confirmation command reused")
            return change, True
        if change.version != expected_current_change_version or change.resume_step is not ResumeStep.CONFIRM_CHANGE:
            raise V2RepositoryConflict("stale confirmation")
        if change.plan_item_id is None:
            raise V2RepositoryInvalidState("manual change must be linked")
        item = self._plans[project_id][change.plan_item_id]
        change = replace(change, done_condition_snapshot=item.intended_outcome,
            teaching_policy_version="phase4-mechanical-v1",
            risk_policy_version="phase4-mechanical-v1", resume_step=ResumeStep.CHOOSE_AGENT,
            version=change.version + 1, updated_at=self._now())
        self._changes[current_change_id] = (owner_user_id, change)
        self._manual_commands[command_id] = ("confirm", current_change_id)
        return change, False

    async def record_manual_return(
        self, owner_user_id: str, project_id: uuid.UUID, current_change_id: uuid.UUID,
        expected_current_change_version: int, command_id: uuid.UUID,
        outcome: str, check_id: uuid.UUID | None,
    ) -> tuple[V2CurrentChange, V2Check | None, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        existing = self._manual_commands.get(command_id)
        if existing:
            stored = self._checks.get(check_id) if check_id else None
            return change, stored[1] if stored else None, True
        if change.version != expected_current_change_version or change.lifecycle_state is not CurrentChangeState.AWAITING_AGENT:
            raise V2RepositoryConflict("stale return")
        check = None
        if outcome in {"worked", "unsure"}:
            if check_id is not None:
                if not change.done_condition_snapshot:
                    raise V2RepositoryInvalidState("return requires a done condition")
                check = V2Check(id=check_id, project_id=project_id,
                    current_change_id=current_change_id, check_plan=change.done_condition_snapshot,
                    plan_source="codize",
                    status="proposed", result=None, student_observation=None,
                    performed_at=None, version=1)
                self._checks[check_id] = (owner_user_id, check)
            change = replace(change, lifecycle_state=CurrentChangeState.REVIEWING,
                resume_step=ResumeStep.CHECK, student_return_outcome=outcome,
                help_context_key="testing",
                support_level_disclosed=(SupportLevel.TEACH if check_id else SupportLevel.NONE),
                unresolved_uncertainty_summary=("The student was unsure before checking." if outcome == "unsure" else None),
                version=change.version + 1, updated_at=self._now())
        else:
            change = replace(change, lifecycle_state=CurrentChangeState.RECOVERING,
                resume_step=ResumeStep.RECOVERY_SYMPTOM, student_return_outcome="broken",
                version=change.version + 1, updated_at=self._now())
        self._changes[current_change_id] = (owner_user_id, change)
        self._manual_commands[command_id] = ("return", current_change_id)
        return change, check, False

    async def record_manual_check(
        self, owner_user_id: str, project_id: uuid.UUID, current_change_id: uuid.UUID,
        check_id: uuid.UUID, expected_current_change_version: int,
        expected_check_version: int, command_id: uuid.UUID, result: str,
        observation: str, performed_by_student: bool, next_check_id: uuid.UUID | None,
    ) -> tuple[V2CurrentChange, V2Check, V2Check | None, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        entry = self._checks.get(check_id)
        if entry is None or entry[0] != owner_user_id:
            raise V2RepositoryNotFound("Check not found")
        check = entry[1]
        if self._manual_commands.get(command_id):
            next_entry = self._checks.get(next_check_id) if next_check_id else None
            return change, check, next_entry[1] if next_entry else None, True
        if not performed_by_student or not observation.strip():
            raise V2RepositoryInvalidState("student performed check required")
        if change.version != expected_current_change_version or check.version != expected_check_version or check.status != "proposed":
            raise V2RepositoryConflict("stale check")
        parsed = CheckResult(result)
        check = replace(check, status="performed", result=parsed,
            student_observation=observation.strip(), performed_at=self._now(),
            version=check.version + 1)
        self._checks[check_id] = (owner_user_id, check)
        next_check = None
        if parsed is CheckResult.UNSURE:
            if next_check_id is None:
                raise V2RepositoryInvalidState("unsure requires successor")
            next_check = V2Check(id=next_check_id, project_id=project_id,
                current_change_id=current_change_id, check_plan=check.check_plan,
                plan_source=check.plan_source,
                status="proposed", result=None, student_observation=None,
                performed_at=None, version=1)
            self._checks[next_check_id] = (owner_user_id, next_check)
        recovery = parsed in {CheckResult.DID_NOT_WORK, CheckResult.PARTLY_WORKED}
        change = replace(change,
            lifecycle_state=CurrentChangeState.RECOVERING if recovery else CurrentChangeState.REVIEWING,
            resume_step=(ResumeStep.RECOVERY_SYMPTOM if recovery else
                         ResumeStep.UNDERSTAND if parsed is CheckResult.WORKED else ResumeStep.CHECK),
            unresolved_uncertainty_summary=(
                f"Student remains unsure after check {check.id}."
                if parsed is CheckResult.UNSURE
                else change.unresolved_uncertainty_summary
            ),
            version=change.version + 1, updated_at=self._now())
        self._changes[current_change_id] = (owner_user_id, change)
        self._manual_commands[command_id] = ("check", check_id)
        return change, check, next_check, False

    async def get_latest_check(self, owner_user_id: str, project_id: uuid.UUID,
                               current_change_id: uuid.UUID) -> V2Check | None:
        self._owned_change(owner_user_id, project_id, current_change_id)
        checks = [check for owner, check in self._checks.values()
                  if owner == owner_user_id and check.current_change_id == current_change_id]
        return checks[-1] if checks else None

    async def get_active_recovery_case(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID,
    ) -> V2RecoveryCase | None:
        self._owned_change(owner_user_id, project_id, current_change_id)
        active = {
            RecoveryStatus.OPEN, RecoveryStatus.INVESTIGATING,
            RecoveryStatus.CORRECTING, RecoveryStatus.RECHECKING,
        }
        rows = [case for owner, case in self._recovery_cases.values()
                if owner == owner_user_id and case.project_id == project_id
                and case.current_change_id == current_change_id and case.status in active]
        return rows[0] if rows else None

    async def record_recovery_symptom(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, recovery_case_id: uuid.UUID,
        expected_current_change_version: int, command_id: uuid.UUID,
        observed_symptom: str, last_known_working_statement: str | None,
        last_known_working_certainty: str, investigation_prompt: str,
        risk: str, risk_reason_key: str | None, risk_policy_version: str,
        risk_input_fingerprint: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        existing = self._recovery_commands.get(command_id)
        if existing:
            if existing != ("symptom", recovery_case_id):
                raise V2RepositoryConflict("Recovery command reused")
            return change, self._recovery_cases[recovery_case_id][1], True
        if await self.get_active_recovery_case(owner_user_id, project_id, current_change_id):
            raise V2RepositoryConflict("active Recovery Case exists")
        if (change.version != expected_current_change_version
                or change.lifecycle_state is not CurrentChangeState.RECOVERING
                or change.resume_step is not ResumeStep.RECOVERY_SYMPTOM):
            raise V2RepositoryConflict("stale Recovery symptom")
        now = self._now()
        case = V2RecoveryCase(
            id=recovery_case_id, project_id=project_id,
            current_change_id=current_change_id, status=RecoveryStatus.INVESTIGATING,
            intended_behavior=change.done_condition_snapshot or change.goal_snapshot,
            observed_symptom=observed_symptom.strip(),
            last_known_working_statement=(last_known_working_statement.strip()
                                          if last_known_working_statement else None),
            last_known_working_certainty=last_known_working_certainty,
            candidate_change_summary=change.goal_snapshot, student_hypothesis=None,
            proposed_first_check=None, investigation_finding=None, cause_summary=None,
            correction_summary=None, resolution_summary=None, opened_at=now,
            resolved_at=None, version=1,
        )
        change = replace(
            change, resume_step=ResumeStep.RECOVERY_INVESTIGATE,
            prompt_draft=investigation_prompt,
            prompt_draft_version=change.prompt_draft_version + 1,
            risk=RiskMode(risk), risk_reason_key=risk_reason_key,
            risk_policy_version=risk_policy_version,
            risk_input_fingerprint=risk_input_fingerprint,
            help_context_key=None, support_level_disclosed=SupportLevel.NONE,
            version=change.version + 1, updated_at=now,
        )
        self._changes[current_change_id] = (owner_user_id, change)
        self._recovery_cases[recovery_case_id] = (owner_user_id, case)
        self._recovery_commands[command_id] = ("symptom", recovery_case_id)
        return change, case, False

    async def accept_recovery_prompt(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, recovery_case_id: uuid.UUID, purpose: str,
        expected_current_change_version: int, expected_prompt_draft_version: int,
        acceptance_command_id: uuid.UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        case = await self.get_active_recovery_case(owner_user_id, project_id, current_change_id)
        if case is None or case.id != recovery_case_id:
            raise V2RepositoryNotFound("Recovery Case not found")
        existing_id = self._acceptance_commands.get((owner_user_id, acceptance_command_id))
        if existing_id:
            return change, self._prompt_versions[existing_id][1], True
        parsed = PromptPurpose(purpose)
        expected_status = (RecoveryStatus.INVESTIGATING if parsed is PromptPurpose.DIAGNOSTIC
                           else RecoveryStatus.CORRECTING)
        if (change.version != expected_current_change_version
                or change.prompt_draft_version != expected_prompt_draft_version
                or change.lifecycle_state is not CurrentChangeState.RECOVERING
                or case.status is not expected_status or change.prompt_draft is None
                or change.coding_agent_key is None):
            raise V2RepositoryConflict("stale Recovery prompt")
        prompt_id = uuid.uuid4()
        now = self._now()
        prior = await self.list_prompt_versions(owner_user_id, project_id, current_change_id)
        prompt = V2PromptVersion(
            id=prompt_id, project_ref=change.project_ref,
            current_change_id=current_change_id, ordinal=len(prior)+1,
            purpose=parsed, content=change.prompt_draft,
            content_sha256=hashlib.sha256(change.prompt_draft.encode()).hexdigest(),
            input_current_change_version=change.version,
            # The accepted schema snapshots these columns only for feature
            # prompts; Recovery freshness is purpose/content/current-state based.
            input_goal_snapshot=None,
            input_done_condition_snapshot=None,
            input_boundary_snapshots=None,
            generation_attempt_id=None, coding_agent_key=change.coding_agent_key,
            effort_category=change.effort_category, provider_mapping_key=None,
            provider_mapping_version=None, accepted_at=now, handed_off_at=None, version=1,
        )
        change = replace(change, latest_prompt_version_id=prompt_id,
                         version=change.version+1, updated_at=now)
        self._prompt_versions[prompt_id] = (owner_user_id, prompt)
        self._acceptance_commands[(owner_user_id, acceptance_command_id)] = prompt_id
        self._changes[current_change_id] = (owner_user_id, change)
        return change, prompt, False

    async def handoff_recovery_prompt(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, recovery_case_id: uuid.UUID,
        prompt_version_id: uuid.UUID, expected_current_change_version: int,
        expected_prompt_version: int, handoff_command_id: uuid.UUID,
    ) -> tuple[V2CurrentChange, V2PromptVersion, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        case = await self.get_active_recovery_case(owner_user_id, project_id, current_change_id)
        if case is None or case.id != recovery_case_id:
            raise V2RepositoryNotFound("Recovery Case not found")
        existing_id = self._handoff_commands.get((owner_user_id, handoff_command_id))
        if existing_id:
            return change, self._prompt_versions[existing_id][1], True
        entry = self._prompt_versions.get(prompt_version_id)
        if entry is None or entry[0] != owner_user_id:
            raise V2RepositoryNotFound("Prompt Version not found")
        prompt = entry[1]
        expected_status = (RecoveryStatus.INVESTIGATING
                           if prompt.purpose is PromptPurpose.DIAGNOSTIC
                           else RecoveryStatus.CORRECTING)
        if (change.version != expected_current_change_version
                or prompt.version != expected_prompt_version
                or change.lifecycle_state is not CurrentChangeState.RECOVERING
                or case.status is not expected_status
                or change.latest_prompt_version_id != prompt.id
                or prompt.handed_off_at is not None):
            raise V2RepositoryConflict("stale Recovery handoff")
        now = self._now()
        prompt = replace(prompt, handed_off_at=now, version=prompt.version+1)
        change = replace(change, lifecycle_state=CurrentChangeState.AWAITING_AGENT,
                         resume_step=ResumeStep.RETURN_OUTCOME,
                         handoff_command_id=handoff_command_id,
                         version=change.version+1, updated_at=now)
        self._prompt_versions[prompt.id] = (owner_user_id, prompt)
        self._changes[current_change_id] = (owner_user_id, change)
        self._handoff_commands[(owner_user_id, handoff_command_id)] = prompt.id
        return change, prompt, False

    async def record_recovery_investigation_return(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, recovery_case_id: uuid.UUID,
        expected_current_change_version: int, command_id: uuid.UUID,
        finding: str, correction_summary: str, correction_prompt: str,
        risk: str, risk_reason_key: str | None, risk_policy_version: str,
        risk_input_fingerprint: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        case = await self.get_active_recovery_case(owner_user_id, project_id, current_change_id)
        existing = self._recovery_commands.get(command_id)
        if existing:
            return change, self._recovery_cases[recovery_case_id][1], True
        prompt = self._prompt_versions[change.latest_prompt_version_id][1]
        if (case is None or case.id != recovery_case_id
                or change.version != expected_current_change_version
                or change.lifecycle_state is not CurrentChangeState.AWAITING_AGENT
                or case.status is not RecoveryStatus.INVESTIGATING
                or prompt.purpose is not PromptPurpose.DIAGNOSTIC
                or prompt.handed_off_at is None):
            raise V2RepositoryConflict("stale investigation return")
        now = self._now()
        case = replace(case, status=RecoveryStatus.CORRECTING,
                       investigation_finding=finding.strip(),
                       correction_summary=correction_summary.strip(),
                       version=case.version+1)
        change = replace(change, lifecycle_state=CurrentChangeState.RECOVERING,
            resume_step=ResumeStep.RECOVERY_CORRECT, prompt_draft=correction_prompt,
            prompt_draft_version=change.prompt_draft_version+1, risk=RiskMode(risk),
            risk_reason_key=risk_reason_key, risk_policy_version=risk_policy_version,
            risk_input_fingerprint=risk_input_fingerprint, help_context_key=None,
            support_level_disclosed=SupportLevel.NONE, version=change.version+1,
            updated_at=now)
        self._changes[current_change_id] = (owner_user_id, change)
        self._recovery_cases[recovery_case_id] = (owner_user_id, case)
        self._recovery_commands[command_id] = ("investigation", recovery_case_id)
        return change, case, False

    async def record_recovery_correction_return(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, recovery_case_id: uuid.UUID,
        expected_current_change_version: int, command_id: uuid.UUID,
        check_id: uuid.UUID, check_plan: str,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, V2Check, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        case = await self.get_active_recovery_case(owner_user_id, project_id, current_change_id)
        if self._recovery_commands.get(command_id):
            return change, self._recovery_cases[recovery_case_id][1], self._checks[check_id][1], True
        prompt = self._prompt_versions[change.latest_prompt_version_id][1]
        if (case is None or case.id != recovery_case_id
                or change.version != expected_current_change_version
                or change.lifecycle_state is not CurrentChangeState.AWAITING_AGENT
                or case.status is not RecoveryStatus.CORRECTING
                or prompt.purpose is not PromptPurpose.CORRECTION
                or prompt.handed_off_at is None):
            raise V2RepositoryConflict("stale correction return")
        check = V2Check(id=check_id, project_id=project_id,
            current_change_id=current_change_id, check_plan=check_plan.strip(),
            plan_source="codize", status="proposed", result=None,
            student_observation=None, performed_at=None, version=1)
        now = self._now()
        case = replace(case, status=RecoveryStatus.RECHECKING, version=case.version+1)
        change = replace(change, lifecycle_state=CurrentChangeState.RECOVERING,
            resume_step=ResumeStep.RECOVERY_RECHECK, help_context_key=None,
            support_level_disclosed=SupportLevel.NONE, version=change.version+1,
            updated_at=now)
        self._checks[check_id] = (owner_user_id, check)
        self._changes[current_change_id] = (owner_user_id, change)
        self._recovery_cases[recovery_case_id] = (owner_user_id, case)
        self._recovery_commands[command_id] = ("correction", recovery_case_id)
        return change, case, check, False

    async def record_recovery_check(
        self, owner_user_id: str, project_id: uuid.UUID,
        current_change_id: uuid.UUID, recovery_case_id: uuid.UUID,
        check_id: uuid.UUID, expected_current_change_version: int,
        expected_check_version: int, command_id: uuid.UUID, result: str,
        observation: str, performed_by_student: bool,
        next_check_id: uuid.UUID | None, investigation_prompt: str | None,
        risk: str | None, risk_reason_key: str | None,
        risk_policy_version: str | None, risk_input_fingerprint: str | None,
    ) -> tuple[V2CurrentChange, V2RecoveryCase, V2Check, V2Check | None, bool]:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        case = await self.get_active_recovery_case(owner_user_id, project_id, current_change_id)
        check = self._checks.get(check_id, (None, None))[1]
        if self._recovery_commands.get(command_id):
            next_check = self._checks.get(next_check_id, (None, None))[1] if next_check_id else None
            return change, case, check, next_check, True
        if (case is None or case.id != recovery_case_id or check is None
                or change.version != expected_current_change_version
                or check.version != expected_check_version or check.status != "proposed"
                or change.lifecycle_state is not CurrentChangeState.RECOVERING
                or change.resume_step is not ResumeStep.RECOVERY_RECHECK
                or case.status is not RecoveryStatus.RECHECKING
                or not performed_by_student or not observation.strip()):
            raise V2RepositoryConflict("stale Recovery recheck")
        parsed = CheckResult(result)
        now = self._now()
        check = replace(check, status="performed", result=parsed,
                        student_observation=observation.strip(), performed_at=now,
                        version=check.version+1)
        self._checks[check_id] = (owner_user_id, check)
        next_check = None
        if parsed is CheckResult.UNSURE:
            next_check = V2Check(id=next_check_id, project_id=project_id,
                current_change_id=current_change_id, check_plan=check.check_plan,
                plan_source="codize", status="proposed", result=None,
                student_observation=None, performed_at=None, version=1)
            self._checks[next_check_id] = (owner_user_id, next_check)
        failed = parsed in {CheckResult.DID_NOT_WORK, CheckResult.PARTLY_WORKED}
        if failed:
            case = replace(case, status=RecoveryStatus.INVESTIGATING,
                           proposed_first_check=check.check_plan, version=case.version+1)
        change = replace(change,
            resume_step=(ResumeStep.RECOVERY_INVESTIGATE if failed
                         else ResumeStep.RECOVERY_RECHECK),
            prompt_draft=(investigation_prompt if failed else change.prompt_draft),
            prompt_draft_version=change.prompt_draft_version+(1 if failed else 0),
            risk=RiskMode(risk) if risk else change.risk,
            risk_reason_key=risk_reason_key if failed else change.risk_reason_key,
            risk_policy_version=risk_policy_version or change.risk_policy_version,
            risk_input_fingerprint=risk_input_fingerprint or change.risk_input_fingerprint,
            unresolved_uncertainty_summary=(
                f"Student remains unsure after Recovery recheck {check.id}."
                if parsed is CheckResult.UNSURE else change.unresolved_uncertainty_summary),
            version=change.version+1, updated_at=now)
        self._changes[current_change_id] = (owner_user_id, change)
        self._recovery_cases[recovery_case_id] = (owner_user_id, case)
        self._recovery_commands[command_id] = ("recheck", recovery_case_id)
        return change, case, check, next_check, False

    async def complete_manual_change(
        self, owner_user_id: str, project_id: uuid.UUID, current_change_id: uuid.UUID,
        expected_current_change_version: int, expected_plan_version: int,
        expected_plan_item_version: int, command_id: uuid.UUID, check: V2Check,
    ) -> bool:
        change = self._owned_change(owner_user_id, project_id, current_change_id)
        project = self._owned_project(owner_user_id, project_id)
        if self._manual_commands.get(command_id):
            return True
        if change.version != expected_current_change_version or project.plan_version != expected_plan_version or change.plan_item_id is None:
            raise V2RepositoryConflict("stale completion")
        item = self._plans[project_id][change.plan_item_id]
        if item.version != expected_plan_item_version or check.result is not CheckResult.WORKED:
            raise V2RepositoryInvalidState("ineligible completion")
        now = self._now()
        self._plans[project_id][item.id] = replace(item, status=PlanItemStatus.DONE,
            completed_at=now, terminal_current_change_id=current_change_id,
            version=item.version + 1)
        self._changes[current_change_id] = (owner_user_id, replace(change,
            lifecycle_state=CurrentChangeState.COMPLETED, resume_step=None,
            accepted_outcome_summary=check.student_observation,
            completed_at=now, version=change.version + 1, updated_at=now))
        recovery = await self.get_active_recovery_case(
            owner_user_id, project_id, current_change_id
        )
        if recovery is not None:
            if recovery.status is not RecoveryStatus.RECHECKING:
                raise V2RepositoryInvalidState("Recovery is not ready for completion")
            self._recovery_cases[recovery.id] = (owner_user_id, replace(
                recovery, status=RecoveryStatus.RESOLVED,
                resolution_summary=check.student_observation,
                resolved_at=now, version=recovery.version + 1,
            ))
        self._store_project(owner_user_id, replace(project,
            plan_version=project.plan_version + 1, version=project.version + 1,
            first_version_completed_at=now, updated_at=now))
        same_change_testing = [
            item for evidence_owner, item in self._learner_evidence.values()
            if evidence_owner == owner_user_id
            and item.competency_key == "testing"
            and item.source_current_change_id == current_change_id
        ]
        latest_support = same_change_testing[-1] if same_change_testing else None
        if check.plan_source == "codize":
            completion_elicitation = "taught"
            completion_support = SupportLevel.TEACH
        else:
            completion_elicitation = latest_support.elicitation if latest_support else "spontaneous"
            completion_support = latest_support.support_level if latest_support else SupportLevel.NONE
        self.seed_learner_evidence(
            owner_user_id,
            "testing",
            elicitation=completion_elicitation,
            support_level=completion_support,
            current_change_id=current_change_id,
            observed_at=now,
        )
        self._manual_commands[command_id] = ("complete", current_change_id)
        return False

    async def get_preferences(self, owner_user_id: str) -> V2UserPreferences:
        return self._preferences.get(owner_user_id, V2UserPreferences(True, "system", 0))

    async def update_dialogue_sound(self, owner_user_id: str, expected_version: int,
                                    enabled: bool) -> V2UserPreferences:
        current = await self.get_preferences(owner_user_id)
        if current.version > 0 and current.dialogue_sound_enabled == enabled:
            return current
        if current.version != expected_version:
            raise V2RepositoryConflict("stale preference")
        updated = V2UserPreferences(enabled, current.motion_preference,
                                    1 if current.version == 0 else current.version + 1)
        self._preferences[owner_user_id] = updated
        return updated

    async def start_generation_attempt(
        self, owner_user_id: str, project_id: uuid.UUID, payload: dict
    ) -> tuple[V2GenerationAttempt, bool]:
        project = self._owned_project(owner_user_id, project_id)
        command_id = uuid.UUID(str(payload["command_id"]))
        command_key = (owner_user_id, command_id)
        existing_id = self._generation_commands.get(command_key)
        if existing_id is not None:
            existing = self._generation_attempts[existing_id][1]
            if (
                existing.project_ref.project_id != project_id
                or existing.target_current_change_id
                != (
                    uuid.UUID(str(payload["target_current_change_id"]))
                    if payload.get("target_current_change_id")
                    else None
                )
                or existing.target_recovery_case_id
                != (
                    uuid.UUID(str(payload["target_recovery_case_id"]))
                    if payload.get("target_recovery_case_id")
                    else None
                )
                or existing.purpose.value != payload["purpose"]
                or existing.target_aggregate_version
                != payload["target_aggregate_version"]
                or existing.policy_version != payload.get("policy_version")
                or existing.config_version != payload["config_version"]
                or existing.provider_key != payload["provider_key"]
                or existing.model_key != payload["model_key"]
                or existing.input_sha256 != payload["input_sha256"]
            ):
                raise V2RepositoryConflict("generation command reused")
            return existing, True
        current_id = payload.get("target_current_change_id")
        recovery_id = payload.get("target_recovery_case_id")
        if current_id and recovery_id:
            raise V2RepositoryInvalidState("Generation Attempt has multiple targets")
        current = None
        if current_id:
            current = self._owned_change(owner_user_id, project_id, uuid.UUID(str(current_id)))
            target_version = current.version
        elif recovery_id:
            raise V2RepositoryNotFound("Recovery target not available in this fake")
        else:
            target_version = project.version
        if target_version != payload["target_aggregate_version"]:
            raise V2RepositoryConflict("stale generation target")
        attempt_id = uuid.uuid4()
        attempt = V2GenerationAttempt(
            id=attempt_id,
            project_ref=project.ref,
            target_current_change_id=current.id if current else None,
            target_recovery_case_id=None,
            purpose=GenerationPurpose(payload["purpose"]),
            target_aggregate_version=target_version,
            policy_version=payload.get("policy_version"),
            config_version=payload["config_version"],
            status=GenerationStatus.PENDING,
            provider_key=payload["provider_key"],
            model_key=payload["model_key"],
            input_sha256=payload["input_sha256"],
            safe_error_category=None,
            retryable=None,
            result_record_type=None,
            result_record_id=None,
            started_at=self._now(),
            completed_at=None,
            version=1,
        )
        self._generation_attempts[attempt_id] = (owner_user_id, attempt)
        self._generation_commands[command_key] = attempt_id
        return attempt, False

    async def finish_generation_attempt(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        generation_attempt_id: uuid.UUID,
        payload: dict,
    ) -> V2GenerationAttempt:
        project = self._owned_project(owner_user_id, project_id)
        entry = self._generation_attempts.get(generation_attempt_id)
        if (
            entry is None
            or entry[0] != owner_user_id
            or entry[1].project_ref.project_id != project_id
        ):
            raise V2RepositoryNotFound("Generation Attempt not found")
        attempt = entry[1]
        if attempt.version != payload["expected_attempt_version"]:
            raise V2RepositoryConflict("stale Generation Attempt")
        if attempt.status is not GenerationStatus.PENDING:
            raise V2RepositoryInvalidState("Generation Attempt already finished")
        if attempt.target_current_change_id:
            target = self._owned_change(owner_user_id, project_id, attempt.target_current_change_id)
            current_target_version = target.version
        else:
            current_target_version = project.version
        requested = GenerationStatus(payload["status"])
        stale = (
            requested is GenerationStatus.SUCCEEDED
            and current_target_version != attempt.target_aggregate_version
        )
        status = GenerationStatus.SUPERSEDED if stale else requested
        if status is GenerationStatus.SUCCEEDED:
            record_type = payload.get("result_record_type")
            record_id = uuid.UUID(str(payload["result_record_id"]))
            if record_type not in {"prompt_version", "build_turn"}:
                raise V2RepositoryInvalidState("invalid generation result record")
        completed = replace(
            attempt,
            status=status,
            safe_error_category=(
                payload.get("safe_error_category")
                if status is GenerationStatus.FAILED
                else None
            ),
            retryable=payload.get("retryable") if status is GenerationStatus.FAILED else None,
            result_record_type=(
                payload.get("result_record_type")
                if status is GenerationStatus.SUCCEEDED
                else None
            ),
            result_record_id=(
                uuid.UUID(str(payload["result_record_id"]))
                if status is GenerationStatus.SUCCEEDED
                else None
            ),
            completed_at=self._now(),
            version=attempt.version + 1,
        )
        self._generation_attempts[generation_attempt_id] = (owner_user_id, completed)
        return completed

    async def apply_generated_prompt_draft(
        self,
        owner_user_id: str,
        project_id: uuid.UUID,
        generation_attempt_id: uuid.UUID,
        expected_attempt_version: int,
        expected_current_change_version: int,
        expected_prompt_draft_version: int,
        prompt_text: str,
        done_condition: str | None,
        boundaries: list[str],
    ) -> tuple[V2GenerationAttempt, V2CurrentChange, bool, bool]:
        self._owned_project(owner_user_id, project_id)
        entry = self._generation_attempts.get(generation_attempt_id)
        if (
            entry is None
            or entry[0] != owner_user_id
            or entry[1].project_ref.project_id != project_id
        ):
            raise V2RepositoryNotFound("Generation Attempt not found")
        attempt = entry[1]
        if attempt.target_current_change_id is None:
            raise V2RepositoryInvalidState("prompt draft generation requires a Current Change")
        change = self._owned_change(
            owner_user_id, project_id, attempt.target_current_change_id
        )

        if attempt.status is GenerationStatus.SUCCEEDED:
            if (
                attempt.purpose is not GenerationPurpose.PROMPT_DRAFT
                or attempt.result_record_type != "prompt_draft"
                or attempt.result_record_id != change.id
            ):
                raise V2RepositoryConflict("Generation Attempt completion mismatch")
            return attempt, change, True, True
        if attempt.status is GenerationStatus.SUPERSEDED:
            return attempt, change, False, True
        if attempt.status is not GenerationStatus.PENDING:
            raise V2RepositoryInvalidState("Generation Attempt already finished")
        if attempt.version != expected_attempt_version:
            raise V2RepositoryConflict("stale Generation Attempt")
        if attempt.purpose is not GenerationPurpose.PROMPT_DRAFT:
            raise V2RepositoryInvalidState("Generation Attempt has the wrong purpose")
        if (
            change.version != attempt.target_aggregate_version
            or change.version != expected_current_change_version
        ):
            if change.version != attempt.target_aggregate_version:
                superseded = replace(
                    attempt,
                    status=GenerationStatus.SUPERSEDED,
                    completed_at=self._now(),
                    version=attempt.version + 1,
                )
                self._generation_attempts[generation_attempt_id] = (
                    owner_user_id,
                    superseded,
                )
                return superseded, change, False, False
            raise V2RepositoryConflict("stale Current Change command")
        if change.prompt_draft_version != expected_prompt_draft_version:
            raise V2RepositoryConflict("stale prompt draft")
        if (
            not change.policy_is_resolved
            or change.lifecycle_state is not CurrentChangeState.PREPARING
            or change.handoff_command_id is not None
            or change.coding_agent_key is None
        ):
            raise V2RepositoryInvalidState("generated prompt cannot be applied")
        if (
            not prompt_text.strip()
            or len(prompt_text.encode("utf-8")) > 65536
            or (
                done_condition is not None
                and (
                    not done_condition.strip()
                    or len(done_condition.encode("utf-8")) > 8192
                )
            )
            or len(boundaries) > 32
            or any(
                not boundary.strip() or len(boundary.encode("utf-8")) > 256
                for boundary in boundaries
            )
            or len("".join(boundaries).encode("utf-8")) > 8192
            or len(set(boundaries)) != len(boundaries)
        ):
            raise V2RepositoryInvalidState("invalid bounded generated prompt")
        if (
            change.prompt_draft == prompt_text
            and change.done_condition_snapshot == done_condition
            and change.boundary_snapshots == tuple(boundaries)
        ):
            raise V2RepositoryInvalidState("generated prompt did not change the draft")

        now = self._now()
        text_changed = change.prompt_draft != prompt_text
        applied = replace(
            change,
            prompt_draft=prompt_text,
            prompt_draft_version=(
                change.prompt_draft_version + (1 if text_changed else 0)
            ),
            done_condition_snapshot=done_condition,
            boundary_snapshots=tuple(boundaries),
            version=change.version + 1,
            updated_at=now,
        )
        succeeded = replace(
            attempt,
            status=GenerationStatus.SUCCEEDED,
            result_record_type="prompt_draft",
            result_record_id=change.id,
            completed_at=now,
            version=attempt.version + 1,
        )
        self._changes[change.id] = (owner_user_id, applied)
        self._generation_attempts[generation_attempt_id] = (owner_user_id, succeeded)
        return succeeded, applied, True, False


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
    EffortCategory,
    GenerationPurpose,
    GenerationStatus,
    PromptPurpose,
    V2PromptVersion,
