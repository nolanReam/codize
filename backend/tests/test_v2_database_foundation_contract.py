"""Static guardrails for the executable V2.2 database verification package.

The companion SQL verifier exercises behavior against PostgreSQL. These tests
keep the additive V1/V2 boundary and security-critical migration shape visible
in ordinary backend CI even when a local database is unavailable.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260812074622_v2_database_foundation.sql"
)
VERIFY = ROOT / "scripts" / "verify_v2_database_foundation.sql"
CONCURRENCY_VERIFY = ROOT / "scripts" / "verify_v2_completion_concurrency.py"

V2_TABLES = {
    "v2_projects",
    "v2_plan_items",
    "v2_current_changes",
    "v2_prompt_versions",
    "v2_checks",
    "v2_project_facts",
    "v2_build_turns",
    "v2_generation_attempts",
    "v2_recovery_cases",
    "v2_learner_evidence",
    "v2_user_preferences",
}


def _sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_migration_creates_exactly_the_eleven_canonical_v2_tables():
    sql = _sql(MIGRATION)
    created = set(re.findall(r"create\s+table\s+public\.([a-z0-9_]+)", sql))
    assert created == V2_TABLES


def test_migration_is_additive_and_has_no_v1_product_mutation():
    sql = _sql(MIGRATION)
    legacy_tables = (
        "profiles",
        "projects",
        "gate_sessions",
        "unlocks",
    )
    for table in legacy_tables:
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
        "workflow_artifacts",
        "task_progress",
        "archetype_id",
        "gate_sessions",
        "cooldown",
        "defense",
        "unlocks",
    ):
        assert legacy_contract not in sql


def test_every_v2_table_has_default_deny_rls_and_no_browser_grant():
    sql = _sql(MIGRATION)
    for table in V2_TABLES:
        assert f"alter table public.{table} enable row level security;" in sql
    assert "create policy" not in sql
    assert "to anon" not in sql
    assert "to authenticated" not in sql
    assert "from public, anon, authenticated, service_role" in sql


def test_transaction_functions_use_private_definers_and_public_invoker_wrappers():
    sql = _sql(MIGRATION)
    transaction_functions = (
        "mutate_v2_plan",
        "accept_v2_prompt_version",
        "handoff_v2_prompt_version",
        "resume_v2_recovery_handoff",
        "open_v2_recovery_case",
        "transition_v2_recovery_case",
        "complete_v2_current_change",
        "purge_v2_project",
    )
    for function in transaction_functions:
        starts = [
            match.start()
            for match in re.finditer(
                rf"create function public\.{function}\(", sql
            )
        ]
        assert len(starts) == 2
        privileged_end = sql.index("\n$$;", starts[0])
        privileged_body = sql[starts[0]:privileged_end]
        wrapper_end = sql.index("\n$wrapper$;", starts[1])
        wrapper_body = sql[starts[1]:wrapper_end]
        assert "security definer" in privileged_body
        assert "set search_path = ''" in privileged_body
        assert "security invoker" in wrapper_body
        assert "language sql" in wrapper_body
        assert f"codize_v2_internal.{function}(" in wrapper_body
        assert f"alter function codize_v2_internal.{function}(" in sql
    assert "create role codize_v2_executor" in sql
    assert "nologin noinherit" in sql
    assert "create schema if not exists codize_v2_internal" in sql
    assert "owner to codize_v2_executor" in sql
    membership_grant = sql.index(
        "grant codize_v2_executor to current_user with set true;"
    )
    ownership_transfer = sql.index("owner to codize_v2_executor")
    membership_revoke = sql.index("revoke codize_v2_executor from current_user;")
    assert membership_grant < ownership_transfer < membership_revoke
    assert (
        "alter default privileges\n"
        "  revoke execute on functions from public, anon, authenticated, service_role;"
        in sql
    )
    assert (
        "alter default privileges for role codize_v2_executor\n"
        "  revoke execute on functions from public, anon, authenticated, service_role;"
        in sql
    )
    assert "grant select on table" in sql
    assert "grant select, insert, update, delete on table public.v2_projects to service_role" not in sql
    assert "from public, anon, authenticated, service_role" in sql
    assert "to service_role" in sql


def test_custom_gucs_are_not_an_integrity_boundary():
    sql = _sql(MIGRATION)
    assert "current_setting(" not in sql
    assert "set_config(" not in sql
    assert "codize.v2_" not in sql


def test_completion_body_preserves_lock_order_and_post_lock_recheck():
    sql = _sql(MIGRATION)
    start = sql.index("create function public.complete_v2_current_change(")
    end = sql.index("\n$$;", start)
    body = sql[start:end]
    project_lock = body.index("from public.v2_projects as p")
    change_lock = body.index("from public.v2_current_changes as cc", project_lock)
    plan_lock = body.index("from public.v2_plan_items as pi", change_lock)
    recovery_lock = body.index("from public.v2_recovery_cases as rc", plan_lock)
    replay_recheck = body.index("v_change.completion_command_id = p_completion_command_id")
    source_value_validation = body.index("public.v2_system_fact_source_matches")
    first_write = body.index("update public.v2_current_changes as cc")
    assert (
        project_lock
        < change_lock
        < plan_lock
        < recovery_lock
        < replay_recheck
        < source_value_validation
        < first_write
    )
    assert "current_change_boundaries" in sql
    assert "selected_coding_agent" in sql
    assert "recovery_observed_symptom" in sql
    assert "p_expected_recovery" not in body
    assert "http" not in body


def test_verifier_exercises_behavior_and_rolls_back_all_fixtures():
    sql = _sql(VERIFY)
    for contract in (
        "set local role anon",
        "set local role authenticated",
        "set local role service_role",
        "spoofed completion guc bypassed direct-dml denial",
        "spoofed purge guc bypassed direct-dml denial",
        "direct plan dml bypassed plan-version semantics",
        "awaiting_agent without handed-off prompt unexpectedly succeeded",
        "mismatched current change / prompt handoff command unexpectedly succeeded",
        "recovery diagnostic handoff did not resume investigating",
        "recovery correction handoff did not resume rechecking",
        "required check missing unexpectedly completed",
        "explicit check waiver did not complete",
        "slowdown with missing check unexpectedly completed",
        "unresolved failed check unexpectedly completed",
        "unresolved unsure check unexpectedly completed",
        "superseding successful check did not permit completion",
        "recovery without post-recovery recheck unexpectedly completed",
        "generation attempt became durable fact provenance",
        "current change source accepted an unsupported system-observed value",
        "prompt version source accepted an unsupported system-observed value",
        "recovery case source accepted an unsupported system-observed value",
        "legitimate source accepted an unsupported system-observed fact combination",
        "performed check without a deterministic system mapping created a fact",
        "invalid system-observed fact did not roll back completion atomically",
        "failed check created an active known-working fact",
        "clearing a fact successor left a stranded predecessor",
        "ordinary learner evidence rewrite unexpectedly succeeded",
        "completion replay duplicated fact or evidence writes",
        "invalid completion did not roll back atomically",
        "stale recovery mutation changed durable versions",
        "fully populated v2 project did not cascade-purge cleanly",
        "project with more than 256 evidence rows did not purge",
        "preference did not survive purge with exact +1 detach",
        "source_project_id is null and source_current_change_id is null",
        "source_record_id is null",
        "source_operation_id is null",
        "build turn redaction changed the original content hash",
        "arbitrary teaching_target unexpectedly succeeded",
        "multibyte reason exceeded the 256-byte bound",
        "pg_default_acl permits a forbidden future-object grant",
        "global function default acl hardening is missing for an execution role",
        "private v2 executor role attributes or membership are unsafe",
        "rollback;",
    ):
        assert contract in sql


def test_two_session_verifier_covers_post_lock_duplicate_command_replay():
    source = CONCURRENCY_VERIFY.read_text(encoding="utf-8")
    ast.parse(source)
    for contract in (
        "threading.thread",
        "winner_locked.wait",
        "release_winner.set",
        "complete_v2_current_change",
        "sorted(result.values()) != [false, true]",
        "fact_count, evidence_count, change_version",
        "(1, 1, 5)",
        "cleanup_fixture()",
    ):
        assert contract in source.lower()
