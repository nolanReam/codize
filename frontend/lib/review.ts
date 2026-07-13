// Linked Review (M16A.2) pure helpers. The page stays focused on rendering and
// events; exact labels, safe payloads, validation, progress, staleness, local
// draft compatibility, and Build Loop status live here for node-only tests.

import type {
  LinkedReviewBoardArtifact,
  LinkedReviewTarget,
  ReviewBoardSaveRequest,
  ReviewDecision,
  ReviewInitializationRequest,
  ReviewSourceCategory,
  ReviewTargetUpdate,
  StoredChangeMap,
  StoredReviewBoardArtifact,
} from "./types";

export const REVIEW_TEXT_MAX = 2_000;

// Python/Pydantic counts Unicode code points. JavaScript string.length counts
// UTF-16 code units, so Array.from keeps counters and blockers aligned.
export function reviewCharacterCount(value: string): number {
  return Array.from(value).length;
}

export const REVIEW_PAGE_TITLE = "Review What Changed";
export const REVIEW_PAGE_INTRO =
  "Your Change Map records what appears to have changed. Now decide what to keep, revise, remove, test, or inspect further.";
export const REVIEW_HONESTY_LINE = "This is your review—not an AI approval.";

export const REVIEW_TARGET_CATEGORY_ORDER: readonly ReviewSourceCategory[] = [
  "behavior_change",
  "implementation_decision",
  "out_of_scope_change",
  "security_sensitive_area",
  "unresolved_risk",
  "unverified_behavior",
];

export const REVIEW_CATEGORY_LABELS: Record<ReviewSourceCategory, string> = {
  changed_file: "Changed files",
  behavior_change: "Behavior changes",
  implementation_decision: "Implementation decisions",
  out_of_scope_change: "Possible out-of-scope changes",
  security_sensitive_area: "Areas to review carefully",
  unresolved_risk: "Unresolved risks",
  unverified_behavior: "Behavior still needing testing",
  question_to_understand: "Questions you should understand",
};

export const REVIEW_DECISIONS: readonly ReviewDecision[] = [
  "pending",
  "keep",
  "revise",
  "remove",
  "needs_verification",
  "uncertain",
];

export const REVIEW_DECISION_LABELS: Record<ReviewDecision, string> = {
  pending: "Not reviewed yet",
  keep: "Keep",
  revise: "Revise",
  remove: "Remove",
  needs_verification: "Needs testing",
  uncertain: "I’m not sure",
};

export const REVIEW_DECISION_MEANINGS: Record<ReviewDecision, string> = {
  pending: "Leave this item waiting for your review.",
  keep: "Keep this implementation choice for now.",
  revise: "Record the change you want to make next.",
  remove: "This change should be removed or does not belong in the intended implementation.",
  needs_verification: "Test the behavior before deciding whether to keep or revise it.",
  uncertain: "Record honestly that you are not ready to decide yet.",
};

const DECISION_SET = new Set<ReviewDecision>(REVIEW_DECISIONS);
const TARGET_CATEGORY_SET = new Set<ReviewSourceCategory>(REVIEW_TARGET_CATEGORY_ORDER);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isLinkedTarget(value: unknown): value is LinkedReviewTarget {
  if (!isRecord(value)) return false;
  return (
    typeof value.review_target_id === "string" &&
    typeof value.change_map_item_id === "string" &&
    typeof value.change_map_category === "string" &&
    typeof value.change_map_origin === "string" &&
    typeof value.change_map_student_decision === "string" &&
    typeof value.change_text === "string" &&
    (value.source_resolution === "confirmed" || value.source_resolution === "unresolved") &&
    typeof value.review_decision === "string" &&
    DECISION_SET.has(value.review_decision as ReviewDecision) &&
    (value.student_rationale === null || typeof value.student_rationale === "string") &&
    (value.student_revision === null || typeof value.student_revision === "string")
  );
}

export function isLinkedReviewArtifact(
  value: StoredReviewBoardArtifact | null | unknown
): value is LinkedReviewBoardArtifact {
  if (!isRecord(value)) return false;
  return (
    value.initialized_from_change_map === true &&
    typeof value.stale === "boolean" &&
    typeof value.source_change_map_confirmed_at === "string" &&
    typeof value.source_change_map_generated_at === "string" &&
    Array.isArray(value.review_targets) &&
    value.review_targets.every(isLinkedTarget)
  );
}

export type ReviewArtifactMode = "none" | "linked" | "legacy";

export function reviewArtifactMode(value: unknown): ReviewArtifactMode {
  if (value == null) return "none";
  return isLinkedReviewArtifact(value) ? "linked" : "legacy";
}

export function reviewCategoryLabel(category: ReviewSourceCategory): string {
  return REVIEW_CATEGORY_LABELS[category];
}

export function reviewDecisionLabel(decision: ReviewDecision): string {
  return REVIEW_DECISION_LABELS[decision];
}

export function groupReviewTargets(
  targets: readonly LinkedReviewTarget[]
): { category: ReviewSourceCategory; targets: LinkedReviewTarget[] }[] {
  return REVIEW_TARGET_CATEGORY_ORDER.map((category) => ({
    category,
    targets: targets.filter((target) => target.change_map_category === category),
  })).filter((group) => group.targets.length > 0);
}

export function sourceResolutionLabel(target: LinkedReviewTarget): string {
  if (target.change_map_origin === "student_added") return "Added by you";
  if (target.change_map_student_decision === "edited") {
    return "Corrected by you in Change Map";
  }
  if (target.change_map_student_decision === "uncertain") {
    return "Marked uncertain in Change Map";
  }
  if (target.change_map_student_decision === "needs_inspection") {
    return "Still needs inspection";
  }
  return "Confirmed in Change Map";
}

export function sourceResolutionGuidance(target: LinkedReviewTarget): string | null {
  if (target.change_map_student_decision === "uncertain") {
    return "You marked this item uncertain in the Change Map. Review it cautiously and record what should happen next.";
  }
  if (target.change_map_student_decision === "needs_inspection") {
    return "You marked this item for inspection. Keep that uncertainty visible while deciding what to do next.";
  }
  return null;
}

export interface LinkedReviewTargetForm {
  reviewDecision: ReviewDecision;
  studentRationale: string;
  studentRevision: string;
}

export type LinkedReviewFormState = Record<string, LinkedReviewTargetForm>;

export function targetFormFromReview(review: LinkedReviewBoardArtifact): LinkedReviewFormState {
  return Object.fromEntries(
    review.review_targets.map((target) => [
      target.review_target_id,
      {
        reviewDecision: target.review_decision,
        studentRationale: target.student_rationale ?? "",
        studentRevision: target.student_revision ?? "",
      },
    ])
  );
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function rationaleIsActive(decision: ReviewDecision): boolean {
  return decision === "revise" || decision === "remove" ||
    decision === "needs_verification" || decision === "uncertain";
}

export function canonicalTargetUpdate(
  target: LinkedReviewTarget,
  form: LinkedReviewTargetForm
): ReviewTargetUpdate {
  return {
    review_target_id: target.review_target_id,
    review_decision: form.reviewDecision,
    student_rationale: rationaleIsActive(form.reviewDecision)
      ? optionalText(form.studentRationale)
      : null,
    student_revision: form.reviewDecision === "revise"
      ? optionalText(form.studentRevision)
      : null,
  };
}

function storedTargetUpdate(target: LinkedReviewTarget): ReviewTargetUpdate {
  return canonicalTargetUpdate(target, {
    reviewDecision: target.review_decision,
    studentRationale: target.student_rationale ?? "",
    studentRevision: target.student_revision ?? "",
  });
}

export function deriveReviewSavePayload(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): ReviewBoardSaveRequest {
  const target_updates = review.review_targets.flatMap((target) => {
    const form = state[target.review_target_id];
    if (!form) return [];
    const update = canonicalTargetUpdate(target, form);
    return JSON.stringify(update) === JSON.stringify(storedTargetUpdate(target))
      ? []
      : [update];
  });
  return { target_updates };
}

export function isLinkedReviewDirty(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): boolean {
  if (Object.keys(state).length !== review.review_targets.length) return true;
  return review.review_targets.some((target) => {
    const form = state[target.review_target_id];
    return !form || JSON.stringify(canonicalTargetUpdate(target, form)) !==
      JSON.stringify(storedTargetUpdate(target));
  });
}

export interface ReviewTargetValidation {
  decision?: string;
  rationale?: string;
  revision?: string;
}

export function validateReviewTarget(
  form: LinkedReviewTargetForm | undefined
): ReviewTargetValidation {
  if (!form) return { decision: "Reload this page—the Review draft no longer matches." };
  const errors: ReviewTargetValidation = {};
  const rationaleActive = rationaleIsActive(form.reviewDecision);
  if (
    form.reviewDecision === "revise" &&
    !form.studentRationale.trim() &&
    !form.studentRevision.trim()
  ) {
    errors.revision = "Describe what should change, or add a rationale for the revision.";
  }
  if (rationaleActive && reviewCharacterCount(form.studentRationale) > REVIEW_TEXT_MAX) {
    errors.rationale = `Keep this explanation within ${REVIEW_TEXT_MAX.toLocaleString()} characters.`;
  }
  if (
    form.reviewDecision === "revise" &&
    reviewCharacterCount(form.studentRevision) > REVIEW_TEXT_MAX
  ) {
    errors.revision = `Keep the proposed revision within ${REVIEW_TEXT_MAX.toLocaleString()} characters.`;
  }
  return errors;
}

export function reviewFormBlocker(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): string | null {
  for (const target of review.review_targets) {
    const errors = validateReviewTarget(state[target.review_target_id]);
    const first = errors.decision ?? errors.revision ?? errors.rationale;
    if (first) return first;
  }
  return null;
}

export interface LinkedReviewProgress {
  reviewed: number;
  total: number;
  pending: number;
}

export function linkedReviewProgress(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): LinkedReviewProgress {
  const reviewed = review.review_targets.filter(
    (target) => state[target.review_target_id]?.reviewDecision !== "pending"
  ).length;
  const total = review.review_targets.length;
  return { reviewed, total, pending: total - reviewed };
}

export function pendingReviewTargetIds(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): string[] {
  return review.review_targets
    .filter((target) => state[target.review_target_id]?.reviewDecision === "pending")
    .map((target) => target.review_target_id);
}

export function linkedReviewComplete(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): boolean {
  return (
    review.review_targets.length > 0 &&
    pendingReviewTargetIds(review, state).length === 0 &&
    reviewFormBlocker(review, state) === null
  );
}

export function linkedReviewAllowsVerification(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): boolean {
  return review.review_targets.length === 0 || linkedReviewComplete(review, state);
}

export type ReviewPrerequisiteState =
  | "missing_change_map"
  | "draft_change_map"
  | "stale_change_map"
  | "ready";

export function reviewPrerequisiteState(map: StoredChangeMap | null): ReviewPrerequisiteState {
  if (!map) return "missing_change_map";
  if (map.stale) return "stale_change_map";
  if (map.status !== "confirmed") return "draft_change_map";
  return "ready";
}

export function canReplaceReviewFromMap(map: StoredChangeMap | null): boolean {
  return reviewPrerequisiteState(map) === "ready";
}

export function reviewInitializationBody(
  replaceExisting: boolean
): ReviewInitializationRequest | undefined {
  return replaceExisting ? { replace_existing: true } : undefined;
}

function reviewFingerprint(review: LinkedReviewBoardArtifact): string {
  const input = [
    review.source_change_map_generated_at,
    review.source_change_map_confirmed_at,
    ...review.review_targets.map((target) => target.review_target_id),
  ].join("\n");
  // FNV-1a: a compact compatibility token, not a security primitive. It keeps
  // raw source text out of storage keys while changing when the source binding
  // or ordered target set changes.
  let hash = 0x811c9dc5;
  for (const character of input) {
    hash ^= character.codePointAt(0) ?? 0;
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function linkedReviewDraftSurface(
  phase: number,
  review: LinkedReviewBoardArtifact
): string {
  // Codize currently has exactly one active project per authenticated user;
  // `active-project` is the project scope until the multi-project contract adds
  // a safe client-visible project identifier. useDraft adds the user scope.
  return `linked_review:active-project:${phase}:${reviewFingerprint(review)}`;
}

// React may receive a freshly parsed Review object even when the saved server
// state is unchanged. Keep form resets tied to the actual persisted state so
// a later parent re-render cannot overwrite a local draft restored on mount.
export function linkedReviewServerRevision(review: LinkedReviewBoardArtifact): string {
  return JSON.stringify({
    savedAt: review.saved_at ?? null,
    stale: review.stale,
    generatedAt: review.source_change_map_generated_at,
    confirmedAt: review.source_change_map_confirmed_at,
    targets: review.review_targets.map((target) => [
      target.review_target_id,
      target.review_decision,
      target.student_rationale,
      target.student_revision,
    ]),
  });
}

export interface LinkedReviewDraft {
  fingerprint: string;
  targets: LinkedReviewFormState;
}

export function linkedReviewDraftValue(
  review: LinkedReviewBoardArtifact,
  state: LinkedReviewFormState
): LinkedReviewDraft {
  return { fingerprint: reviewFingerprint(review), targets: state };
}

export function restoreLinkedReviewDraft(
  review: LinkedReviewBoardArtifact,
  value: unknown
): LinkedReviewFormState | null {
  if (review.stale || !isRecord(value) || !isRecord(value.targets)) return null;
  if (value.fingerprint !== reviewFingerprint(review)) return null;
  const expectedIds = review.review_targets.map((target) => target.review_target_id);
  const storedIds = Object.keys(value.targets);
  if (
    expectedIds.length !== storedIds.length ||
    expectedIds.some((targetId) => !storedIds.includes(targetId))
  ) {
    return null;
  }
  const restored: LinkedReviewFormState = {};
  for (const targetId of expectedIds) {
    const candidate = value.targets[targetId];
    if (
      !isRecord(candidate) ||
      typeof candidate.reviewDecision !== "string" ||
      !DECISION_SET.has(candidate.reviewDecision as ReviewDecision) ||
      typeof candidate.studentRationale !== "string" ||
      typeof candidate.studentRevision !== "string"
    ) {
      return null;
    }
    restored[targetId] = {
      reviewDecision: candidate.reviewDecision as ReviewDecision,
      studentRationale: candidate.studentRationale,
      studentRevision: candidate.studentRevision,
    };
  }
  return restored;
}

export function reviewStepStatus(
  review: StoredReviewBoardArtifact | null,
  map: StoredChangeMap | null
): { label: string; tone: "idle" | "draft" | "done" | "stale" } {
  if (!review) {
    return reviewPrerequisiteState(map) === "ready"
      ? { label: "ready to start", tone: "draft" }
      : { label: "not started", tone: "idle" };
  }
  if (!isLinkedReviewArtifact(review)) return { label: "saved", tone: "done" };
  if (review.stale) return { label: "stale", tone: "stale" };
  if (review.review_targets.length === 0) return { label: "no targets", tone: "done" };
  const state = targetFormFromReview(review);
  return linkedReviewComplete(review, state)
    ? { label: "complete", tone: "done" }
    : { label: "in progress", tone: "draft" };
}

// The category policy excludes changed_file and question_to_understand. This
// runtime check is useful in tests and defensive UI assertions without hiding
// or remapping data to make the screen look fuller.
export function isReviewTargetCategory(category: ReviewSourceCategory): boolean {
  return TARGET_CATEGORY_SET.has(category);
}
