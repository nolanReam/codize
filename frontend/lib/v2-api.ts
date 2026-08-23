import { request } from "./api";
import type {
  BuildResumeState,
  CodingAgentChoice,
  CodingAgentSelectionResponse,
  CurrentChangeResponse,
  CurrentChangeView,
  EffortCategory,
  PlanResponse,
  ProjectRefView,
  PromptHandoffResponse,
  PromptVersionView,
  V2ProjectView,
} from "./v2-types";

const v2 = (path: string) => `/v2${path}`;

export const getProjectRefs = () =>
  request<{ projects: ProjectRefView[] }>(v2("/project-refs"));
export const getV2Project = (projectId: string) =>
  request<V2ProjectView>(v2(`/projects/${encodeURIComponent(projectId)}`));
export const getV2Plan = (projectId: string) =>
  request<PlanResponse>(v2(`/projects/${encodeURIComponent(projectId)}/plan`));
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
