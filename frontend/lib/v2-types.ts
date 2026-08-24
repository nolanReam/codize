export type V2LifecycleState =
  | "draft"
  | "temporary_recovery"
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
  | "confirm_change"
  | "intervention"
  | "choose_agent"
  | "edit_prompt"
  | "choose_effort"
  | "review_prompt"
  | "ready_to_handoff"
  | "waiting_for_return"
  | "report_return_outcome"
  | "perform_check"
  | "propose_check"
  | "check_unsure"
  | "check_failed"
  | "recovery_symptom"
  | "recovery_investigate"
  | "recovery_investigation_handoff"
  | "recovery_investigation_return"
  | "recovery_correct"
  | "recovery_correction_handoff"
  | "recovery_correction_return"
  | "recovery_recheck"
  | "understand"
  | "ready_to_complete";
export type CheckResult = "worked" | "partly_worked" | "did_not_work" | "unsure";

export interface ProjectRefView {
  workflow_version: "v1" | "v2";
  project_id: string;
  display_name: string;
  open_mode: "legacy_active_only" | "explicit";
  lifecycle_state: V2LifecycleState | null;
  setup_resume_step: string | null;
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
  teaching_mode: "skip" | "ask" | "remind" | "teach";
  teaching_target: string | null;
  policy_resolved: boolean;
  risk: "normal" | "slowdown";
  risk_reason_key: string | null;
  check_requirement: "required" | "waived";
  help_context_key: string | null;
  support_level_disclosed: "none" | "nudge" | "clue" | "teach";
  student_return_outcome: "worked" | "broken" | "unsure" | null;
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
  active_check: CheckView | null;
  last_check_result: CheckResult | null;
  teaching: TeachingInteractionView | null;
  effort_feedback: EffortFeedbackView | null;
  learner_statuses: Record<string, "new" | "guided" | "practiced" | "recently_independent">;
  verification_plan_source: "codize" | "student";
  recovery_case: RecoveryCaseView | null;
}

export interface TeachingInteractionView {
  context: "prebuild" | "verification" | "understanding" | "recovery_symptom"
    | "recovery_investigate" | "recovery_correct" | "recovery_recheck";
  competency_key: string;
  mode: "skip" | "ask" | "remind" | "teach";
  risk: "normal" | "slowdown";
  risk_reason_key: string | null;
  title: string;
  explanation: string | null;
  example: string | null;
  question: string | null;
  reminder: string | null;
  hint_level: "none" | "nudge" | "clue" | "teach";
  hint_text: string | null;
  can_request_help: boolean;
}

export interface EffortFeedbackView {
  selected: EffortCategory;
  recommended: EffortCategory | null;
  appropriate: boolean;
  retry_allowed: boolean;
  revealed: boolean;
  message: string;
}

export interface CheckView {
  id: string;
  current_change_id: string;
  check_plan: string;
  plan_source: "codize" | "student";
  status: "proposed" | "performed" | "not_run";
  result: CheckResult | null;
  student_observation: string | null;
  performed_at: string | null;
  version: number;
}

export interface RecoveryCaseView {
  id: string;
  current_change_id: string;
  status: "open" | "investigating" | "correcting" | "rechecking" | "resolved" | "abandoned";
  intended_behavior: string;
  observed_symptom: string;
  last_known_working_statement: string | null;
  last_known_working_certainty: "yes" | "no" | "unsure";
  candidate_change_summary: string | null;
  student_hypothesis: string | null;
  proposed_first_check: string | null;
  investigation_finding: string | null;
  investigation_finding_provenance: "agent_claimed" | null;
  cause_summary: string | null;
  correction_summary: string | null;
  resolution_summary: string | null;
  opened_at: string;
  resolved_at: string | null;
  version: number;
}

export interface RecoveryCommandResponse {
  current_change: CurrentChangeView;
  recovery_case: RecoveryCaseView;
  check: CheckView | null;
  next_check: CheckView | null;
  prompt_version: PromptVersionView | null;
  exact_prompt: string | null;
  replayed: boolean;
}

export interface UserPreferencesView {
  dialogue_sound_enabled: boolean;
  motion_preference: "system" | "full" | "reduced";
  version: number;
}

export interface RecentChangeView {
  id: string;
  goal: string;
  completed_at: string;
  check_plan: string;
  observation: string;
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
