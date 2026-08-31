"""Semantic guardrails for V2 executor-role privilege setup.

Hosted Supabase runs migrations as a non-superuser. A migration that transfers
private routine ownership to ``codize_v2_executor`` must retain temporary role
membership and private-schema CREATE until their respective work is complete,
then remove both capabilities.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts" / "verify_v2_database_foundation.sql"
MIGRATIONS = tuple(
    ROOT / "supabase" / "migrations" / name
    for name in (
        "20260812074622_v2_database_foundation.sql",
        "20260813090000_v2_backend_core_primitives.sql",
        "20260815234436_v2_agent_prompt_handoff_lifecycle.sql",
        "20260823064612_v2_phase4_manual_build_loop.sql",
        "20260823150000_v2_phase5_teaching_system.sql",
        "20260824010000_v2_phase6_recovery_system.sql",
        "20260825042409_v2_beta_setup_draft.sql",
    )
)

MEMBERSHIP_GRANT = "grant codize_v2_executor to current_user with set true;"
MEMBERSHIP_REVOKE = "revoke codize_v2_executor from current_user;"
SCHEMA_CREATE_REVOKE = (
    "revoke create on schema codize_v2_internal from codize_v2_executor;"
)


def _sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _function_grants(sql: str) -> list[tuple[int, str]]:
    return [
        (match.start(), match.group(0))
        for match in re.finditer(
            r"\bgrant\s+(?:all(?:\s+privileges)?|execute)\s+on\s+function\b[^;]*;",
            sql,
            flags=re.DOTALL,
        )
    ]


def _schema_create_grants(sql: str) -> list[int]:
    return [
        match.start()
        for match in re.finditer(
            r"\bgrant\s+(?:usage\s*,\s*)?create\s+on\s+schema\s+"
            r"codize_v2_internal\s+to\s+codize_v2_executor\s*;",
            sql,
        )
    ]


def test_executor_membership_covers_private_routine_changes_and_all_grants():
    for migration in MIGRATIONS:
        sql = _sql(migration)
        assert sql.count(MEMBERSHIP_GRANT) == 1, migration.name
        assert sql.count(MEMBERSHIP_REVOKE) == 1, migration.name

        membership_grant = sql.index(MEMBERSHIP_GRANT)
        membership_revoke = sql.index(MEMBERSHIP_REVOKE)
        schema_create_grants = _schema_create_grants(sql)
        schema_create_revoke = sql.index(SCHEMA_CREATE_REVOKE)
        private_routine_changes = [
            match.start()
            for match in re.finditer(
                r"\b(?:create(?:\s+or\s+replace)?|alter)\s+function\s+"
                r"codize_v2_internal\.",
                sql,
            )
        ]
        routine_grants = _function_grants(sql)

        assert private_routine_changes, migration.name
        assert routine_grants, migration.name
        assert len(schema_create_grants) == 1, migration.name
        assert membership_grant < min(private_routine_changes), migration.name
        assert membership_grant < schema_create_grants[0], migration.name
        assert schema_create_grants[0] < min(private_routine_changes), migration.name
        assert max(private_routine_changes) < schema_create_revoke, migration.name
        assert schema_create_revoke < membership_revoke, migration.name
        assert max(private_routine_changes) < membership_revoke, migration.name
        assert max(position for position, _ in routine_grants) < membership_revoke, (
            migration.name
        )


def test_executor_membership_is_temporary_and_never_administrative():
    for migration in MIGRATIONS:
        sql = _sql(migration)
        membership_grant = sql.index(MEMBERSHIP_GRANT)
        membership_revoke = sql.index(MEMBERSHIP_REVOKE)

        assert membership_grant < membership_revoke, migration.name
        assert "grant codize_v2_executor to current_user with admin" not in sql
        assert not re.search(
            r"grant\s+codize_v2_executor\s+to\s+(?!current_user\b)", sql
        ), migration.name


def test_executor_private_schema_create_is_never_left_permanent():
    for migration in MIGRATIONS:
        sql = _sql(migration)
        grants = _schema_create_grants(sql)
        revoke = sql.index(SCHEMA_CREATE_REVOKE)

        assert len(grants) == 1, migration.name
        assert grants[0] < revoke, migration.name
        assert not _schema_create_grants(sql[revoke:]), migration.name


def test_routine_execute_grants_remain_backend_only():
    for migration in MIGRATIONS:
        grants = _function_grants(_sql(migration))
        service_role_grants = [
            statement
            for _, statement in grants
            if re.search(r"\bto\s+service_role\b", statement)
        ]

        assert service_role_grants, migration.name
        for _, statement in grants:
            assert not re.search(
                r"\bto\s+(?:public|anon|authenticated)\b", statement
            ), (migration.name, statement)


def test_service_role_table_access_remains_read_only():
    service_role_table_grants = []
    for migration in MIGRATIONS:
        sql = _sql(migration)
        service_role_table_grants.extend(
            (migration.name, match.group(0))
            for match in re.finditer(
                r"\bgrant\b[^;]*\bon\s+table\b[^;]*\bto\s+service_role\s*;",
                sql,
                flags=re.DOTALL,
            )
        )

    assert len(service_role_table_grants) == 1
    _, statement = service_role_table_grants[0]
    normalized = " ".join(statement.split())
    assert normalized.startswith("grant select on table ")


def test_foundation_verifier_allows_only_the_exact_safe_hosted_membership():
    sql = _sql(VERIFY)
    compact = " ".join(sql.split())

    assert "member_role.rolname = 'postgres'" in compact
    assert "grantor_role.rolname = 'supabase_admin'" in compact
    assert "and m.admin_option" in compact
    assert "and not m.inherit_option" in compact
    assert "and not m.set_option" in compact
    assert "select count(*) from pg_catalog.pg_auth_members" in compact
    assert ") > 1 or exists (" in compact
    assert "join pg_catalog.pg_roles as member_role" in compact
    assert "join pg_catalog.pg_roles as grantor_role" in compact
