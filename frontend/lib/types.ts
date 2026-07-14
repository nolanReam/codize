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
  | "verification"
  | "implementation_import";

export interface PromptBuilderArtifact {
  inputs: Record<string, string>;
  generated_prompt: string;
  why_stronger?: string | null;
  bad_prompt_comparison?: string | null;
  saved_at?: string;
}

// Legacy/manual Review fields (M13B). M16A.1 keeps this exact shape valid and
// adds a linked variant rather than converting or replacing old artifacts.
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

// Linked Review (M16A.1 backend / M16A.2 UI). Change Map source fields are
// server-owned snapshots; only the decision, rationale, and revision are
// writable through ReviewTargetUpdate.
export type ReviewDecision =
  | "pending"
  | "keep"
  | "revise"
  | "remove"
  | "needs_verification"
  | "uncertain";

export type ReviewSourceCategory = ChangeMapCategory;
export type ReviewSourceOrigin = ChangeMapOrigin;
export type ReviewSourceChangeMapDecision = ChangeMapStudentDecision;
export type ReviewSourceResolution = "confirmed" | "unresolved";

export interface ReviewSourceBinding {
  source_change_map_confirmed_at: string;
  source_change_map_generated_at: string;
}

export interface ReviewServerState {
  initialized_from_change_map: true;
  stale: boolean;
}

export interface LinkedReviewTarget {
  review_target_id: string;
  change_map_item_id: string;
  change_map_category: ReviewSourceCategory;
  change_map_origin: ReviewSourceOrigin;
  change_map_student_decision: ReviewSourceChangeMapDecision;
  change_text: string;
  source_resolution: ReviewSourceResolution;
  review_decision: ReviewDecision;
  student_rationale: string | null;
  student_revision: string | null;
}

export interface LinkedReviewBoardArtifact
  extends ReviewBoardArtifact,
    ReviewSourceBinding,
    ReviewServerState {
  review_targets: LinkedReviewTarget[];
}

export type StoredReviewBoardArtifact = ReviewBoardArtifact | LinkedReviewBoardArtifact;

export interface ReviewInitializationRequest {
  replace_existing?: true;
}

export interface ReviewTargetUpdate {
  review_target_id: string;
  review_decision: ReviewDecision;
  student_rationale: string | null;
  student_revision: string | null;
}

// Every manual field has a backend default. Linked saves normally send only
// target_updates; manual Review continues to send its established fields.
export interface ReviewBoardSaveRequest
  extends Partial<Omit<ReviewBoardArtifact, "saved_at">> {
  target_updates?: ReviewTargetUpdate[];
}

export interface ReviewInitializationResponse {
  phase: number;
  section: "review_board";
  artifact: LinkedReviewBoardArtifact;
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

// Linked Verification (M16B.1 backend / M16B.2 UI). Review provenance,
// source snapshots, suggestions, bindings, and stale state are server-owned.
// The browser may update only student_check, result, and result_notes through
// VerificationTargetUpdateRequest.
export type VerificationSourceCategory =
  | "behavior_change"
  | "implementation_decision"
  | "out_of_scope_change"
  | "security_sensitive_area"
  | "unresolved_risk"
  | "unverified_behavior";

export interface VerificationReviewBinding {
  source_change_map_generated_at: string;
  source_change_map_confirmed_at: string;
  review_saved_at: string;
  review_target_fingerprint: string;
}

export interface VerificationServerState {
  initialized_from_review: true;
  stale: boolean;
}

export interface LinkedVerificationTarget {
  verification_target_id: string;
  review_target_id: string;
  change_map_item_id: string;
  category: VerificationSourceCategory;
  source_text: string;
  source_rationale: string | null;
  suggested_check: string;
  student_check: string | null;
  result: VerificationResult | null;
  result_notes: string | null;
}

export interface LinkedVerificationArtifact
  extends VerificationArtifact,
    VerificationServerState {
  initialized_at: string;
  source_review_binding: VerificationReviewBinding;
  verification_targets: LinkedVerificationTarget[];
}

export type ZeroTargetLinkedVerificationArtifact = LinkedVerificationArtifact & {
  verification_targets: [];
};

export type StoredVerificationArtifact = VerificationArtifact | LinkedVerificationArtifact;

export interface VerificationInitializationRequest {
  replace_existing?: true;
}

export interface VerificationInitializationResponse {
  phase: number;
  section: "verification";
  artifact: LinkedVerificationArtifact;
}

export interface VerificationTargetUpdateRequest {
  verification_target_id: string;
  student_check: string | null;
  result: VerificationResult | null;
  result_notes: string | null;
}

// Manual Verification keeps its full-section payload. Linked Verification
// sends target_updates only; every field on each update is student-owned.
export interface VerificationSaveRequest
  extends Partial<Omit<VerificationArtifact, "saved_at">> {
  target_updates?: VerificationTargetUpdateRequest[];
}

// "Bring Back What AI Changed" (M15A backend / M15B UI). Student-provided,
// self-reported material — never verified, never proof of correctness.
export type ImplementationImportSourceKind =
  | "ai_response"
  | "git_diff"
  | "changed_files"
  | "code_snippet"
  | "manual_summary"
  | "other";

export interface ImplementationImportArtifact {
  source_kind: ImplementationImportSourceKind;
  content?: string | null;
  changed_files: string[];
  student_summary?: string | null;
  tool_name?: string | null;
  saved_at?: string;
}

// Change Map (M15C.1 backend / M15C.2 UI). This is an AI-drafted,
// student-reviewed sibling of the five workflow sections. It is deliberately
// not a sixth section and never contributes to the N/5 captured count.
export type ChangeMapStatus = "draft" | "confirmed";

export type ChangeMapCategory =
  | "changed_file"
  | "behavior_change"
  | "implementation_decision"
  | "out_of_scope_change"
  | "security_sensitive_area"
  | "unresolved_risk"
  | "unverified_behavior"
  | "question_to_understand";

export type ChangeMapOrigin = "ai_inferred" | "student_added";

export type ChangeMapStudentDecision =
  | "pending_review"
  | "confirmed"
  | "edited"
  | "rejected"
  | "uncertain"
  | "needs_inspection";

export type ChangeMapAiUncertainty = "supported" | "ambiguous" | "needs_inspection";

export type ChangeMapSourceField = "content" | "changed_files" | "student_summary";

export type ChangeMapSourceKind = ImplementationImportSourceKind;

export interface ChangeMapSourceReference {
  source_field: ChangeMapSourceField;
  source_kind: ChangeMapSourceKind;
  file_path: string | null;
  supporting_excerpt: string | null;
}

export interface ChangeMapItem {
  item_id: string;
  origin: ChangeMapOrigin;
  category: ChangeMapCategory;
  draft_text: string | null;
  ai_uncertainty: ChangeMapAiUncertainty | null;
  uncertainty_reason: string | null;
  source_references: ChangeMapSourceReference[];
  student_decision: ChangeMapStudentDecision;
  student_text: string | null;
  student_note: string | null;
}

export interface StoredChangeMap {
  schema_version: "1.0";
  status: ChangeMapStatus;
  source_import_saved_at: string;
  generated_at: string;
  confirmed_at: string | null;
  source_redacted: boolean;
  source_truncated: boolean;
  stale: boolean;
  items: ChangeMapItem[];
}

export interface ChangeMapMutationResult extends StoredChangeMap {
  phase: number;
}

export interface ChangeMapGenerateRequest {
  replace_existing?: true;
}

export interface ChangeMapItemUpdate {
  item_id: string;
  student_decision: ChangeMapStudentDecision;
  student_text: string | null;
  student_note: string | null;
}

export type StudentAddedChangeMapDecision =
  | "confirmed"
  | "uncertain"
  | "needs_inspection";

export interface StudentAddedChangeMapItemRequest {
  category: ChangeMapCategory;
  student_text: string;
  student_note: string | null;
  student_decision: StudentAddedChangeMapDecision;
}

export interface ChangeMapUpdateRequest {
  updates: ChangeMapItemUpdate[];
  student_added_items: StudentAddedChangeMapItemRequest[];
}

export type ChangeMapConfirmationResponse = ChangeMapMutationResult;

export interface WorkflowSections {
  prompt_builder: PromptBuilderArtifact | null;
  review_board: StoredReviewBoardArtifact | null;
  evidence: EvidenceArtifact | null;
  verification: StoredVerificationArtifact | null;
  implementation_import: ImplementationImportArtifact | null;
}

export interface WorkflowPhaseState {
  phase: number;
  sections: WorkflowSections;
  change_map: StoredChangeMap | null;
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

// Metadata-only view of what Project Defense questions can draw on (M14C).
// Presence + labels + truncation flags ONLY — the backend never sends artifact
// content, intake answers, rendered context, or grounding terms here.
export interface ContextSummarySource {
  source_id: string;
  label: string;
  source_type: string;
  truncated: boolean;
}

export interface ContextSummaryMissingSource {
  source_id: string;
  label: string;
}

export interface DefenseContextSummary {
  schema_version: string;
  phase_number: number;
  included_sources: ContextSummarySource[];
  missing_sources: ContextSummaryMissingSource[];
  has_truncation: boolean;
  artifact_aware: boolean;
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
