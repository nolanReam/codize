"""Static security and persistence-boundary guards for V2.3A.

The behavioral route suite uses an in-memory repository. These tests keep the
real PostgREST adapter and additive SQL command migration visible in ordinary
CI when a disposable PostgreSQL database is not configured.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260813090000_v2_backend_core_primitives.sql"
)
REPOSITORY = ROOT / "backend" / "app" / "services" / "v2_repository.py"
ROUTER = ROOT / "backend" / "app" / "routers" / "v2_projects.py"
VERIFY = ROOT / "scripts" / "verify_v2_backend_core.sql"

COMMANDS = (
    "create_v2_project",
    "resolve_v2_current_change_policy",
    "promote_v2_temporary_project",
    "start_v2_current_change",
    "cancel_v2_current_change",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_command_migration_preserves_entity_cut_and_does_not_touch_v1():
    sql = _text(MIGRATION)
    assert "create table" not in sql
    assert sql.count("add column") == 2
    assert "add column promotion_command_id uuid" in sql
    assert "add column policy_resolution_command_id uuid" in sql
    for table in ("profiles", "projects", "gate_sessions", "unlocks"):
        assert not re.search(
            rf"\b(?:alter|drop|truncate)\s+table\s+(?:if\s+exists\s+)?public\.{table}\b",
            sql,
        )
        assert not re.search(
            rf"\b(?:insert\s+into|update|delete\s+from)\s+public\.{table}\b",
            sql,
        )
    for legacy_contract in (
        "current_phase",
        "task_progress",
        "workflow_artifacts",
        "gate_sessions",
        "cooldown",
        "defense",
        "unlocks",
    ):
        assert legacy_contract not in sql


def test_each_new_command_has_a_private_definer_and_public_invoker_wrapper():
    sql = _text(MIGRATION)
    for command in COMMANDS:
        private_start = sql.index(f"create function codize_v2_internal.{command}(")
        private_end = sql.index("\n$$;", private_start)
        private_body = sql[private_start:private_end]
        public_start = sql.index(f"create function public.{command}(")
        public_end = sql.index("\n$wrapper$;", public_start)
        public_body = sql[public_start:public_end]

        assert "security definer" in private_body
        assert "set search_path = ''" in private_body
        assert "security invoker" in public_body
        assert "language sql" in public_body
        assert f"codize_v2_internal.{command}(" in public_body
        assert f"alter function codize_v2_internal.{command}(" in sql
        assert f"owner to codize_v2_executor" in sql

    assert "from public, anon, authenticated, service_role" in sql
    assert "to service_role" in sql
    assert "grant select, insert" not in sql
    assert "grant update" not in sql
    assert "grant delete" not in sql


def test_new_database_commands_are_owner_scoped_and_preserve_lock_order():
    sql = _text(MIGRATION)
    for owner_predicate in (
        "p.owner_user_id = p_owner_user_id",
        "cc.owner_user_id = p_owner_user_id",
        "pi.owner_user_id = p_owner_user_id",
    ):
        assert owner_predicate in sql

    start = sql.index("create function codize_v2_internal.start_v2_current_change(")
    end = sql.index("\n$$;", start)
    start_body = sql[start:end]
    assert start_body.index("from public.v2_projects as p") < start_body.index(
        "from public.v2_plan_items as pi"
    )
    assert "lifecycle_state in ('preparing', 'awaiting_agent', 'reviewing', 'recovering')" in start_body

    cancel = sql.index("create function codize_v2_internal.cancel_v2_current_change(")
    end = sql.index("\n$$;", cancel)
    cancel_body = sql[cancel:end]
    assert cancel_body.index("from public.v2_projects as p") < cancel_body.index(
        "from public.v2_current_changes as cc"
    )
    assert "if v_change.lifecycle_state in ('completed', 'cancelled')" in cancel_body
    assert "set_state" not in sql


def test_unresolved_policy_is_guarded_at_rows_and_v2_2_commands():
    sql = _text(MIGRATION)
    foundation = _text(
        ROOT / "supabase" / "migrations" / "20260812074622_v2_database_foundation.sql"
    )
    assert "v2_current_changes_unresolved_policy_state_check" in sql
    assert "v2_guard_policy_resolution" in sql
    assert "unresolved v2 policy fields cannot be partially rewritten" in sql
    for rejection in (
        "prompt acceptance requires resolved v2 policy",
        "prompt handoff requires resolved v2 policy",
        "completion requires resolved v2 policy",
        "unresolved v2 policy permits only initial preparation or cancellation",
    ):
        assert rejection in foundation


def test_promotion_requires_resolved_recovery_and_exact_command_provenance():
    sql = _text(MIGRATION)
    start = sql.index("create function codize_v2_internal.promote_v2_temporary_project(")
    end = sql.index("\n$$;", start)
    body = sql[start:end]
    assert "v_project.promotion_command_id = p_command_id" in body
    assert "cc.lifecycle_state <> 'completed'" in body
    assert "rc.status <> 'resolved'" in body
    assert "setup_resume_step = 'existing_project_context'" in body
    assert "setup_resume_step = 'ready'" not in body


def test_real_repository_reads_are_explicitly_scoped_and_writes_use_only_rpc():
    source = _text(REPOSITORY)
    for table_path in ("/v2_projects", "/v2_plan_items", "/v2_current_changes"):
        assert table_path in source
    assert '"owner_user_id": f"eq.{owner_user_id}"' in source
    assert '"project_id": f"eq.{project_id}"' in source
    assert '"id": f"eq.{project_id}"' in source
    assert 'return await self._request("post", f"/rpc/{name}", body=body)' in source

    # V2 table paths are only ever used with GET. All POST calls are RPCs.
    assert not re.search(r'_request\(\s*"(?:post|patch|put|delete)"\s*,\s*"/v2_', source)
    get_project_start = source.index("async def get_project(", source.index("class supabasev2repository"))
    get_project_end = source.index("async def list_projects(", get_project_start)
    get_project_body = source[get_project_start:get_project_end]
    assert '"id": f"eq.{project_id}"' in get_project_body
    assert '"owner_user_id": f"eq.{owner_user_id}"' in get_project_body
    assert '"order"' not in get_project_body


def test_router_has_no_user_id_input_or_frontend_database_credential_contract():
    source = _text(ROUTER)
    assert "require_user" in source
    assert "user.user_id" in source
    assert "owner_user_id:" not in source
    assert "service_role" not in source
    assert "supabase" not in source


def test_disposable_database_verifier_covers_commands_security_and_rollback():
    sql = _text(VERIFY)
    for contract in (
        "set local role anon",
        "set local role service_role",
        "anon unexpectedly executed a v2.3a command",
        "service_role unexpectedly wrote a v2 project directly",
        "cross-owner v2 project mutation unexpectedly succeeded",
        "new idea did not begin in canonical draft setup",
        "already-building entry claimed readiness prematurely",
        "recovery-first project creation accepted missing context",
        "unresolved policy prompt acceptance unexpectedly succeeded",
        "unresolved policy prompt handoff unexpectedly succeeded",
        "unresolved policy completion unexpectedly succeeded",
        "unresolved policy later lifecycle transition unexpectedly succeeded",
        "partial v2 policy resolution unexpectedly succeeded",
        "zero-recovery project promotion unexpectedly succeeded",
        "cancelled recovery project promotion unexpectedly succeeded",
        "open recovery project promotion unexpectedly succeeded",
        "valid resolved recovery promotion returned the wrong state",
        "unrelated active project was treated as a promotion replay",
        "genuine duplicate promotion replay was not safe",
        "temporary recovery project was not purged",
        "rollback;",
    ):
        assert contract in sql
