"""Static architecture, security, provenance, and UI contracts for Phase 6."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20260824010000_v2_phase6_recovery_system.sql"
VERIFY = ROOT / "scripts/verify_v2_phase6_recovery.sql"
ROUTER = ROOT / "backend/app/routers/v2_projects.py"
SERVICE = ROOT / "backend/app/services/v2_recovery_service.py"
FRONTEND = ROOT / "frontend/app/app/project/[id]/build/page.tsx"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase6_reuses_the_eleven_tables_and_preserves_the_backend_write_boundary():
    sql = text(MIGRATION).lower()
    assert "create table" not in sql
    assert "security definer" in sql
    assert "security invoker" in sql
    assert "set search_path=''" in sql or "set search_path = ''" in sql
    assert "to service_role" in sql
    assert "to codize_v2_backend" not in sql
    compact = sql.replace(" ", "").replace("\n", "")
    assert "frompublic,anon,authenticated;" in compact
    assert "frompublic,anon,authenticated,service_role;" in compact
    assert "toanon" not in compact
    assert "toauthenticated" not in compact


def test_phase6_routes_are_owner_scoped_and_use_explicit_recovery_identity():
    router = text(ROUTER)
    for suffix in (
        "/recovery/symptom",
        "/recovery/prompt",
        "/recovery/handoff",
        "/recovery/investigation-return",
        "/recovery/correction-return",
        "/recovery/checks/{check_id}",
    ):
        assert suffix in router
    assert "require_user" in router
    assert "recovery_case_id" in text(ROOT / "backend/app/schemas/v2.py")


def test_phase6_separates_observation_agent_claim_and_student_recheck():
    sql = text(MIGRATION).lower()
    service = text(SERVICE)
    assert "'provenance','agent_claimed'" in sql.replace(" ", "").replace("\n", "")
    assert "performed_by_student" in sql
    assert "student_observation" in sql
    assert "claimed_working',false" in sql.replace(" ", "").replace("\n", "")
    assert "DO NOT MODIFY FILES YET" in service
    assert "Do not claim the bug is fixed" in service


def test_phase6_is_contextual_build_recovery_not_a_new_global_destination():
    frontend = text(FRONTEND)
    shell = text(ROOT / "frontend/components/v2/V2AppShell.tsx")
    for step in ("Observe", "Investigate", "Correct", "Recheck"):
        assert step in frontend
    assert "Student observed:" in frontend
    assert "Coding AI suggested:" in frontend
    assert "personally observe" in frontend
    assert "Recovery" not in shell


def test_phase6_sql_verifier_covers_replay_ownership_stale_writes_and_resolution():
    sql = text(VERIFY).lower()
    for marker in (
        "replayed",
        "cross-owner",
        "stale",
        "agent_claimed",
        "student-performed",
        "resolved",
        "rollback",
    ):
        assert marker in sql
