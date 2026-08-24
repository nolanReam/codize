"""Static security and product-boundary checks for the Phase 4 manual loop."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20260823064612_v2_phase4_manual_build_loop.sql"
ROUTER = ROOT / "backend/app/routers/v2_projects.py"
REPOSITORY = ROOT / "backend/app/services/v2_repository.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase4_preserves_the_eleven_table_cut_and_backend_only_boundary():
    sql = _text(MIGRATION).lower()
    assert "create table" not in sql
    assert "alter table public.projects" not in sql
    assert "security definer" in sql
    assert "security invoker" in sql
    assert "set search_path = ''" in sql
    assert "to service_role" in sql
    assert "to anon" not in sql
    assert "to authenticated" not in sql


def test_phase4_manual_check_requires_student_performance_and_observation():
    sql = _text(MIGRATION).lower()
    check = sql.split("create function codize_v2_internal.record_v2_manual_check", 1)[1]
    check = check.split("create function codize_v2_internal.update_v2_dialogue_sound", 1)[0]
    assert "p_performed_by_student is distinct from true" in check
    assert "p_observation is null" in check
    assert "insert into public.v2_build_turns" in check
    assert "'student_answer','student'" in check.replace(" ", "").replace("\n", "")
    assert "insert into public.v2_learner_evidence" not in check
    assert "student remains unsure after check" in check
    assert "v_check.id::text" in check


def test_phase4_setup_recognizes_a_fresh_session_replay_from_durable_state():
    sql = _text(MIGRATION).lower()
    setup = sql.split("create function codize_v2_internal.establish_v2_manual_project", 1)[1]
    setup = setup.split("create or replace function codize_v2_internal.start_v2_current_change", 1)[0]
    assert "v_project.lifecycle_state = 'active'" in setup
    assert "v_project.setup_resume_step = 'ready'" in setup
    assert "v_project.setup_draft = pg_catalog.jsonb_build_object" in setup
    assert "'replayed', true" in setup


def test_phase4_uses_existing_atomic_completion_and_preserves_provenance():
    repository = _text(REPOSITORY)
    assert '"complete_v2_current_change"' in repository
    assert '"source_kind": "student_observed"' in repository
    assert '"source_record_type": "check"' in repository
    assert '"competency_key": "testing"' in repository
    assert '"source_record_type": "check"' in repository


def test_phase4_routes_are_authenticated_and_explicitly_scoped():
    router = _text(ROUTER)
    for suffix in ("/manual-setup", "/confirm", "/return", "/checks/{check_id}",
                   "/complete", "/preferences/dialogue-sound"):
        assert suffix in router
    assert "require_user" in router
    repository = _text(REPOSITORY)
    assert '"p_owner_user_id": owner_user_id' in repository
    assert '"p_project_id": str(project_id)' in repository
    assert '"p_current_change_id": str(current_change_id)' in repository
