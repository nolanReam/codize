"""Two-session duplicate-command test for V2 atomic completion.

This verifier requires a disposable PostgreSQL database with the V2.2
migration already applied and a pre-existing Auth user. It deliberately is not
run against production.

Environment:
  CODEX_V2_TEST_DATABASE_URL   direct PostgreSQL connection string
  CODEX_V2_TEST_OWNER_USER_ID  auth.users.id owned by the test operator

Install the opt-in driver with: python -m pip install "psycopg[binary]>=3.2"
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid

try:
    import psycopg
except ImportError as exc:  # pragma: no cover - environment-dependent verifier
    raise SystemExit(
        'psycopg is required; install with: python -m pip install "psycopg[binary]>=3.2"'
    ) from exc


DATABASE_URL = os.environ.get("CODEX_V2_TEST_DATABASE_URL")
OWNER_TEXT = os.environ.get("CODEX_V2_TEST_OWNER_USER_ID")
if not DATABASE_URL or not OWNER_TEXT:
    raise SystemExit(
        "Set CODEX_V2_TEST_DATABASE_URL and CODEX_V2_TEST_OWNER_USER_ID "
        "for a disposable migrated database."
    )

OWNER_ID = uuid.UUID(OWNER_TEXT)
PROJECT_ID = uuid.uuid4()
CHANGE_ID = uuid.uuid4()
CHECK_ID = uuid.uuid4()
ACCEPT_COMMAND_ID = uuid.uuid4()
HANDOFF_COMMAND_ID = uuid.uuid4()
COMPLETION_COMMAND_ID = uuid.uuid4()
PROMPT = "Implement the isolated concurrency fixture."

FACT_INPUTS = json.dumps(
    [
        {
            "fact_type": "known_working_behavior",
            "subject_key": "concurrent_completion",
            "value_kind": "boolean",
            "value": True,
            "source_kind": "student_observed",
            "source_record_type": "check",
            "source_record_id": str(CHECK_ID),
            "observed_at": "2026-08-12T12:00:00Z",
        }
    ]
)
EVIDENCE_INPUTS = json.dumps(
    [
        {
            "competency_key": "testing",
            "observed_behavior": "Ran the isolated concurrency check and reported its result.",
            "elicitation": "asked",
            "support_level": "none",
            "context_key": "normal_novel",
            "source_record_type": "check",
            "source_record_id": str(CHECK_ID),
            "observed_at": "2026-08-12T12:00:00Z",
            "evidence_policy_version": "qualification-v1",
        }
    ]
)

COMPLETE_SQL = """
select * from public.complete_v2_current_change(
  %s, %s, %s, 4, null, null, %s, false,
  'Concurrent completion persisted once.', null, %s::jsonb, %s::jsonb
)
"""


def setup_fixture() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.v2_projects (
                  id, owner_user_id, display_name, lifecycle_state,
                  setup_resume_step, coding_agent_key, create_command_id
                ) values (%s, %s, 'Concurrency verifier', 'active', 'ready',
                  'test-agent', %s)
                """,
                (PROJECT_ID, OWNER_ID, uuid.uuid4()),
            )
            cursor.execute(
                """
                insert into public.v2_current_changes (
                  id, project_id, owner_user_id, change_kind, lifecycle_state,
                  resume_step, goal_snapshot, done_condition_snapshot,
                  prompt_draft, coding_agent_key, effort_category,
                  teaching_mode, teaching_reason_key, teaching_policy_version,
                  risk, risk_policy_version, create_command_id
                ) values (
                  %s, %s, %s, 'build', 'preparing', 'prompt',
                  'Exercise duplicate completion', 'Only one command writes',
                  %s, 'test-agent', 'standard', 'skip', 'policy_not_set',
                  'unresolved-v0', 'normal', 'risk-v1', %s
                )
                """,
                (CHANGE_ID, PROJECT_ID, OWNER_ID, PROMPT, uuid.uuid4()),
            )
            cursor.execute(
                """
                select * from public.accept_v2_prompt_version(
                  %s, %s, %s, 1, 1, %s, 'feature', null, %s, %s,
                  null, 'test-agent', 'standard', null, null
                )
                """,
                (
                    OWNER_ID,
                    PROJECT_ID,
                    CHANGE_ID,
                    ACCEPT_COMMAND_ID,
                    PROMPT,
                    hashlib.sha256(PROMPT.encode()).hexdigest(),
                ),
            )
            cursor.execute(
                "select latest_prompt_version_id from public.v2_current_changes where id = %s",
                (CHANGE_ID,),
            )
            prompt_version_id = cursor.fetchone()[0]
            cursor.execute(
                """
                select * from public.handoff_v2_prompt_version(
                  %s, %s, %s, %s, null, 2, 1, %s
                )
                """,
                (
                    OWNER_ID,
                    PROJECT_ID,
                    CHANGE_ID,
                    prompt_version_id,
                    HANDOFF_COMMAND_ID,
                ),
            )
            cursor.execute(
                """
                update public.v2_current_changes
                set lifecycle_state = 'reviewing', resume_step = 'check',
                    student_return_outcome = 'worked', version = 4
                where id = %s
                """,
                (CHANGE_ID,),
            )
            cursor.execute(
                """
                insert into public.v2_checks (
                  id, project_id, owner_user_id, current_change_id, check_plan,
                  plan_source, status, result, student_observation,
                  create_command_id
                ) values (
                  %s, %s, %s, %s, 'Run the duplicate-command check',
                  'student', 'performed', 'worked', 'It completed once.', %s
                )
                """,
                (CHECK_ID, PROJECT_ID, OWNER_ID, CHANGE_ID, uuid.uuid4()),
            )


def complete_once(
    name: str,
    result: dict[str, object],
    locked: threading.Event | None = None,
    release: threading.Event | None = None,
) -> None:
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    COMPLETE_SQL,
                    (
                        OWNER_ID,
                        PROJECT_ID,
                        CHANGE_ID,
                        COMPLETION_COMMAND_ID,
                        FACT_INPUTS,
                        EVIDENCE_INPUTS,
                    ),
                )
                row = cursor.fetchone()
                result[name] = bool(row[-1])
                if locked is not None and release is not None:
                    locked.set()
                    if not release.wait(timeout=10):
                        raise RuntimeError("timed out waiting to release the winning transaction")
    except BaseException as exc:  # capture thread failures for the main thread
        result[name] = exc
        if locked is not None:
            locked.set()


def cleanup_fixture() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select version, lifecycle_state from public.v2_projects where id = %s for update",
                (PROJECT_ID,),
            )
            project = cursor.fetchone()
            if project is None:
                return
            version, lifecycle = project
            if lifecycle != "deletion_pending":
                cursor.execute(
                    """
                    update public.v2_projects
                    set lifecycle_state = 'deletion_pending',
                        deletion_requested_at = now() - interval '2 minutes',
                        purge_after = now() - interval '1 minute',
                        deletion_command_id = %s, version = version + 1
                    where id = %s
                    returning version
                    """,
                    (uuid.uuid4(), PROJECT_ID),
                )
                version = cursor.fetchone()[0]
            cursor.execute(
                "select public.purge_v2_project(%s, %s, %s, 'standard', '[]'::jsonb)",
                (OWNER_ID, PROJECT_ID, version),
            )


def main() -> None:
    setup_fixture()
    result: dict[str, object] = {}
    winner_locked = threading.Event()
    release_winner = threading.Event()
    first = threading.Thread(
        target=complete_once,
        args=("first", result, winner_locked, release_winner),
        daemon=True,
    )
    second = threading.Thread(
        target=complete_once,
        args=("second", result),
        daemon=True,
    )
    try:
        first.start()
        if not winner_locked.wait(timeout=10):
            raise RuntimeError("first completion did not acquire and retain its locks")
        second.start()
        time.sleep(0.5)  # second session is now blocked behind the Project lock
        release_winner.set()
        first.join(timeout=10)
        second.join(timeout=10)
        if first.is_alive() or second.is_alive():
            raise RuntimeError("concurrent completion verifier timed out")
        errors = [value for value in result.values() if isinstance(value, BaseException)]
        if errors:
            raise errors[0]
        if sorted(result.values()) != [False, True]:
            raise AssertionError(f"expected one write and one replay, got {result!r}")

        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      (select count(*) from public.v2_project_facts
                       where source_operation_id = %s),
                      (select count(*) from public.v2_learner_evidence
                       where source_operation_id = %s),
                      (select version from public.v2_current_changes where id = %s)
                    """,
                    (COMPLETION_COMMAND_ID, COMPLETION_COMMAND_ID, CHANGE_ID),
                )
                fact_count, evidence_count, change_version = cursor.fetchone()
                if (fact_count, evidence_count, change_version) != (1, 1, 5):
                    raise AssertionError(
                        "duplicate command wrote more than once or advanced the version twice: "
                        f"{(fact_count, evidence_count, change_version)!r}"
                    )
        print("PASS: concurrent completion wrote once and replayed current canonical state")
    finally:
        release_winner.set()
        cleanup_fixture()


if __name__ == "__main__":
    main()
