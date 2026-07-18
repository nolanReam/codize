// Change Map (M15C.2) pure helpers. The page is deliberately a thin consumer:
// human labels, review progress, local review state, validation, confirmation
// readiness, phase routing, and the student-only PUT payload live here and are
// covered by node-only vitest tests.

import type {
  ChangeMapAiUncertainty,
  ChangeMapCategory,
  ChangeMapGenerateRequest,
  ChangeMapItem,
  ChangeMapSourceField,
  ChangeMapStudentDecision,
  ChangeMapUpdateRequest,
  StoredChangeMap,
  StudentAddedChangeMapDecision,
  WorkflowSections,
} from "./types";
import { buildGuidedProjectNavigation } from "./guidedProjectNavigation";

export const CHANGE_MAP_TEXT_MAX = 600;
export const CHANGE_MAP_NOTE_MAX = 1_000;
export const CHANGE_MAP_STUDENT_ITEMS_MAX = 20;

// Python/Pydantic string limits count Unicode code points, while JavaScript's
// string.length counts UTF-16 code units. Array.from keeps the browser-side
// counters and blockers aligned with the backend for non-BMP characters.
export function changeMapCharacterCount(value: string): number {
  return Array.from(value).length;
}

export const CHANGE_MAP_PAGE_TITLE = "Review Your Change Map";
export const CHANGE_MAP_PAGE_INTRO =
  "Codize drafted what appears to have changed from the material you brought back; review and correct it before continuing.";
export const CHANGE_MAP_HONESTY_LINE =
  "This is a draft—not proof that the implementation is correct.";
export const CHANGE_MAP_GENERATION_FAILURE =
  "Codize could not create a safely grounded Change Map from this material yet.";
export const CHANGE_MAP_GENERATION_CORRECTION =
  "Codize could not match every drafted change to a saved file or source. If you edit the Import, put the changed file name beside each change.";

export const CHANGE_MAP_CATEGORY_ORDER: readonly ChangeMapCategory[] = [
  "changed_file",
  "behavior_change",
  "implementation_decision",
  "out_of_scope_change",
  "security_sensitive_area",
  "unresolved_risk",
  "unverified_behavior",
  "question_to_understand",
];

export const CHANGE_MAP_CATEGORY_LABELS: Record<ChangeMapCategory, string> = {
  changed_file: "Changed files",
  behavior_change: "Behavior changes",
  implementation_decision: "Implementation decisions",
  out_of_scope_change: "Possible out-of-scope changes",
  security_sensitive_area: "Areas to review carefully",
  unresolved_risk: "Unresolved risks",
  unverified_behavior: "Behavior still needing testing",
  question_to_understand: "Questions you should understand",
};

export const CHANGE_MAP_CATEGORY_EXPLANATIONS: Record<ChangeMapCategory, string> = {
  changed_file: "Files the imported material indicates may have been created or modified.",
  behavior_change: "Things the app may now do differently.",
  implementation_decision: "Important choices about how the feature was built.",
  out_of_scope_change: "Changes that may go beyond what you originally asked AI to do.",
  security_sensitive_area:
    "Changes involving accounts, permissions, user data, secrets, or other sensitive behavior.",
  unresolved_risk: "Possible concerns or unclear areas that still need review.",
  unverified_behavior: "Behavior the available material does not show as tested.",
  question_to_understand: "Project-specific questions worth answering before moving on.",
};

export const CHANGE_MAP_DECISION_LABELS: Record<ChangeMapStudentDecision, string> = {
  pending_review: "Not reviewed yet",
  confirmed: "Looks right",
  edited: "I need to correct it",
  rejected: "Not accurate or not relevant",
  uncertain: "I’m not sure",
  needs_inspection: "I need to inspect this",
};

export const CHANGE_MAP_AI_UNCERTAINTY_LABELS: Record<ChangeMapAiUncertainty, string> = {
  supported: "Clearly supported by the imported material",
  ambiguous: "The imported material is unclear",
  needs_inspection: "Needs a closer look",
};

export const CHANGE_MAP_SOURCE_FIELD_LABELS: Record<ChangeMapSourceField, string> = {
  content: "Imported material",
  changed_files: "Changed-file list",
  student_summary: "Your summary",
};

export const REVIEWABLE_DECISIONS: readonly Exclude<
  ChangeMapStudentDecision,
  "pending_review"
>[] = ["confirmed", "edited", "rejected", "uncertain", "needs_inspection"];

export const STUDENT_ADDED_DECISIONS: readonly StudentAddedChangeMapDecision[] = [
  "confirmed",
  "uncertain",
  "needs_inspection",
];

export interface AiItemReviewDraft {
  studentDecision: ChangeMapStudentDecision;
  studentText: string;
  studentNote: string;
}

export interface StudentAddedReviewDraft {
  localId: string;
  category: ChangeMapCategory;
  studentText: string;
  studentNote: string;
  studentDecision: StudentAddedChangeMapDecision;
}

// Local persistence contains student editing state only. The server map's
// generation timestamp is part of the draft KEY, not this value, so raw
// imports, references, provenance, timestamps, and provider material are never
// copied into localStorage.
export interface ChangeMapReviewState {
  itemDecisions: Record<string, AiItemReviewDraft>;
  studentAddedItems: StudentAddedReviewDraft[];
}

export interface ReviewProgress {
  reviewed: number;
  total: number;
  pending: number;
}

export interface ConfirmationReadiness {
  allowed: boolean;
  message: string;
}

export interface PhaseNextStep {
  label: string;
  href: string;
  hint: string;
}

export type ChangeMapPageState =
  | "missing_import"
  | "ready_to_generate"
  | "generating"
  | "generation_failed"
  | "draft"
  | "confirmed"
  | "stale";

export interface ChangeMapPageModel {
  state: ChangeMapPageState;
  showRedactionNotice: boolean;
  showTruncationNotice: boolean;
}

const CATEGORIES = new Set<ChangeMapCategory>(CHANGE_MAP_CATEGORY_ORDER);
const DECISIONS = new Set<ChangeMapStudentDecision>([
  "pending_review",
  ...REVIEWABLE_DECISIONS,
]);
const STUDENT_DECISIONS = new Set<StudentAddedChangeMapDecision>(STUDENT_ADDED_DECISIONS);

export function categoryLabel(category: ChangeMapCategory): string {
  return CHANGE_MAP_CATEGORY_LABELS[category];
}

export function categoryExplanation(category: ChangeMapCategory): string {
  return CHANGE_MAP_CATEGORY_EXPLANATIONS[category];
}

export function decisionLabel(decision: ChangeMapStudentDecision): string {
  return CHANGE_MAP_DECISION_LABELS[decision];
}

export function aiUncertaintyLabel(uncertainty: ChangeMapAiUncertainty): string {
  return CHANGE_MAP_AI_UNCERTAINTY_LABELS[uncertainty];
}

export function sourceFieldLabel(field: ChangeMapSourceField): string {
  return CHANGE_MAP_SOURCE_FIELD_LABELS[field];
}

export function groupItemsByCategory(
  items: readonly ChangeMapItem[]
): { category: ChangeMapCategory; items: ChangeMapItem[] }[] {
  return CHANGE_MAP_CATEGORY_ORDER.map((category) => ({
    category,
    items: items.filter((item) => item.category === category),
  })).filter((group) => group.items.length > 0);
}

// Display text is intentionally different from the future downstream M16
// seam: rejected and unresolved items stay visible in the review record.
export function effectiveDisplayText(item: ChangeMapItem): string | null {
  if (item.origin === "student_added" || item.student_decision === "edited") {
    return item.student_text;
  }
  return item.draft_text;
}

export function reviewStateFromMap(map: StoredChangeMap): ChangeMapReviewState {
  const itemDecisions: Record<string, AiItemReviewDraft> = {};
  const studentAddedItems: StudentAddedReviewDraft[] = [];
  for (const item of map.items) {
    if (item.origin === "ai_inferred") {
      itemDecisions[item.item_id] = {
        studentDecision: item.student_decision,
        studentText: item.student_text ?? "",
        studentNote: item.student_note ?? "",
      };
    } else {
      studentAddedItems.push({
        localId: item.item_id,
        category: item.category,
        studentText: item.student_text ?? "",
        studentNote: item.student_note ?? "",
        studentDecision: item.student_decision as StudentAddedChangeMapDecision,
      });
    }
  }
  return { itemDecisions, studentAddedItems };
}

export function deriveReviewProgress(
  map: StoredChangeMap,
  state: ChangeMapReviewState
): ReviewProgress {
  const aiItems = map.items.filter((item) => item.origin === "ai_inferred");
  const reviewedAi = aiItems.filter(
    (item) => {
      const decision = state.itemDecisions[item.item_id]?.studentDecision;
      return decision != null && decision !== "pending_review";
    }
  ).length;
  const reviewedStudentItems = state.studentAddedItems.filter(
    (item) => item.studentText.trim().length > 0
  ).length;
  const total = aiItems.length + state.studentAddedItems.length;
  const reviewed = reviewedAi + reviewedStudentItems;
  return { reviewed, total, pending: total - reviewed };
}

export function pendingItemIds(
  map: StoredChangeMap,
  state: ChangeMapReviewState
): string[] {
  return map.items
    .filter(
      (item) =>
        item.origin === "ai_inferred" &&
        (!state.itemDecisions[item.item_id] ||
          state.itemDecisions[item.item_id].studentDecision === "pending_review")
    )
    .map((item) => item.item_id);
}

function optionalText(value: string): string | null {
  return value.trim().length > 0 ? value : null;
}

export function deriveSavePayload(
  map: StoredChangeMap,
  state: ChangeMapReviewState
): ChangeMapUpdateRequest {
  return {
    updates: map.items
      .filter((item) => item.origin === "ai_inferred")
      .map((item) => {
        const draft = state.itemDecisions[item.item_id] ?? {
          studentDecision: item.student_decision,
          studentText: item.student_text ?? "",
          studentNote: item.student_note ?? "",
        };
        return {
          item_id: item.item_id,
          student_decision: draft.studentDecision,
          student_text: draft.studentDecision === "edited" ? draft.studentText : null,
          student_note: optionalText(draft.studentNote),
        };
      }),
    student_added_items: state.studentAddedItems.map((item) => ({
      category: item.category,
      student_text: item.studentText,
      student_note: optionalText(item.studentNote),
      student_decision: item.studentDecision,
    })),
  };
}

export function reviewBlocker(
  map: StoredChangeMap,
  state: ChangeMapReviewState
): string | null {
  for (const item of map.items) {
    if (item.origin !== "ai_inferred") continue;
    const draft = state.itemDecisions[item.item_id];
    if (!draft) return "Reload this page before saving—the draft no longer matches this map.";
    if (draft.studentDecision === "edited" && !draft.studentText.trim()) {
      return "Add your correction before saving the item marked “I need to correct it.”";
    }
    if (changeMapCharacterCount(draft.studentText) > CHANGE_MAP_TEXT_MAX) {
      return `One correction is over the ${CHANGE_MAP_TEXT_MAX}-character limit.`;
    }
    if (changeMapCharacterCount(draft.studentNote) > CHANGE_MAP_NOTE_MAX) {
      return `One review note is over the ${CHANGE_MAP_NOTE_MAX.toLocaleString()}-character limit.`;
    }
  }
  if (state.studentAddedItems.length > CHANGE_MAP_STUDENT_ITEMS_MAX) {
    return `A Change Map can include at most ${CHANGE_MAP_STUDENT_ITEMS_MAX} student-added items.`;
  }
  for (const item of state.studentAddedItems) {
    if (!item.studentText.trim()) return "Describe each item you added before saving.";
    if (changeMapCharacterCount(item.studentText) > CHANGE_MAP_TEXT_MAX) {
      return `One added item is over the ${CHANGE_MAP_TEXT_MAX}-character limit.`;
    }
    if (changeMapCharacterCount(item.studentNote) > CHANGE_MAP_NOTE_MAX) {
      return `One added-item note is over the ${CHANGE_MAP_NOTE_MAX.toLocaleString()}-character limit.`;
    }
  }
  return null;
}

export function isReviewDirty(map: StoredChangeMap, state: ChangeMapReviewState): boolean {
  const aiIds = map.items
    .filter((item) => item.origin === "ai_inferred")
    .map((item) => item.item_id);
  const stateIds = Object.keys(state.itemDecisions);
  if (aiIds.length !== stateIds.length || aiIds.some((id) => !stateIds.includes(id))) {
    return true;
  }

  // Compare what the PUT would actually persist. This deliberately ignores a
  // retained correction draft after the student switches back to another
  // decision; keeping that text supports toggling without creating a phantom
  // unsaved change or silently returning a confirmed map to draft.
  return (
    JSON.stringify(deriveSavePayload(map, state)) !==
    JSON.stringify(deriveSavePayload(map, reviewStateFromMap(map)))
  );
}

export function isMapStale(map: StoredChangeMap | null): boolean {
  return map?.stale === true;
}

export function confirmationReadiness(
  map: StoredChangeMap,
  state: ChangeMapReviewState,
  hasUnsavedChanges: boolean
): ConfirmationReadiness {
  if (map.status === "confirmed") {
    return { allowed: false, message: "This Change Map is already reviewed and confirmed." };
  }
  if (map.stale) {
    return {
      allowed: false,
      message: "Regenerate this map from the latest implementation material before confirming.",
    };
  }
  if (hasUnsavedChanges) {
    return { allowed: false, message: "Save your review before confirming the map." };
  }
  if (map.items.length === 0 && state.studentAddedItems.length === 0) {
    return {
      allowed: false,
      message: "Add at least one change in your own words before confirming this manual Change Map.",
    };
  }
  const pending = pendingItemIds(map, state).length;
  if (pending > 0) {
    return {
      allowed: false,
      message: `Review every draft item before confirming. ${pending} ${pending === 1 ? "item is" : "items are"} still waiting.`,
    };
  }
  return { allowed: true, message: "Your map is ready to confirm." };
}

export function humanSafeStatusCopy(map: StoredChangeMap): string {
  if (map.stale) return "Needs regeneration";
  return map.status === "confirmed" ? "Reviewed and confirmed" : "Draft needs review";
}

export function changeMapStepStatus(
  map: StoredChangeMap | null
): { label: string; tone: "idle" | "draft" | "done" | "stale" } {
  if (!map) return { label: "not created", tone: "idle" };
  if (map.stale) return { label: "stale", tone: "stale" };
  if (map.status === "confirmed") return { label: "reviewed", tone: "done" };
  return { label: "draft needs review", tone: "draft" };
}

export function generationRequestBody(
  replaceExisting: boolean
): ChangeMapGenerateRequest | undefined {
  return replaceExisting ? { replace_existing: true } : undefined;
}

export function deriveChangeMapPageModel(
  hasImport: boolean,
  map: StoredChangeMap | null,
  generating: boolean,
  generationFailed: boolean
): ChangeMapPageModel {
  let state: ChangeMapPageState;
  if (map?.stale) state = "stale";
  else if (map?.status === "confirmed") state = "confirmed";
  else if (map) state = "draft";
  else if (generating) state = "generating";
  else if (generationFailed) state = "generation_failed";
  else state = hasImport ? "ready_to_generate" : "missing_import";
  return {
    state,
    showRedactionNotice: map?.source_redacted === true,
    showTruncationNotice: map?.source_truncated === true,
  };
}

export function changeMapDraftSurface(phase: number, map: StoredChangeMap): string {
  return `change_map_review:${phase}:${map.generated_at}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// LocalStorage is an untrusted boundary. Restore only a complete review state
// for the exact AI item set in this map; generation timestamp scoping handles
// replacement maps, and stale maps are rejected outright.
export function restoreReviewDraft(
  map: StoredChangeMap,
  value: unknown
): ChangeMapReviewState | null {
  if (map.stale || !isRecord(value) || !isRecord(value.itemDecisions)) return null;
  if (!Array.isArray(value.studentAddedItems)) return null;

  const aiIds = map.items
    .filter((item) => item.origin === "ai_inferred")
    .map((item) => item.item_id);
  const storedIds = Object.keys(value.itemDecisions);
  if (aiIds.length !== storedIds.length || aiIds.some((id) => !storedIds.includes(id))) {
    return null;
  }

  const itemDecisions: Record<string, AiItemReviewDraft> = {};
  for (const id of aiIds) {
    const candidate = value.itemDecisions[id];
    if (!isRecord(candidate)) return null;
    if (
      typeof candidate.studentDecision !== "string" ||
      !DECISIONS.has(candidate.studentDecision as ChangeMapStudentDecision) ||
      typeof candidate.studentText !== "string" ||
      typeof candidate.studentNote !== "string"
    ) {
      return null;
    }
    itemDecisions[id] = {
      studentDecision: candidate.studentDecision as ChangeMapStudentDecision,
      studentText: candidate.studentText,
      studentNote: candidate.studentNote,
    };
  }

  const studentAddedItems: StudentAddedReviewDraft[] = [];
  for (const candidate of value.studentAddedItems) {
    if (!isRecord(candidate)) return null;
    if (
      typeof candidate.localId !== "string" ||
      typeof candidate.category !== "string" ||
      !CATEGORIES.has(candidate.category as ChangeMapCategory) ||
      typeof candidate.studentText !== "string" ||
      typeof candidate.studentNote !== "string" ||
      typeof candidate.studentDecision !== "string" ||
      !STUDENT_DECISIONS.has(candidate.studentDecision as StudentAddedChangeMapDecision)
    ) {
      return null;
    }
    studentAddedItems.push({
      localId: candidate.localId,
      category: candidate.category as ChangeMapCategory,
      studentText: candidate.studentText,
      studentNote: candidate.studentNote,
      studentDecision: candidate.studentDecision as StudentAddedChangeMapDecision,
    });
  }
  if (studentAddedItems.length > CHANGE_MAP_STUDENT_ITEMS_MAX) return null;
  return { itemDecisions, studentAddedItems };
}

export function hasOnlyQuestionItems(map: StoredChangeMap): boolean {
  return map.items.length > 0 && map.items.every((item) => item.category === "question_to_understand");
}

export function derivePhaseNextStep(
  sections: WorkflowSections | null,
  map: StoredChangeMap | null
): PhaseNextStep {
  const navigation = buildGuidedProjectNavigation({
    evaluation: {
      state: "gate_ready",
      project_status: "active",
      next_action: "",
      current_phase: 1,
      phase_title: "",
      total_phases: 1,
      completed_phases: 0,
      completed_task_count: 0,
      total_task_count: 0,
      incomplete_tasks: [],
      recent_gate: null,
      unlocks: [],
    },
    workflow: sections ? { phase: 1, sections, change_map: map } : null,
    gate: { phase: 1, phase_title: "", state: "not_started" },
  });
  return {
    label: navigation.continueAction.label,
    href: navigation.continueAction.href ?? "/app/phase",
    hint: navigation.continueAction.reason,
  };
}
