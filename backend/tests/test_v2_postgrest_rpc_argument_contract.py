"""Public V2 RPC wrappers must match the backend's named PostgREST payloads."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = next(
    (ROOT / "supabase" / "migrations").glob(
        "*_fix_v2_postgrest_named_rpc_arguments.sql"
    )
)
REPOSITORY = ROOT / "backend" / "app" / "services" / "v2_repository.py"

EXPECTED_ARGUMENTS = {
    "save_v2_setup_draft": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_expected_project_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_project_context", "text"),
        ("p_initial_change_label", "text"),
        ("p_done_condition", "text"),
    ),
    "establish_v2_manual_project": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_expected_project_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_project_context", "text"),
        ("p_plan_item_id", "uuid"),
        ("p_change_label", "text"),
        ("p_done_condition", "text"),
    ),
    "confirm_v2_manual_current_change": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
    ),
    "record_v2_manual_return": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_outcome", "text"),
        ("p_check_id", "uuid"),
    ),
    "record_v2_manual_check": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_check_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_expected_check_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_result", "text"),
        ("p_observation", "text"),
        ("p_performed_by_student", "boolean"),
        ("p_next_check_id", "uuid"),
    ),
    "update_v2_dialogue_sound": (
        ("p_owner_user_id", "uuid"),
        ("p_expected_version", "bigint"),
        ("p_dialogue_sound_enabled", "boolean"),
    ),
    "disclose_v2_teaching_help": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_context", "text"),
    ),
    "record_v2_teaching_response": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_context", "text"),
        ("p_response", "text"),
        ("p_elicitation", "text"),
        ("p_support_level", "text"),
    ),
    "record_v2_effort_attempt": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_selected", "text"),
        ("p_recommended", "text"),
        ("p_appropriate", "boolean"),
    ),
    "create_v2_student_check_plan": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_check_id", "uuid"),
        ("p_check_plan", "text"),
        ("p_elicitation", "text"),
        ("p_support_level", "text"),
    ),
    "update_v2_prompt_draft_with_risk": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_expected_prompt_draft_version", "bigint"),
        ("p_prompt_draft", "text"),
        ("p_done_condition_snapshot", "text"),
        ("p_boundary_snapshots", "text[]"),
        ("p_risk", "text"),
        ("p_risk_reason_key", "text"),
        ("p_risk_policy_version", "text"),
        ("p_risk_input_fingerprint", "text"),
    ),
    "record_v2_recovery_symptom": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_recovery_case_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_observed_symptom", "text"),
        ("p_last_known_working_statement", "text"),
        ("p_last_known_working_certainty", "text"),
        ("p_investigation_prompt", "text"),
        ("p_risk", "text"),
        ("p_risk_reason_key", "text"),
        ("p_risk_policy_version", "text"),
        ("p_risk_input_fingerprint", "text"),
    ),
    "record_v2_recovery_investigation_return": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_recovery_case_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_finding", "text"),
        ("p_correction_summary", "text"),
        ("p_correction_prompt", "text"),
        ("p_risk", "text"),
        ("p_risk_reason_key", "text"),
        ("p_risk_policy_version", "text"),
        ("p_risk_input_fingerprint", "text"),
    ),
    "record_v2_recovery_correction_return": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_recovery_case_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_check_id", "uuid"),
        ("p_check_plan", "text"),
    ),
    "record_v2_recovery_check": (
        ("p_owner_user_id", "uuid"),
        ("p_project_id", "uuid"),
        ("p_current_change_id", "uuid"),
        ("p_recovery_case_id", "uuid"),
        ("p_check_id", "uuid"),
        ("p_expected_current_change_version", "bigint"),
        ("p_expected_check_version", "bigint"),
        ("p_command_id", "uuid"),
        ("p_result", "text"),
        ("p_observation", "text"),
        ("p_performed_by_student", "boolean"),
        ("p_next_check_id", "uuid"),
        ("p_investigation_prompt", "text"),
        ("p_risk", "text"),
        ("p_risk_reason_key", "text"),
        ("p_risk_policy_version", "text"),
        ("p_risk_input_fingerprint", "text"),
    ),
}


def _migration_sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def _declared_arguments(sql: str, function_name: str) -> tuple[tuple[str, str], ...]:
    match = re.search(
        rf"create\s+or\s+replace\s+function\s+public\.{function_name}\s*"
        rf"\((.*?)\)\s*returns\s+jsonb",
        sql,
        flags=re.DOTALL,
    )
    assert match, function_name
    return tuple(
        tuple(argument.strip().split())  # type: ignore[misc]
        for argument in match.group(1).split(",")
    )


def _repository_payload_names(source: str, function_name: str) -> tuple[str, ...]:
    match = re.search(
        rf'_rpc\(\s*"{function_name}"\s*,\s*\{{(.*?)\}}\s*,?\s*\)',
        source,
        flags=re.DOTALL,
    )
    assert match, function_name
    return tuple(re.findall(r'"(p_[a-z0-9_]+)"\s*:', match.group(1)))


def test_forward_migration_matches_every_affected_backend_payload_exactly():
    sql = _migration_sql()
    repository = REPOSITORY.read_text(encoding="utf-8")

    assert sql.count("create or replace function public.") == len(EXPECTED_ARGUMENTS)
    for function_name, arguments in EXPECTED_ARGUMENTS.items():
        assert _declared_arguments(sql, function_name) == arguments
        assert _repository_payload_names(repository, function_name) == tuple(
            name for name, _ in arguments
        )


def test_forward_wrappers_keep_the_backend_only_security_boundary():
    sql = _migration_sql()
    revoke_block = sql.split("revoke all on function", 1)[1].split(
        "from public, anon, authenticated;", 1
    )[0]
    grant_block = sql.split("grant execute on function", 1)[1].split(
        "to service_role;", 1
    )[0]

    assert "security definer" not in sql
    assert sql.count("security invoker") == len(EXPECTED_ARGUMENTS)
    assert sql.count("set search_path = ''") == len(EXPECTED_ARGUMENTS)
    for function_name in EXPECTED_ARGUMENTS:
        assert f"public.{function_name}(" in revoke_block
        assert f"public.{function_name}(" in grant_block
        assert f"codize_v2_internal.{function_name}(" in sql

    assert "from public, anon, authenticated;" in sql
    assert "to service_role;" in sql
    assert "notify pgrst, 'reload schema';" in sql


def test_forward_migration_cannot_write_tables_or_expand_browser_access():
    sql = _migration_sql()

    assert not re.search(r"\b(?:insert\s+into|delete\s+from|truncate\s+)\b", sql)
    assert not re.search(r"\bupdate\s+public\.v2_", sql)
    assert not re.search(
        r"\bgrant\s+(?:all|select|insert|update|delete)\s+on\s+(?:table\s+)?",
        sql,
    )
    assert not re.search(r"\bgrant\s+execute\b[^;]*\bto\s+(?:public|anon|authenticated)\b", sql, re.DOTALL)
