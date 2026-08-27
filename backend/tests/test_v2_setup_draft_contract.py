"""Static security and compatibility checks for resumable V2 setup."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20260825042409_v2_beta_setup_draft.sql"
ROUTER = ROOT / "backend/app/routers/v2_projects.py"
REPOSITORY = ROOT / "backend/app/services/v2_repository.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_setup_draft_keeps_the_eleven_table_boundary_and_private_write_path():
    sql = _text(MIGRATION).lower()
    assert "create table" not in sql
    assert "alter table public.v2_projects" in sql
    assert "security definer" in sql
    assert "security invoker" in sql
    assert "set search_path = ''" in sql
    assert "to service_role" in sql
    assert "to anon" not in sql
    assert "to authenticated" not in sql


def test_setup_draft_is_owner_scoped_versioned_bounded_and_retry_safe():
    sql = _text(MIGRATION).lower()
    command = sql.split("create function codize_v2_internal.save_v2_setup_draft", 1)[1]
    command = command.split("create or replace function", 1)[0]
    assert "p.owner_user_id = p_owner_user_id" in command
    assert "for update" in command
    assert "v_project.version <> p_expected_project_version" in command
    assert "setup_draft_command_id = p_command_id" in command
    assert "'replayed', true" in command
    for maximum in (8192, 200, 4096):
        assert f"> {maximum}" in command


def test_setup_draft_route_stays_authenticated_and_explicitly_scoped():
    router = _text(ROUTER)
    repository = _text(REPOSITORY)
    assert '"/projects/{project_id}/setup-draft"' in router
    assert "require_user" in router
    assert '"p_owner_user_id": owner_user_id' in repository
    assert '"p_project_id": str(project_id)' in repository
