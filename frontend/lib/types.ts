// Response shapes of the FastAPI backend (see backend/README.md). These
// mirror the routes as-built — do not invent fields the backend doesn't send.

export interface IntakeQuestion {
  number: number;
  key: string;
  text: string;
  options?: string[];
}

export interface IntakeStatus {
  started: boolean;
  completed: boolean;
  answered_questions: number[];
  next_question: number | null;
  archetype_id: number | null;
  answers: Record<string, string | null> | null;
}

export interface IntakeCompleteResult {
  completed: boolean;
  archetype_id: number;
  archetype_name: string;
}

export interface TaskEntry {
  task_id: string;
  description: string;
  completed: boolean;
}

export interface PhaseView {
  phase: number;
  phase_title: string;
  core_concept: string;
  ai_appropriate_tasks: TaskEntry[];
  human_required_tasks: TaskEntry[];
  explanation_gate_targets: string[];
  gate_depth: string;
  unlock_condition: string;
  functional_unlock: string;
  is_current: boolean;
  completed_task_count: number;
  total_task_count: number;
}

export interface PhaseSummary {
  phase: number;
  phase_title: string;
  gate_depth: string;
  is_current: boolean;
  completed_task_count: number;
  total_task_count: number;
}

export interface PhaseList {
  current_phase: number;
  phases: PhaseSummary[];
}

// --- workflow artifacts (M13B) ---------------------------------------------

export type WorkflowSectionName =
  | "prompt_builder"
  | "review_board"
  | "evidence"
  | "verification";

export interface PromptBuilderArtifact {
  inputs: Record<string, string>;
  generated_prompt: string;
  why_stronger?: string | null;
  bad_prompt_comparison?: string | null;
  saved_at?: string;
}

export interface ReviewBoardArtifact {
  files_changed: string[];
  ai_generated?: string | null;
  accepted?: string | null;
  rejected?: string | null;
  edited_manually?: string | null;
  ai_assumptions?: string | null;
  least_confident?: string | null;
  out_of_scope_changes?: string | null;
  saved_at?: string;
}

export type EvidenceKind =
  | "repo_url"
  | "commit_hash"
  | "changed_files"
  | "terminal_output"
  | "test_output"
  | "screenshot_note"
  | "app_url"
  | "api_response"
  | "note";

export interface EvidenceEntry {
  kind: EvidenceKind;
  content: string;
}

export interface EvidenceArtifact {
  entries: EvidenceEntry[];
  summary?: string | null;
  saved_at?: string;
}

export type VerificationCheckId =
  | "app_runs_locally"
  | "smoke_test"
  | "api_route_checked"
  | "ui_flow_checked"
  | "failure_case_tested"
  | "auth_boundary_checked"
  | "secret_exposure_checked"
  | "rls_wrong_user_checked";

export type VerificationResult = "pass" | "fail" | "skipped" | "not_applicable";

export interface VerificationCheck {
  check: VerificationCheckId;
  result: VerificationResult;
  note?: string | null;
}

export interface VerificationArtifact {
  checks: VerificationCheck[];
  explanation?: string | null;
  saved_at?: string;
}

export interface WorkflowSections {
  prompt_builder: PromptBuilderArtifact | null;
  review_board: ReviewBoardArtifact | null;
  evidence: EvidenceArtifact | null;
  verification: VerificationArtifact | null;
}

export interface WorkflowPhaseState {
  phase: number;
  sections: WorkflowSections;
}

// --- reconnection / evaluation / gate ---------------------------------------

export interface ReconnectionSummary {
  intake_purpose: string;
  current_phase: number;
  phase_title: string;
  phase_reminder: string;
  incomplete_tasks: { task_id: string; description: string }[];
  last_gate_summary: string | null;
  unlocks: UnlockView[];
  next_action: string;
}

export interface ReconnectionState {
  reconnection_needed: boolean;
  state: "new_user" | "recently_active" | "workspace_not_ready" | "reconnection";
  summary?: ReconnectionSummary;
}

export interface UnlockView {
  id: string;
  unlock_key: string;
  project_id: string;
  phase: number;
  description: string;
  unlocked_at: string;
}

export type EvaluationStateName =
  | "not_started"
  | "intake_needed"
  | "roadmap_needed"
  | "in_progress"
  | "gate_ready"
  | "cooldown"
  | "complete";

export interface Evaluation {
  state: EvaluationStateName;
  project_status: string | null;
  next_action: string;
  current_phase?: number;
  phase_title?: string;
  total_phases?: number;
  completed_phases?: number;
  completed_task_count?: number;
  total_task_count?: number;
  incomplete_tasks?: { task_id: string; description: string }[];
  recent_gate?: { outcome: "passed" | "failed" | "in_progress"; summary: string | null } | null;
  unlocks?: UnlockView[];
  cooldown_seconds_remaining?: number;
}

export interface GateTurn {
  turn: number;
  question: string;
  answer: string | null;
}

export type GateNextAction = "turn1" | "turn2" | "turn3" | "evaluate";

export interface GateCurrent {
  phase: number;
  phase_title: string;
  state: "not_started" | "in_progress" | "cooldown" | "passed";
  anchor_prompt?: string;
  reason?: string | null;
  cooldown_seconds_remaining?: number;
  gate_session_id?: string;
  next_action?: GateNextAction;
  anchor_statement?: string | null;
  turns?: GateTurn[];
}

export interface GateStartResult {
  gate_session_id: string;
  phase: number;
  phase_title: string;
  anchor_prompt: string;
}

export interface GateTurnResult {
  gate_session_id: string;
  turn: number;
  question: string;
}

export interface GateEvaluationResult {
  gate_session_id: string;
  phase: number;
  verdict: "PASS" | "FAIL";
  reason: string;
  current_phase: number;
  new_unlocks?: UnlockView[];
  cooldown_seconds?: number;
}
