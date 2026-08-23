export type V2LifecycleState =
  | "draft"
  | "temp"
  | "active"
  | "archived"
  | "deletion_pending";

export type CodingAgentKey =
  | "codex"
  | "claude_code"
  | "cursor"
  | "chatgpt"
  | "replit"
  | "other";

export type CodingAgentChoice = CodingAgentKey | "help_me_choose";
export type EffortCategory = "quick" | "standard" | "deep";
export type BuildStage =
  | "choose_agent"
  | "edit_prompt"
  | "choose_effort"
  | "review_prompt"
  | "ready_to_handoff"
  | "waiting_for_return";

export interface ProjectRefView {
  workflow_version: "v1" | "v2";
  project_id: string;
  display_name: string;
  open_mode: "legacy_active_only" | "explicit";
}

export interface V2ProjectView {
  workflow_version: "v2";
  project_id: string;
  display_name: string;
  lifecycle_state: V2LifecycleState;
  setup_resume_step: string;
  coding_agent_key: string | null;
  plan_version: number;
  version: number;
  first_version_completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlanItemView {
  id: string;
  label: string;
  intended_outcome: string | null;
  scope_band: "first_version" | "later";
  status: "proposed" | "ready" | "deferred" | "done" | "removed";
  order_key: number;
  version: number;
  completed_at: string | null;
  terminal_current_change_id: string | null;
}

export interface PlanResponse {
  workflow_version: "v2";
  project_id: string;
  project_version: number;
  plan_version: number;
  items: PlanItemView[];
  replayed: boolean;
}

export interface CurrentChangeView {
  id: string;
  workflow_version: "v2";
  project_id: string;
  plan_item_id: string | null;
  change_kind: "build" | "recovery";
  lifecycle_state: string;
  resume_step: string | null;
  resume: {
    lifecycle_state: string;
    resume_step: string | null;
    available_commands: Array<"cancel">;
  };
  goal_snapshot: string;
  done_condition_snapshot: string | null;
  boundary_snapshots: string[];
  prompt_draft: string | null;
  prompt_draft_version: number;
  coding_agent_key: CodingAgentKey | null;
  effort_category: EffortCategory | null;
  latest_prompt_version_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  cancelled_at: string | null;
}

export interface CurrentChangeResponse {
  current_change: CurrentChangeView | null;
  replayed: boolean;
}

export interface PromptVersionView {
  id: string;
  current_change_id: string;
  ordinal: number;
  purpose: string;
  content: string;
  coding_agent_key: CodingAgentKey;
  effort_category: EffortCategory | null;
  accepted_at: string;
  handed_off_at: string | null;
  version: number;
}

export interface AgentMetadataView {
  key: CodingAgentKey;
  display_name: string;
  reasoning_controls_known: boolean;
  mapping_available: boolean;
  stale_fallback: string;
}

export interface BuildResumeState {
  workflow_version: "v2";
  project_id: string;
  current_change_id: string;
  lifecycle_state: string;
  resume_step: string | null;
  build_stage: BuildStage;
  selected_agent: AgentMetadataView | null;
  prompt_draft: string | null;
  prompt_draft_version: number;
  effort_category: EffortCategory | null;
  structured_decisions: {
    intended_result: string | null;
    done_condition: string | null;
    boundaries: string[];
    coding_agent_key: CodingAgentKey | null;
  };
  accepted_prompt_version: PromptVersionView | null;
  ready_to_handoff: boolean;
  exact_handoff_prompt: string | null;
  current_change_version: number;
}

export interface CodingAgentSelectionResponse {
  workflow_version: "v2";
  project_id: string;
  current_change_id: string;
  project_version: number;
  current_change_version: number;
  selected_agent: AgentMetadataView | null;
  guidance_required: boolean;
}

export interface PromptHandoffResponse {
  current_change: CurrentChangeView;
  prompt_version: PromptVersionView;
  exact_prompt: string;
  replayed: boolean;
}
