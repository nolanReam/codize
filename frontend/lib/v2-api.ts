import { request } from "./api";
import type {
  BuildResumeState,
  CodingAgentChoice,
  CodingAgentSelectionResponse,
  CheckResult,
  CheckView,
  CurrentChangeResponse,
  CurrentChangeView,
  EffortCategory,
  PlanResponse,
  ProjectRefView,
  RecentChangeView,
  PromptHandoffResponse,
  PromptVersionView,
  V2ProjectView,
  UserPreferencesView,
} from "./v2-types";

const v2 = (path: string) => `/v2${path}`;

export const createV2Project = (displayName: string, creationIntent: "new_idea" | "already_building", commandId: string) =>
  request<{ project: V2ProjectView; replayed: boolean }>(v2("/projects"), {
    method: "POST", body: { workflow_version: "v2", command_id: commandId,
      display_name: displayName, creation_intent: creationIntent },
  });
export const establishManualProject = (
  projectId: string, projectVersion: number, commandId: string, projectContext: string,
  planItemId: string, changeLabel: string, doneCondition: string
) => request<{ project: V2ProjectView; plan_item: import("./v2-types").PlanItemView; replayed: boolean }>(
  v2(`/projects/${encodeURIComponent(projectId)}/manual-setup`), { method: "POST", body: {
    workflow_version: "v2", command_id: commandId, expected_project_version: projectVersion,
    project_context: projectContext, plan_item_id: planItemId, change_label: changeLabel,
    done_condition: doneCondition,
  }});
export const startCurrentChange = (projectId: string, projectVersion: number,
  planItemId: string, goal: string, commandId = crypto.randomUUID()) =>
  request<CurrentChangeResponse>(v2(`/projects/${encodeURIComponent(projectId)}/current-change`), {
    method: "POST", body: { workflow_version: "v2", command_id: commandId,
      expected_project_version: projectVersion, plan_item_id: planItemId,
      change_kind: "build", goal_snapshot: goal },
  });
export const confirmCurrentChange = (projectId: string, changeId: string,
  changeVersion: number, commandId = crypto.randomUUID()) =>
  request<CurrentChangeResponse>(v2(`/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/confirm`), {
    method: "POST", body: { workflow_version: "v2", command_id: commandId,
      expected_current_change_version: changeVersion },
  });

export const getProjectRefs = () =>
  request<{ projects: ProjectRefView[] }>(v2("/project-refs"));
export const getV2Project = (projectId: string) =>
  request<V2ProjectView>(v2(`/projects/${encodeURIComponent(projectId)}`));
export const getV2Plan = (projectId: string) =>
  request<PlanResponse>(v2(`/projects/${encodeURIComponent(projectId)}/plan`));
export const getRecentChanges = (projectId: string) =>
  request<{ recent_changes: RecentChangeView[] }>(
    v2(`/projects/${encodeURIComponent(projectId)}/recent-changes`));
export const getCurrentChange = (projectId: string) =>
  request<CurrentChangeResponse>(
    v2(`/projects/${encodeURIComponent(projectId)}/current-change`)
  );
export const getBuildState = (projectId: string, changeId: string) =>
  request<BuildResumeState>(
    v2(
      `/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/build-state`
    )
  );

export const selectCodingAgent = (
  projectId: string,
  changeId: string,
  choice: CodingAgentChoice,
  projectVersion: number,
  changeVersion: number
) =>
  request<CodingAgentSelectionResponse>(
    v2(
      `/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/coding-agent`
    ),
    {
      method: "PUT",
      body: {
        workflow_version: "v2",
        expected_project_version: projectVersion,
        expected_current_change_version: changeVersion,
        choice,
      },
    }
  );

export const updatePromptDraft = (
  projectId: string,
  changeId: string,
  changeVersion: number,
  draftVersion: number,
  promptText: string,
  doneCondition: string | null,
  boundaries: string[]
) =>
  request<CurrentChangeView>(
    v2(
      `/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/prompt-draft`
    ),
    {
      method: "PUT",
      body: {
        workflow_version: "v2",
        expected_current_change_version: changeVersion,
        expected_prompt_draft_version: draftVersion,
        prompt_text: promptText,
        done_condition: doneCondition,
        boundaries,
      },
    }
  );

export const selectEffort = (
  projectId: string,
  changeId: string,
  effort: EffortCategory,
  changeVersion: number
) =>
  request<CurrentChangeView>(
    v2(
      `/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/effort`
    ),
    {
      method: "PUT",
      body: {
        workflow_version: "v2",
        expected_current_change_version: changeVersion,
        effort,
      },
    }
  );

export const acceptPrompt = (
  projectId: string,
  changeId: string,
  changeVersion: number,
  draftVersion: number
) =>
  request<{ current_change: CurrentChangeView; prompt_version: PromptVersionView; replayed: boolean }>(
    v2(
      `/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/prompt-versions`
    ),
    {
      method: "POST",
      body: {
        workflow_version: "v2",
        command_id: crypto.randomUUID(),
        expected_current_change_version: changeVersion,
        expected_prompt_draft_version: draftVersion,
      },
    }
  );

export const handoffPrompt = (
  projectId: string,
  changeId: string,
  promptVersionId: string,
  changeVersion: number,
  promptVersion: number
) =>
  request<PromptHandoffResponse>(
    v2(
      `/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/handoff`
    ),
    {
      method: "POST",
      body: {
        workflow_version: "v2",
        command_id: crypto.randomUUID(),
        prompt_version_id: promptVersionId,
        expected_current_change_version: changeVersion,
        expected_prompt_version: promptVersion,
      },
    }
  );

export const recordReturn = (projectId: string, changeId: string, changeVersion: number,
  outcome: "worked" | "broken" | "unsure", checkId: string | null) =>
  request<{ current_change: CurrentChangeView; check: CheckView | null; replayed: boolean }>(
    v2(`/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/return`), {
      method: "POST", body: { workflow_version: "v2", command_id: crypto.randomUUID(),
        expected_current_change_version: changeVersion, outcome, check_id: checkId },
    });
export const recordCheck = (projectId: string, changeId: string, checkId: string,
  changeVersion: number, checkVersion: number, result: CheckResult,
  observation: string, nextCheckId: string | null) =>
  request<{ current_change: CurrentChangeView; check: CheckView; next_check: CheckView | null; replayed: boolean }>(
    v2(`/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/checks/${encodeURIComponent(checkId)}`), {
      method: "POST", body: { workflow_version: "v2", command_id: crypto.randomUUID(),
        expected_current_change_version: changeVersion, expected_check_version: checkVersion,
        result, observation, performed_by_student: true, next_check_id: nextCheckId },
    });
export const completeCurrentChange = (projectId: string, changeId: string,
  changeVersion: number, planVersion: number, planItemVersion: number) =>
  request<{ current_change: CurrentChangeView; project: V2ProjectView; plan: PlanResponse;
    check: CheckView; replayed: boolean }>(
    v2(`/projects/${encodeURIComponent(projectId)}/current-change/${encodeURIComponent(changeId)}/complete`), {
      method: "POST", body: { workflow_version: "v2", command_id: crypto.randomUUID(),
        expected_current_change_version: changeVersion, expected_plan_version: planVersion,
        expected_plan_item_version: planItemVersion },
    });
export const getPreferences = () => request<UserPreferencesView>(v2("/preferences"));
export const updateDialogueSound = (expectedVersion: number, enabled: boolean) =>
  request<UserPreferencesView>(v2("/preferences/dialogue-sound"), {
    method: "PUT", body: { expected_version: expectedVersion, dialogue_sound_enabled: enabled },
  });
