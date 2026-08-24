"""V2.3B Generation Attempts stay operational and stale-safe."""

from __future__ import annotations

import asyncio
import uuid

from app.schemas.v2 import (
    ApplyGeneratedPromptDraftRequest,
    FinishGenerationAttemptRequest,
    StartGenerationAttemptRequest,
)
from app.services import v2_generation_service
from app.services.v2_errors import V2ConflictError
from app.services.v2_repository import V2RepositoryInvalidState
from app.services.v2_teaching_policy import RISK_POLICY_VERSION, risk_input_fingerprint
from tests.fakes import InMemoryV2Repository

OWNER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


async def _active_change(repo: InMemoryV2Repository):
    project, _ = await repo.create_project(
        OWNER, uuid.uuid4(), "Generation test", "new_idea", None, None
    )
    repo.activate_project_for_test(OWNER, project.ref.project_id)
    change, _ = await repo.start_current_change(
        OWNER,
        project.ref.project_id,
        project.version,
        uuid.uuid4(),
        None,
        "build",
        "Add a durable result",
    )
    return project, change


def _start_request(change_id, version, command_id=None):
    return StartGenerationAttemptRequest(
        command_id=command_id or uuid.uuid4(),
        target_current_change_id=change_id,
        purpose="prompt_draft",
        target_aggregate_version=version,
        policy_version="test-policy-v1",
        config_version="test-config-v1",
        provider_key="stub-provider",
        model_key="stub-model",
        input_sha256="a" * 64,
    )


def test_generated_prompt_draft_is_applied_atomically_and_retry_is_idempotent():
    async def scenario():
        repo = InMemoryV2Repository()
        project, change = await _active_change(repo)
        change = repo.resolve_policy_for_test(OWNER, project.ref.project_id, change.id)
        project, change = await repo.update_coding_agent(
            OWNER, project.ref.project_id, change.id, project.version, change.version, "codex"
        )
        command_id = uuid.uuid4()
        request = _start_request(change.id, change.version, command_id)
        started, replayed = await v2_generation_service.start_attempt(
            repo, OWNER, project.ref.project_id, request
        )
        assert started.status.value == "pending"
        assert replayed is False
        retry, replayed = await v2_generation_service.start_attempt(
            repo, OWNER, project.ref.project_id, request
        )
        assert retry.id == started.id
        assert replayed is True
        conflicting = request.model_copy(update={"model_key": "different-model"})
        try:
            await v2_generation_service.start_attempt(
                repo, OWNER, project.ref.project_id, conflicting
            )
        except V2ConflictError:
            pass
        else:
            raise AssertionError("changed generation inputs reused one command identity")

        application = ApplyGeneratedPromptDraftRequest(
            expected_attempt_version=started.version,
            expected_current_change_version=change.version,
            expected_prompt_draft_version=change.prompt_draft_version,
            prompt_text="Generated draft candidate",
            done_condition="The generated behavior is observable",
            boundaries=["Keep existing behavior"],
        )
        finished = await v2_generation_service.apply_prompt_draft(
            repo,
            OWNER,
            project.ref.project_id,
            started.id,
            application,
        )
        assert finished.applied is True
        assert finished.replayed is False
        assert finished.generation_attempt.status.value == "succeeded"
        assert finished.generation_attempt.result_record_type == "prompt_draft"
        assert finished.generation_attempt.result_record_id == change.id
        assert finished.current_change.version == change.version + 1
        assert finished.current_change.prompt_draft == "Generated draft candidate"
        assert finished.current_change.lifecycle_state == change.lifecycle_state
        assert finished.current_change.resume_step == change.resume_step
        assert finished.current_change.latest_prompt_version_id is None

        replay = await v2_generation_service.apply_prompt_draft(
            repo,
            OWNER,
            project.ref.project_id,
            started.id,
            application,
        )
        assert replay.applied is True
        assert replay.replayed is True
        assert replay.current_change.version == finished.current_change.version
        assert replay.generation_attempt.version == finished.generation_attempt.version

        durable = await repo.get_current_change_by_id(
            OWNER, project.ref.project_id, change.id
        )
        assert durable is not None
        assert durable.lifecycle_state == change.lifecycle_state
        assert durable.resume_step == change.resume_step
        assert durable.version == change.version + 1
        assert durable.latest_prompt_version_id is None

    asyncio.run(scenario())


def test_generation_success_is_superseded_when_referenced_state_changed():
    async def scenario():
        repo = InMemoryV2Repository()
        project, change = await _active_change(repo)
        change = repo.resolve_policy_for_test(OWNER, project.ref.project_id, change.id)
        project, change = await repo.update_coding_agent(
            OWNER, project.ref.project_id, change.id, project.version, change.version, "codex"
        )
        started, _ = await v2_generation_service.start_attempt(
            repo, OWNER, project.ref.project_id, _start_request(change.id, change.version)
        )
        changed = await repo.update_prompt_draft(
            OWNER,
            project.ref.project_id,
            change.id,
            change.version,
            change.prompt_draft_version,
            "Independent student edit",
            None,
            [],
            "normal",
            None,
            RISK_POLICY_VERSION,
            risk_input_fingerprint(
                change.goal_snapshot, None, [], "Independent student edit"
            ),
        )
        finished = await v2_generation_service.apply_prompt_draft(
            repo,
            OWNER,
            project.ref.project_id,
            started.id,
            ApplyGeneratedPromptDraftRequest(
                expected_attempt_version=started.version,
                expected_current_change_version=change.version,
                expected_prompt_draft_version=change.prompt_draft_version,
                prompt_text="Late provider result",
            ),
        )
        assert finished.applied is False
        assert finished.replayed is False
        assert finished.generation_attempt.status.value == "superseded"
        assert finished.generation_attempt.result_record_type is None
        assert finished.generation_attempt.result_record_id is None
        assert finished.current_change.version == changed.version
        assert finished.current_change.prompt_draft == "Independent student edit"

    asyncio.run(scenario())


def test_generated_prompt_atomic_application_rolls_back_on_invalid_result():
    async def scenario():
        repo = InMemoryV2Repository()
        project, change = await _active_change(repo)
        change = repo.resolve_policy_for_test(OWNER, project.ref.project_id, change.id)
        project, change = await repo.update_coding_agent(
            OWNER, project.ref.project_id, change.id, project.version, change.version, "codex"
        )
        started, _ = await v2_generation_service.start_attempt(
            repo, OWNER, project.ref.project_id, _start_request(change.id, change.version)
        )
        try:
            await repo.apply_generated_prompt_draft(
                OWNER,
                project.ref.project_id,
                started.id,
                started.version,
                change.version,
                change.prompt_draft_version,
                "   ",
                None,
                [],
            )
        except V2RepositoryInvalidState:
            pass
        else:
            raise AssertionError("invalid generated prompt unexpectedly applied")

        durable = await repo.get_current_change_by_id(
            OWNER, project.ref.project_id, change.id
        )
        pending = repo._generation_attempts[started.id][1]
        assert durable is not None
        assert durable.prompt_draft is None
        assert durable.version == change.version
        assert pending.status.value == "pending"
        assert pending.version == started.version

    asyncio.run(scenario())


def test_generation_failure_records_only_safe_operational_metadata():
    async def scenario():
        repo = InMemoryV2Repository()
        project, change = await _active_change(repo)
        started, _ = await v2_generation_service.start_attempt(
            repo, OWNER, project.ref.project_id, _start_request(change.id, change.version)
        )
        failed = await v2_generation_service.finish_attempt(
            repo,
            OWNER,
            project.ref.project_id,
            started.id,
            FinishGenerationAttemptRequest(
                expected_attempt_version=started.version,
                status="failed",
                safe_error_category="provider_unavailable",
                retryable=True,
            ),
        )
        assert failed.status.value == "failed"
        assert failed.safe_error_category == "provider_unavailable"
        assert failed.retryable is True
        assert failed.result_record_id is None

    asyncio.run(scenario())


def test_generation_contract_cannot_name_project_fact_as_a_result():
    try:
        FinishGenerationAttemptRequest(
            expected_attempt_version=1,
            status="succeeded",
            result_record_type="project_fact",
            result_record_id=uuid.uuid4(),
        )
    except ValueError:
        return
    raise AssertionError("Project Fact provenance must not be accepted")


def test_generic_generation_finish_cannot_claim_separately_applied_prompt_draft():
    try:
        FinishGenerationAttemptRequest(
            expected_attempt_version=1,
            status="succeeded",
            result_record_type="prompt_draft",
            result_record_id=uuid.uuid4(),
        )
    except ValueError:
        return
    raise AssertionError("prompt drafts must use the atomic application command")
