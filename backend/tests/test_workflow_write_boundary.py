"""M16S.1 static security contract for the projects write boundary.

Effective role behavior is exercised by the companion SQL and authenticated
HTTP smoke scripts after deployment. These tests keep the forward migration,
repository architecture, and alternate-path inventory reviewable in CI.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
MIGRATION = MIGRATIONS / "20260714064425_harden_workflow_artifact_write_boundary.sql"
SQL_VERIFY = ROOT / "scripts" / "verify_workflow_artifact_write_boundary.sql"
HTTP_VERIFY = ROOT / "scripts" / "verify_workflow_artifact_write_boundary.py"


def _sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_forward_migration_makes_projects_authenticated_read_only():
    sql = _sql(MIGRATION)
    assert "revoke all privileges on table public.projects from authenticated;" in sql
    assert "grant select on table public.projects to authenticated;" in sql
    assert not re.search(
        r"grant\s+(?:insert|update|delete|truncate|all).*?to\s+authenticated", sql
    )


def test_migration_preserves_service_role_anon_and_rls_contracts():
    sql = _sql(MIGRATION)
    assert "from service_role" not in sql
    assert "to service_role" not in sql
    assert "disable row level security" not in sql
    assert "drop policy" not in sql
    assert "tadkbymxkdncqahzshml" not in sql
    assert not any(marker in sql for marker in ("sb_secret_", "sk-or-", "aiza"))


def test_historical_migrations_remain_separate_from_m16s1():
    files = sorted(MIGRATIONS.glob("*.sql"))
    assert files[-1] == MIGRATION
    assert len(files) == 7
    older = "\n".join(_sql(path) for path in files[:-1])
    assert "harden_workflow_artifact_write_boundary" not in older


def test_rls_and_owner_read_policy_still_exist_in_schema_history():
    schema = _sql(MIGRATIONS / "20260702070937_codize_schema_with_rls.sql")
    assert "alter table public.projects enable row level security;" in schema
    assert 'create policy "projects_select_own"' in schema
    assert "for select to authenticated using (auth.uid() = user_id);" in schema


def test_browser_supabase_client_is_auth_only_with_no_product_table_calls():
    frontend = ROOT / "frontend"
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in frontend.rglob("*")
        if path.suffix in {".ts", ".tsx"} and "node_modules" not in path.parts
    )
    assert not re.search(r"\.from\(\s*['\"]", sources)
    assert "/rest/v1/" not in sources
    assert ".rpc(" not in sources
    assert "supabase.auth" in sources


def test_backend_project_writes_use_the_owner_filtered_service_repository():
    repository = (ROOT / "backend" / "app" / "services" / "project_repository.py").read_text(
        encoding="utf-8"
    )
    assert '"POST", "/projects"' in repository
    assert '"PATCH", "/projects"' in repository
    assert 'params={"id": f"eq.{project_id}", "user_id": f"eq.{user_id}"}' in repository
    assert "supabase_service_role_key.get_secret_value()" in repository


def test_no_exposed_view_or_rpc_bypass_exists_in_migration_history():
    sql = "\n".join(_sql(path) for path in MIGRATIONS.glob("*.sql"))
    assert not re.search(r"\bcreate\s+(?:or\s+replace\s+)?view\b", sql)
    functions = re.findall(r"create\s+function\s+public\.([a-z0-9_]+)\s*\(", sql)
    assert set(functions) == {"set_updated_at", "handle_new_user"}
    assert "revoke execute on function public.handle_new_user()" in sql
    assert "revoke execute on function public.set_updated_at()" in sql


def test_durable_verifiers_cover_effective_mutation_paths_and_parse():
    sql = _sql(SQL_VERIFY)
    for fragment in (
        "set local role authenticated",
        "set local role anon",
        "set local role service_role",
        "jsonb_set(",
        "workflow_artifacts ||",
        "on conflict (id) do update",
        "delete from public.projects",
        "has_function_privilege('authenticated'",
        "rollback;",
    ):
        assert fragment in sql
    http = HTTP_VERIFY.read_text(encoding="utf-8")
    for path in (
        "/workflow/1/prompt_builder",
        "/workflow/1/implementation_import",
        "/workflow/1/change-map/generate",
        "/workflow/1/change-map",
        "/workflow/1/change-map/confirm",
        "/workflow/1/review/from-change-map",
        "/workflow/1/review_board",
        "/workflow/1/verification/from-review",
        "/workflow/1/verification",
        "/workflow/2",
    ):
        assert path in http
    ast.parse(http)
