// Linked Verification pure contract helpers. The page renders and orchestrates;
// this module owns exact labels, grouping, student-only payloads, validation,
// progress, dirty state, draft compatibility, and guided-workflow status.

import {
  isLinkedReviewArtifact,
  linkedReviewAllowsVerification,
  targetFormFromReview,
} from "./review";
import type {
  LinkedVerificationArtifact,
  LinkedVerificationTarget,
  StoredReviewBoardArtifact,
  StoredVerificationArtifact,
  VerificationInitializationRequest,
  VerificationResult,
  VerificationSaveRequest,
  VerificationSourceCategory,
  VerificationTargetUpdateRequest,
} from "./types";

export const VERIFICATION_TEXT_MAX = 2_000;
export const VERIFICATION_PAGE_TITLE = "Test What You Changed";
export const VERIFICATION_PAGE_INTRO =
  "Review gave you the implementation items that still need testing. Codize suggested checks to help you get started. You perform the checks and record what actually happened.";
export const VERIFICATION_HONESTY_LINE =
  "A suggested check is not a result. Nothing is marked passed until you record what you observed.";

export const VERIFICATION_CATEGORY_ORDER: readonly VerificationSourceCategory[] = [
  "behavior_change",
  "implementation_decision",
  "out_of_scope_change",
  "security_sensitive_area",
  "unresolved_risk",
  "unverified_behavior",
];

export const VERIFICATION_CATEGORY_LABELS: Record<VerificationSourceCategory, string> = {
  behavior_change: "Behavior changes",
  implementation_decision: "Implementation decisions",
  out_of_scope_change: "Possible out-of-scope changes",
  security_sensitive_area: "Areas to review carefully",
  unresolved_risk: "Unresolved risks",
  unverified_behavior: "Behavior still needing testing",
};

export const VERIFICATION_RESULTS: readonly (VerificationResult | null)[] = [
  null,
  "pass",
  "fail",
  "skipped",
  "not_applicable",
];

export const VERIFICATION_RESULT_LABELS: Record<VerificationResult, string> = {
  pass: "Passed",
  fail: "Failed",
  skipped: "Skipped",
  not_applicable: "Not applicable",
};

export const VERIFICATION_RESULT_DESCRIPTIONS: Record<VerificationResult, string> = {
  pass: "I performed the check and observed the expected behavior.",
  fail: "I performed the check and observed a problem or mismatch.",
  skipped: "I did not perform this check. Skipped does not count as passed.",
  not_applicable:
    "This suggested check does not apply to the current implementation. Not applicable does not count as passed.",
};

const RESULT_SET = new Set<VerificationResult>([
  "pass",
  "fail",
  "skipped",
  "not_applicable",
]);
const CATEGORY_SET = new Set<VerificationSourceCategory>(VERIFICATION_CATEGORY_ORDER);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isVerificationTarget(value: unknown): value is LinkedVerificationTarget {
  if (!isRecord(value)) return false;
  return (
    typeof value.verification_target_id === "string" &&
    typeof value.review_target_id === "string" &&
    typeof value.change_map_item_id === "string" &&
    typeof value.category === "string" &&
    CATEGORY_SET.has(value.category as VerificationSourceCategory) &&
    typeof value.source_text === "string" &&
    isNullableString(value.source_rationale) &&
    typeof value.suggested_check === "string" &&
    isNullableString(value.student_check) &&
    (value.result === null ||
      (typeof value.result === "string" && RESULT_SET.has(value.result as VerificationResult))) &&
    isNullableString(value.result_notes)
  );
}

export function isLinkedVerificationArtifact(
  value: StoredVerificationArtifact | null | unknown
): value is LinkedVerificationArtifact {
  if (!isRecord(value) || !isRecord(value.source_review_binding)) return false;
  const binding = value.source_review_binding;
  return (
    value.initialized_from_review === true &&
    typeof value.stale === "boolean" &&
    typeof value.initialized_at === "string" &&
    typeof binding.source_change_map_generated_at === "string" &&
    typeof binding.source_change_map_confirmed_at === "string" &&
    typeof binding.review_saved_at === "string" &&
    typeof binding.review_target_fingerprint === "string" &&
    Array.isArray(value.verification_targets) &&
    value.verification_targets.every(isVerificationTarget)
  );
}

export type VerificationArtifactMode = "none" | "linked" | "legacy";

export function verificationArtifactMode(value: unknown): VerificationArtifactMode {
  if (value == null) return "none";
  return isLinkedVerificationArtifact(value) ? "linked" : "legacy";
}

export function verificationCharacterCount(value: string): number {
  return Array.from(value).length;
}

export function verificationCategoryLabel(category: VerificationSourceCategory): string {
  return VERIFICATION_CATEGORY_LABELS[category];
}

export function verificationResultLabel(result: VerificationResult | null): string {
  return result === null ? "Not recorded yet" : VERIFICATION_RESULT_LABELS[result];
}

export function verificationResultDescription(result: VerificationResult | null): string {
  return result === null
    ? "No result has been recorded for this check."
    : VERIFICATION_RESULT_DESCRIPTIONS[result];
}

export function resultNotesLabel(result: VerificationResult): string {
  if (result === "fail") return "What happened?";
  if (result === "skipped") return "Why was this skipped? (optional)";
  if (result === "not_applicable") return "Why does this not apply? (optional)";
  return "What happened? (optional)";
}

export function resultNotesGuidance(result: VerificationResult): string {
  if (result === "fail") {
    return "Record what you did, what you expected, and what you observed.";
  }
  if (result === "skipped") return "Skipped records that you did not perform this check.";
  if (result === "not_applicable") {
    return "Not applicable records that this check does not fit the current implementation.";
  }
  return "This records this check only; it does not prove the entire project is correct.";
}

export function groupVerificationTargets(
  targets: readonly LinkedVerificationTarget[]
): { category: VerificationSourceCategory; targets: LinkedVerificationTarget[] }[] {
  return VERIFICATION_CATEGORY_ORDER.map((category) => ({
    category,
    targets: targets.filter((target) => target.category === category),
  })).filter((group) => group.targets.length > 0);
}

export interface LinkedVerificationTargetForm {
  studentCheck: string;
  result: VerificationResult | null;
  resultNotes: string;
}

export type LinkedVerificationFormState = Record<string, LinkedVerificationTargetForm>;

export function targetFormFromVerification(
  verification: LinkedVerificationArtifact
): LinkedVerificationFormState {
  return Object.fromEntries(
    verification.verification_targets.map((target) => [
      target.verification_target_id,
      {
        studentCheck: target.student_check ?? "",
        result: target.result,
        resultNotes: target.result_notes ?? "",
      },
    ])
  );
}

export function changeVerificationResult(
  form: LinkedVerificationTargetForm,
  result: VerificationResult | null
): LinkedVerificationTargetForm {
  if (form.result === result) return form;
  return { ...form, result, resultNotes: "" };
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

export function effectiveCheckWording(
  target: LinkedVerificationTarget,
  form: LinkedVerificationTargetForm
): string {
  return optionalText(form.studentCheck) ?? target.suggested_check;
}

export function canonicalVerificationTargetUpdate(
  target: LinkedVerificationTarget,
  form: LinkedVerificationTargetForm
): VerificationTargetUpdateRequest {
  return {
    verification_target_id: target.verification_target_id,
    student_check: optionalText(form.studentCheck),
    result: form.result,
    result_notes: form.result === null ? null : optionalText(form.resultNotes),
  };
}

function storedTargetUpdate(target: LinkedVerificationTarget): VerificationTargetUpdateRequest {
  return canonicalVerificationTargetUpdate(target, {
    studentCheck: target.student_check ?? "",
    result: target.result,
    resultNotes: target.result_notes ?? "",
  });
}

export function deriveVerificationSavePayload(
  verification: LinkedVerificationArtifact,
  state: LinkedVerificationFormState
): VerificationSaveRequest {
  const target_updates = verification.verification_targets.flatMap((target) => {
    const form = state[target.verification_target_id];
    if (!form) return [];
    const update = canonicalVerificationTargetUpdate(target, form);
    return JSON.stringify(update) === JSON.stringify(storedTargetUpdate(target))
      ? []
      : [update];
  });
  return { target_updates };
}

export function isLinkedVerificationDirty(
  verification: LinkedVerificationArtifact,
  state: LinkedVerificationFormState
): boolean {
  if (Object.keys(state).length !== verification.verification_targets.length) return true;
  return verification.verification_targets.some((target) => {
    const form = state[target.verification_target_id];
    return (
      !form ||
      JSON.stringify(canonicalVerificationTargetUpdate(target, form)) !==
        JSON.stringify(storedTargetUpdate(target))
    );
  });
}

export interface VerificationTargetValidation {
  studentCheck?: string;
  resultNotes?: string;
}

export function validateVerificationTarget(
  form: LinkedVerificationTargetForm | undefined
): VerificationTargetValidation {
  if (!form) return { studentCheck: "Reload this page—the Verification draft no longer matches." };
  const errors: VerificationTargetValidation = {};
  if (verificationCharacterCount(form.studentCheck) > VERIFICATION_TEXT_MAX) {
    errors.studentCheck =
      `Keep this check within ${VERIFICATION_TEXT_MAX.toLocaleString()} characters.`;
  }
  if (
    form.result !== null &&
    verificationCharacterCount(form.resultNotes) > VERIFICATION_TEXT_MAX
  ) {
    errors.resultNotes =
      `Keep these notes within ${VERIFICATION_TEXT_MAX.toLocaleString()} characters.`;
  }
  return errors;
}

export function verificationFormBlocker(
  verification: LinkedVerificationArtifact,
  state: LinkedVerificationFormState
): string | null {
  for (const target of verification.verification_targets) {
    const errors = validateVerificationTarget(state[target.verification_target_id]);
    const first = errors.studentCheck ?? errors.resultNotes;
    if (first) return first;
  }
  return null;
}

export interface VerificationProgress {
  recorded: number;
  total: number;
  unperformed: number;
}

export function linkedVerificationProgress(
  verification: LinkedVerificationArtifact,
  state: LinkedVerificationFormState
): VerificationProgress {
  const recorded = verification.verification_targets.filter(
    (target) => state[target.verification_target_id]?.result != null
  ).length;
  const total = verification.verification_targets.length;
  return { recorded, total, unperformed: total - recorded };
}

export interface VerificationResultSummary {
  recorded: number;
  passed: number;
  failed: number;
  skipped: number;
  notApplicable: number;
  unperformed: number;
}

export function linkedVerificationResultSummary(
  verification: LinkedVerificationArtifact,
  state: LinkedVerificationFormState
): VerificationResultSummary {
  const values = verification.verification_targets.map(
    (target) => state[target.verification_target_id]?.result ?? null
  );
  const recorded = values.filter((result) => result !== null).length;
  return {
    recorded,
    passed: values.filter((result) => result === "pass").length,
    failed: values.filter((result) => result === "fail").length,
    skipped: values.filter((result) => result === "skipped").length,
    notApplicable: values.filter((result) => result === "not_applicable").length,
    unperformed: values.length - recorded,
  };
}

export function linkedVerificationRecorded(
  verification: LinkedVerificationArtifact,
  state: LinkedVerificationFormState
): boolean {
  const progress = linkedVerificationProgress(verification, state);
  return (
    progress.total > 0 &&
    progress.recorded === progress.total &&
    verificationFormBlocker(verification, state) === null
  );
}

export function isZeroTargetVerification(verification: LinkedVerificationArtifact): boolean {
  return verification.verification_targets.length === 0;
}

export type VerificationPrerequisiteState =
  | "no_review"
  | "incomplete_review"
  | "stale_review"
  | "ready";

export function verificationPrerequisiteState(
  review: StoredReviewBoardArtifact | null
): VerificationPrerequisiteState {
  if (!isLinkedReviewArtifact(review)) return "no_review";
  if (review.stale) return "stale_review";
  const state = targetFormFromReview(review);
  if (!review.saved_at || !linkedReviewAllowsVerification(review, state)) {
    return "incomplete_review";
  }
  return "ready";
}

export function canReplaceVerificationFromReview(
  review: StoredReviewBoardArtifact | null
): boolean {
  return verificationPrerequisiteState(review) === "ready";
}

export function verificationInitializationBody(
  replaceExisting: boolean
): VerificationInitializationRequest | undefined {
  return replaceExisting ? { replace_existing: true } : undefined;
}

export function showFullVerificationInitializationState(
  initializing: boolean,
  hasExistingVerification: boolean
): boolean {
  return initializing && !hasExistingVerification;
}

function verificationFingerprint(verification: LinkedVerificationArtifact): string {
  const binding = verification.source_review_binding;
  const input = [
    verification.initialized_at,
    binding.review_target_fingerprint,
    binding.review_saved_at,
    ...verification.verification_targets.map((target) => target.verification_target_id),
  ].join("\n");
  let hash = 0x811c9dc5;
  for (const character of input) {
    hash ^= character.codePointAt(0) ?? 0;
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function linkedVerificationDraftSurface(
  phase: number,
  verification: LinkedVerificationArtifact
): string {
  return `linked_verification:active-project:${phase}:${verificationFingerprint(verification)}`;
}

export function linkedVerificationServerRevision(
  verification: LinkedVerificationArtifact
): string {
  return JSON.stringify({
    savedAt: verification.saved_at ?? null,
    stale: verification.stale,
    fingerprint: verificationFingerprint(verification),
    targets: verification.verification_targets.map((target) => [
      target.verification_target_id,
      target.student_check,
      target.result,
      target.result_notes,
    ]),
  });
}

export function shouldKeepVerificationSaveNotice(
  acknowledgedRevision: string | null,
  serverRevision: string
): boolean {
  return acknowledgedRevision === serverRevision;
}

export interface LinkedVerificationDraft {
  fingerprint: string;
  targets: LinkedVerificationFormState;
}

export function linkedVerificationDraftValue(
  verification: LinkedVerificationArtifact,
  state: LinkedVerificationFormState
): LinkedVerificationDraft {
  return { fingerprint: verificationFingerprint(verification), targets: state };
}

export function restoreLinkedVerificationDraft(
  verification: LinkedVerificationArtifact,
  value: unknown
): LinkedVerificationFormState | null {
  if (verification.stale || !isRecord(value) || !isRecord(value.targets)) return null;
  if (value.fingerprint !== verificationFingerprint(verification)) return null;
  const expectedIds = verification.verification_targets.map(
    (target) => target.verification_target_id
  );
  const storedIds = Object.keys(value.targets);
  if (
    expectedIds.length !== storedIds.length ||
    expectedIds.some((targetId) => !storedIds.includes(targetId))
  ) {
    return null;
  }
  const restored: LinkedVerificationFormState = {};
  for (const targetId of expectedIds) {
    const candidate = value.targets[targetId];
    if (
      !isRecord(candidate) ||
      typeof candidate.studentCheck !== "string" ||
      !(candidate.result === null ||
        (typeof candidate.result === "string" &&
          RESULT_SET.has(candidate.result as VerificationResult))) ||
      typeof candidate.resultNotes !== "string"
    ) {
      return null;
    }
    restored[targetId] = {
      studentCheck: candidate.studentCheck,
      result: candidate.result as VerificationResult | null,
      resultNotes: candidate.resultNotes,
    };
  }
  return restored;
}

export function verificationStepStatus(
  verification: StoredVerificationArtifact | null,
  review: StoredReviewBoardArtifact | null
): { label: string; tone: "idle" | "draft" | "done" | "stale" } {
  if (!verification) {
    return verificationPrerequisiteState(review) === "ready"
      ? { label: "ready to start", tone: "draft" }
      : { label: "not available yet", tone: "idle" };
  }
  if (!isLinkedVerificationArtifact(verification)) return { label: "saved", tone: "done" };
  if (verification.stale) return { label: "stale", tone: "stale" };
  if (verification.verification_targets.length === 0) {
    return { label: "no checks requested", tone: "draft" };
  }
  const state = targetFormFromVerification(verification);
  return linkedVerificationRecorded(verification, state)
    ? { label: "results recorded", tone: "done" }
    : { label: "in progress", tone: "draft" };
}
