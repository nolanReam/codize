"""Regression contracts for hosted Supabase future-function ACL hardening."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FOUNDATION = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260812074622_v2_database_foundation.sql"
)
VERIFY = ROOT / "scripts" / "verify_v2_database_foundation.sql"


def _sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _forward_migration() -> Path:
    matches = tuple(
        (ROOT / "supabase" / "migrations").glob(
            "*_v2_function_default_privilege_hardening.sql"
        )
    )
    assert len(matches) == 1
    return matches[0]


def _assert_postgres_public_function_defaults_are_deny_by_default(sql: str) -> None:
    assert re.search(
        r"alter\s+default\s+privileges\s+for\s+role\s+postgres\s+"
        r"in\s+schema\s+public\s+revoke\s+execute\s+on\s+functions\s+"
        r"from\s+public\s*,\s*anon\s*,\s*authenticated\s*,\s*service_role\s*;",
        sql,
    )
    assert re.search(
        r"alter\s+default\s+privileges\s+for\s+role\s+postgres\s+"
        r"revoke\s+execute\s+on\s+functions\s+from\s+public\s*;",
        sql,
    )


def test_fresh_install_and_forward_migration_apply_the_same_postgres_hardening():
    _assert_postgres_public_function_defaults_are_deny_by_default(_sql(FOUNDATION))
    _assert_postgres_public_function_defaults_are_deny_by_default(
        _sql(_forward_migration())
    )


def test_forward_migration_changes_only_future_function_defaults():
    sql = _sql(_forward_migration())

    assert sql.count("alter default privileges") == 2
    assert " grant " not in f" {sql} "
    assert not re.search(r"\b(?:create|alter|drop)\s+(?:table|schema|role)\b", sql)
    assert not re.search(r"\b(?:insert|update|delete|truncate)\b", sql)
    assert not re.search(r"\brevoke\s+execute\s+on\s+function\s+(?!s\b)", sql)
    assert "auth." not in sql
    assert "storage." not in sql


def test_verifier_proves_default_deny_then_explicit_service_role_execute():
    sql = _sql(VERIFY)
    create_probe = sql.index(
        "create function public.codize_v2_default_acl_verification_probe()"
    )
    forbidden_default = sql.index(
        "future public function inherited a forbidden execute grant"
    )
    explicit_grant = sql.index(
        "grant execute on function public.codize_v2_default_acl_verification_probe()"
    )
    backend_check = sql.index(
        "explicit backend-only future-function grant was ineffective"
    )
    browser_check = sql.index(
        "explicit backend-only future-function grant reached a browser role"
    )
    drop_probe = sql.index(
        "drop function public.codize_v2_default_acl_verification_probe()"
    )
    rollback = sql.rindex("rollback;")

    assert create_probe < forbidden_default < explicit_grant
    assert explicit_grant < backend_check < browser_check < drop_probe < rollback
