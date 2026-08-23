"""Static boundaries for the additive V2.3B slice."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20260815234436_v2_agent_prompt_handoff_lifecycle.sql"
ROUTER = ROOT / "backend/app/routers/v2_projects.py"
REPOSITORY = ROOT / "backend/app/services/v2_repository.py"
GENERATION = ROOT / "backend/app/services/v2_generation_service.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v23b_keeps_the_eleven_table_cut_and_v1_separate():
    sql = _text(MIGRATION).lower()
    assert "create table" not in sql
    assert "alter table public.projects" not in sql
    assert "alter table public.project_" not in sql
    assert "service_role" in sql
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "revoke execute" in sql


def test_v23b_browser_has_no_table_or_rpc_path():
    sql = _text(MIGRATION).lower()
    assert "grant execute" in sql
    assert "to service_role" in sql
    assert "to anon" not in sql
    assert "to authenticated" not in sql
    repository = _text(REPOSITORY)
    assert '"p_owner_user_id": owner_user_id' in repository
    assert '"p_project_id": str(project_id)' in repository
    assert '"p_current_change_id": str(current_change_id)' in repository


def test_v23b_routes_are_narrow_and_generation_is_internal_only():
    router = _text(ROUTER)
    for suffix in (
        "/coding-agent",
        "/prompt-draft",
        "/effort",
        "/prompt-versions",
        "/handoff",
        "/build-state",
    ):
        assert suffix in router
    assert "generation-attempt" not in router
    assert "require_user" in router
    assert "provider" not in router.lower()
    assert "project_fact" not in _text(GENERATION).lower()


def test_v23b_generation_completion_cannot_drive_project_truth():
    sql = _text(MIGRATION).lower()
    finish = sql.split("create function codize_v2_internal.finish_v2_generation_attempt", 1)[1]
    finish = finish.split(
        "create function codize_v2_internal.apply_v2_generated_prompt_draft", 1
    )[0]
    assert "update public.v2_generation_attempts" in finish
    assert "update public.v2_current_changes" not in finish
    assert "insert into public.v2_project_facts" not in finish
    assert "insert into public.v2_learner_evidence" not in finish


def test_v23b_generated_prompt_application_has_one_narrow_atomic_write_boundary():
    sql = _text(MIGRATION).lower()
    application = sql.split(
        "create function codize_v2_internal.apply_v2_generated_prompt_draft", 1
    )[1]
    application = application.split("create function public.update_v2_coding_agent", 1)[0]
    assert "for update" in application
    assert application.count("update public.v2_current_changes") == 1
    assert application.count("update public.v2_generation_attempts") == 2
    assert "status = 'superseded'" in application
    assert "status = 'succeeded'" in application
    assert "insert into public.v2_project_facts" not in application
    assert "insert into public.v2_learner_evidence" not in application
    assert "lifecycle_state =" not in application
    assert "resume_step =" not in application


def test_v23b_feature_prompt_freshness_uses_exact_input_snapshots_not_aggregate_version():
    sql = _text(MIGRATION).lower()
    guard = sql.split("create function public.v2_guard_feature_prompt_snapshot", 1)[1]
    guard = guard.split("grant codize_v2_executor", 1)[0]
    for snapshot in (
        "input_goal_snapshot",
        "input_done_condition_snapshot",
        "input_boundary_snapshots",
    ):
        assert snapshot in guard
    assert "new.content is distinct from v_change.prompt_draft" in guard
    assert "new.coding_agent_key is distinct from v_change.coding_agent_key" in guard
    assert "new.effort_category is distinct from v_change.effort_category" in guard
    assert "new.input_current_change_version + 1 <> v_change.version" not in guard
