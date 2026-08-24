"""Static architecture, provenance, and browser-boundary checks for Phase 5."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20260823150000_v2_phase5_teaching_system.sql"
POLICY = ROOT / "backend/app/services/v2_teaching_policy.py"
ROUTER = ROOT / "backend/app/routers/v2_projects.py"
FRONTEND_API = ROOT / "frontend/lib/v2-api.ts"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase5_reuses_the_eleven_table_architecture_and_backend_write_boundary():
    sql = text(MIGRATION).lower()
    assert "create table" not in sql
    assert "security definer" in sql
    assert "security invoker" in sql
    assert "set search_path=''" in sql or "set search_path = ''" in sql
    assert "to service_role" in sql
    assert "to anon" not in sql
    assert "to authenticated" not in sql


def test_phase5_policy_is_deterministic_versioned_and_not_model_selected():
    policy = text(POLICY)
    assert 'TEACHING_POLICY_VERSION = "phase5-beta-teaching-v1"' in policy
    assert 'RISK_POLICY_VERSION = "phase5-beta-risk-v1"' in policy
    assert 'EVIDENCE_POLICY_VERSION = "phase5-beta-evidence-v1"' in policy
    assert "resolve_teaching_decision" in policy
    assert "GenerationAttempt" not in policy
    assert "llm" not in policy.lower()


def test_phase5_evidence_has_real_student_sources_and_no_generation_source():
    sql = text(MIGRATION).lower()
    assert "insert into public.v2_learner_evidence" in sql
    assert "'build_turn',p_command_id,p_command_id" in sql.replace(" ", "").replace("\n", "")
    assert "'generation_attempt'" not in sql
    assert "-- a remind acknowledgement is navigation, not competency evidence" in sql


def test_phase5_routes_are_authenticated_owner_scoped_and_not_direct_database_calls():
    router = text(ROUTER)
    for suffix in ("/teaching/help", "/teaching/respond", "/effort-attempts", '"/projects/{project_id}/current-change/{current_change_id}/checks"'):
        assert suffix in router
    assert "require_user" in router
    frontend = text(FRONTEND_API).lower()
    assert "supabase" not in frontend
    assert "v2_learner_evidence" not in frontend
    assert "v2_build_turns" not in frontend


def test_phase5_help_and_verification_preserve_support_and_student_observation():
    sql = text(MIGRATION).lower()
    assert "when v_change.support_level_disclosed='none' then 'nudge'" in sql
    assert "when v_change.support_level_disclosed='nudge' then 'clue'" in sql
    assert "else 'teach' end" in sql
    assert "plan_source,status,source_build_turn_id" in sql
    assert "'student','proposed'" in sql
    check_plan = sql.split(
        "create function codize_v2_internal.create_v2_student_check_plan", 1
    )[1].split("-- adaptive return", 1)[0]
    assert "'worked'" not in check_plan
