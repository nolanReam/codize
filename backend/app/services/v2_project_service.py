"""V2 Project application service and the narrow V1/V2 compatibility seam."""

from __future__ import annotations

from uuid import UUID

from app.domain.v2 import ProjectRef, V2Project
from app.schemas.v2 import (
    CreateProjectRequest,
    ProjectCommandResponse,
    ProjectRefIdentityView,
    ProjectRefsResponse,
    ProjectRefView,
    PurgeProjectResponse,
    V2ProjectView,
)
from app.services.project_repository import ProjectRepository
from app.services.v2_errors import V2ConflictError, V2NotFoundError
from app.services.v2_repository import (
    V2Repository,
    V2RepositoryConflict,
    V2RepositoryInvalidState,
    V2RepositoryNotFound,
)


def project_view(project: V2Project) -> V2ProjectView:
    project.ref.require_v2()
    return V2ProjectView(
        project_id=project.ref.project_id,
        display_name=project.display_name,
        lifecycle_state=project.lifecycle_state,
        setup_resume_step=project.setup_resume_step,
        coding_agent_key=project.coding_agent_key,
        plan_version=project.plan_version,
        version=project.version,
        first_version_completed_at=project.first_version_completed_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def require_v2_reference(ref: ProjectRef) -> None:
    """Compatibility guard for future callers that operate on ProjectRef unions."""
    try:
        ref.require_v2()
    except ValueError as exc:
        from app.services.v2_errors import V2InvalidRequestError

        raise V2InvalidRequestError("A V2 operation requires workflow_version v2.") from exc


async def create_project(
    repo: V2Repository,
    owner_user_id: str,
    request: CreateProjectRequest,
) -> ProjectCommandResponse:
    try:
        recovery_context = getattr(request, "recovery_context", None)
        project, replayed = await repo.create_project(
            owner_user_id,
            request.command_id,
            request.display_name,
            request.creation_intent,
            recovery_context.model_dump(mode="json") if recovery_context else None,
            getattr(request, "current_change_command_id", None),
        )
    except V2RepositoryConflict as exc:
        raise V2ConflictError("This Project creation command conflicts with an earlier request.") from exc
    except V2RepositoryInvalidState as exc:
        raise V2ConflictError("The V2 Project could not be created in its requested state.") from exc
    return ProjectCommandResponse(project=project_view(project), replayed=replayed)


async def get_project(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
) -> V2ProjectView:
    project = await repo.get_project(owner_user_id, project_id)
    if project is None:
        raise V2NotFoundError("V2 Project not found.")
    return project_view(project)


async def list_project_refs(
    v2_repo: V2Repository,
    legacy_repo: ProjectRepository,
    owner_user_id: str,
) -> ProjectRefsResponse:
    refs: list[ProjectRefView] = []

    # V1 can truthfully open only its maintained active/newest row. Reuse that
    # exact adapter behavior and never enumerate arbitrary legacy rows.
    legacy = await legacy_repo.get_project(owner_user_id)
    if legacy is not None:
        try:
            legacy_id = UUID(str(legacy["id"]))
        except (KeyError, TypeError, ValueError):
            legacy_id = None
        if legacy_id is not None:
            refs.append(
                ProjectRefView(
                    workflow_version="v1",
                    project_id=legacy_id,
                    display_name="Legacy Codize project",
                    open_mode="legacy_active_only",
                )
            )

    refs.extend(
        ProjectRefView(
            workflow_version="v2",
            project_id=project.ref.project_id,
            display_name=project.display_name,
            open_mode="explicit",
        )
        for project in await v2_repo.list_projects(owner_user_id)
    )
    return ProjectRefsResponse(projects=refs)


async def promote_temporary_project(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    expected_project_version: int,
    command_id: UUID,
) -> ProjectCommandResponse:
    try:
        project, replayed = await repo.promote_temporary_project(
            owner_user_id,
            project_id,
            expected_project_version,
            command_id,
        )
    except V2RepositoryNotFound as exc:
        raise V2NotFoundError("V2 Project not found.") from exc
    except (V2RepositoryConflict, V2RepositoryInvalidState) as exc:
        raise V2ConflictError("The temporary Project changed or cannot be promoted.") from exc
    return ProjectCommandResponse(project=project_view(project), replayed=replayed)


async def purge_temporary_project(
    repo: V2Repository,
    owner_user_id: str,
    project_id: UUID,
    expected_project_version: int,
) -> PurgeProjectResponse:
    try:
        await repo.purge_temporary_project(
            owner_user_id,
            project_id,
            expected_project_version,
        )
    except V2RepositoryConflict as exc:
        raise V2ConflictError("The temporary Project changed. Reload before discarding it.") from exc
    except V2RepositoryInvalidState as exc:
        raise V2ConflictError("Only a temporary Recovery Project can be discarded here.") from exc
    # The approved purge primitive intentionally returns the same success for
    # absence and cross-owner mismatch. The response contains only caller-
    # supplied identity, so it cannot disclose whether the Project existed.
    return PurgeProjectResponse(
        project_ref=ProjectRefIdentityView(
            workflow_version="v2",
            project_id=project_id,
        )
    )
