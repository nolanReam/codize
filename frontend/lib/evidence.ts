// Linked Evidence pure contract helpers. The page renders and orchestrates;
// this module owns exact modes, labels, server-trusted selection, student-only
// payloads, validation, dirty state, draft compatibility, progress, and stale
// behavior.

import {
  isLinkedVerificationArtifact,
  linkedVerificationRecorded,
  targetFormFromVerification,
} from "./verification";
import type {
  EvidenceEntry,
  EvidenceHandoffPreview,
  EvidenceHandoffResult,
  EvidenceHandoffTarget,
  EvidenceInitializationRequest,
  EvidenceKind,
  EvidenceSaveRequest,
  EvidenceStatus,
  EvidenceTargetUpdateRequest,
  LinkedEvidenceArtifact,
  LinkedEvidenceTarget,
  StoredEvidenceArtifact,
  StoredVerificationArtifact,
  VerificationSourceCategory,
} from "./types";

export const EVIDENCE_TARGET_MAX = 20;
export const EVIDENCE_ENTRY_MAX = 20;
export const EVIDENCE_CONTENT_MAX = 8_000;
export const EVIDENCE_TEXT_MAX = 2_000;
export const EVIDENCE_REQUEST_MAX = 30_000;

export const EVIDENCE_PAGE_TITLE = "Record Your Evidence";
export const EVIDENCE_PAGE_INTRO =
  "Verification records what happened when you performed a check. Evidence is the supporting material you choose to keep with that result.";
export const EVIDENCE_HONESTY_LINE =
  "A result is not Evidence by itself. Add material that supports what you observed, or record why Evidence is unavailable.";

export const EVIDENCE_STATUSES: readonly EvidenceStatus[] = [
  "not_addressed",
  "evidence_recorded",
  "evidence_unavailable",
];

export const EVIDENCE_STATUS_LABELS: Record<EvidenceStatus, string> = {
  not_addressed: "Not addressed yet",
  evidence_recorded: "Add supporting Evidence",
  evidence_unavailable: "Evidence is unavailable",
};

export const EVIDENCE_STATUS_DESCRIPTIONS: Record<EvidenceStatus, string> = {
  not_addressed: "You have not added Evidence or explained why it is unavailable.",
  evidence_recorded: "Add material that supports what you observed during the check.",
  evidence_unavailable: "Record why supporting material is not available.",
};

export const EVIDENCE_KIND_OPTIONS: readonly {
  value: EvidenceKind;
  label: string;
  guidance: string;
  placeholder: string;
  primary: boolean;
}[] = [
  {
    value: "screenshot_note",
    label: "Screenshot note",
    guidance: "Add a link or description that identifies the screenshot and what it shows.",
    placeholder: "https://example.com/screenshot or a precise screenshot description",
    primary: true,
  },
  {
    value: "terminal_output",
    label: "Terminal output",
    guidance: "Paste the relevant output from the check you performed.",
    placeholder: "Paste the relevant command output",
    primary: true,
  },
  {
    value: "test_output",
    label: "Test output",
    guidance: "Paste the relevant test result, including a useful failure when one occurred.",
    placeholder: "3 passed in 0.21s",
    primary: true,
  },
  {
    value: "changed_files",
    label: "Changed files",
    guidance: "List the files connected to this performed check.",
    placeholder: "app/routes/tasks.py\napp/models.py",
    primary: true,
  },
  {
    value: "note",
    label: "Observation",
    guidance: "Describe what you directly observed while performing the check.",
    placeholder: "Describe the behavior, error, or mismatch you directly observed",
    primary: true,
  },
  {
    value: "repo_url",
    label: "Repository URL",
    guidance: "Add the http(s) repository link connected to this implementation.",
    placeholder: "https://github.com/you/project",
    primary: false,
  },
  {
    value: "commit_hash",
    label: "Commit identifier",
    guidance: "Add the 7–40 character hexadecimal commit identifier.",
    placeholder: "a1b2c3d",
    primary: false,
  },
  {
    value: "app_url",
    label: "App URL",
    guidance: "Add the http(s) link where you performed or observed the check.",
    placeholder: "https://myapp.example.com",
    primary: false,
  },
  {
    value: "api_response",
    label: "API response",
    guidance: "Paste the relevant response you observed while performing the check.",
    placeholder: '{"id": 1, "status": "created"}',
    primary: false,
  },
];

const KIND_SET = new Set<EvidenceKind>(EVIDENCE_KIND_OPTIONS.map((kind) => kind.value));
const STATUS_SET = new Set<EvidenceStatus>(EVIDENCE_STATUSES);
const CATEGORY_SET = new Set<VerificationSourceCategory>([
  "behavior_change",
  "implementation_decision",
  "out_of_scope_change",
  "security_sensitive_area",
  "unresolved_risk",
  "unverified_behavior",
]);
const RESULT_SET = new Set<EvidenceHandoffResult>([
  "pass",
  "fail",
  "skipped",
  "not_applicable",
  "unrecorded",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isEvidenceEntry(value: unknown): value is EvidenceEntry {
  return (
    isRecord(value) &&
    typeof value.kind === "string" &&
    KIND_SET.has(value.kind as EvidenceKind) &&
    typeof value.content === "string"
  );
}

function isLinkedEvidenceTarget(value: unknown): value is LinkedEvidenceTarget {
  return (
    isRecord(value) &&
    typeof value.evidence_target_id === "string" &&
    typeof value.source_verification_target_id === "string" &&
    typeof value.category === "string" &&
    CATEGORY_SET.has(value.category as VerificationSourceCategory) &&
    typeof value.check_snapshot === "string" &&
    (value.verification_result_snapshot === "pass" ||
      value.verification_result_snapshot === "fail") &&
    isNullableString(value.verification_result_notes_snapshot) &&
    typeof value.evidence_status === "string" &&
    STATUS_SET.has(value.evidence_status as EvidenceStatus) &&
    Array.isArray(value.entries) &&
    value.entries.every(isEvidenceEntry) &&
    isNullableString(value.explanation) &&
    isNullableString(value.unavailable_reason)
  );
}

export function isLinkedEvidenceArtifact(value: unknown): value is LinkedEvidenceArtifact {
  return (
    isRecord(value) &&
    value.initialized_from_verification === true &&
    typeof value.stale === "boolean" &&
    typeof value.evidence_record_complete === "boolean" &&
    Array.isArray(value.entries) &&
    value.entries.every(isEvidenceEntry) &&
    isNullableString(value.summary ?? null) &&
    isNullableString(value.saved_at ?? null) &&
    Array.isArray(value.evidence_targets) &&
    value.evidence_targets.every(isLinkedEvidenceTarget)
  );
}

export type EvidenceArtifactMode = "none" | "linked" | "legacy" | "invalid_linked";

export function evidenceArtifactMode(value: unknown): EvidenceArtifactMode {
  if (value == null) return "none";
  if (isLinkedEvidenceArtifact(value)) return "linked";
  if (isRecord(value) && value.initialized_from_verification === true) {
    return "invalid_linked";
  }
  return "legacy";
}

export function isEvidenceHandoffPreview(value: unknown): value is EvidenceHandoffPreview {
  if (!isRecord(value) || !Array.isArray(value.targets)) return false;
  const modes = new Set(["unavailable", "manual_verification", "linked_verification"]);
  const states = new Set([
    "verification_required",
    "manual_verification",
    "current",
    "stale",
  ]);
  const valid = (
    typeof value.mode === "string" &&
    modes.has(value.mode) &&
    typeof value.verification_state === "string" &&
    states.has(value.verification_state) &&
    Number.isInteger(value.eligible_count) &&
    (value.eligible_count as number) >= 0 &&
    typeof value.guidance === "string" &&
    value.targets.every((target) => {
      if (!isRecord(target)) return false;
      const shapeIsValid = (
        typeof target.verification_target_id === "string" &&
        typeof target.category === "string" &&
        CATEGORY_SET.has(target.category as VerificationSourceCategory) &&
        typeof target.check === "string" &&
        typeof target.result === "string" &&
        RESULT_SET.has(target.result as EvidenceHandoffResult) &&
        isNullableString(target.result_notes) &&
        typeof target.performed === "boolean" &&
        (target.eligibility === "eligible" || target.eligibility === "ineligible") &&
        (target.ineligibility_reason === null ||
          target.ineligibility_reason === "verification_stale" ||
          target.ineligibility_reason === "not_performed")
      );
      if (!shapeIsValid) return false;
      const performedResult = target.result === "pass" || target.result === "fail";
      if (target.performed !== performedResult) return false;
      if (target.eligibility === "eligible") {
        return target.performed === true && target.ineligibility_reason === null;
      }
      return true;
    })
  );
  if (!valid) return false;
  return value.eligible_count === value.targets.filter(
    (target) => target.eligibility === "eligible"
  ).length;
}

export type EvidencePreviewState =
  | "verification_required"
  | "manual_verification"
  | "stale_verification"
  | "incomplete_verification"
  | "ready"
  | "zero_eligible";

export function evidencePreviewState(preview: EvidenceHandoffPreview): EvidencePreviewState {
  if (preview.mode === "manual_verification") return "manual_verification";
  if (preview.verification_state === "verification_required") return "verification_required";
  if (preview.verification_state === "stale") return "stale_verification";
  if (preview.targets.some((target) => target.result === "unrecorded")) {
    return "incomplete_verification";
  }
  return preview.eligible_count > 0 ? "ready" : "zero_eligible";
}

export function eligibleEvidenceTargets(
  preview: EvidenceHandoffPreview
): EvidenceHandoffTarget[] {
  return preview.targets.filter((target) => target.eligibility === "eligible");
}

export function ineligibleEvidenceTargets(
  preview: EvidenceHandoffPreview
): EvidenceHandoffTarget[] {
  return preview.targets.filter((target) => target.eligibility === "ineligible");
}

export function normalizeEvidenceSelection(
  preview: EvidenceHandoffPreview,
  selectedIds: readonly string[]
): string[] {
  const eligible = new Set(
    preview.targets
      .filter((target) => target.eligibility === "eligible")
      .map((target) => target.verification_target_id)
  );
  const selected = new Set(selectedIds);
  return preview.targets
    .map((target) => target.verification_target_id)
    .filter((targetId) => eligible.has(targetId) && selected.has(targetId));
}

export function selectedEvidenceTargetCount(selectedIds: readonly string[]): number {
  return new Set(selectedIds).size;
}

export function updateEvidenceSelection(
  preview: EvidenceHandoffPreview,
  selectedIds: readonly string[],
  targetId: string,
  checked: boolean
): { selectedIds: string[]; limitReached: boolean } {
  const current = normalizeEvidenceSelection(preview, selectedIds);
  if (!checked) {
    return {
      selectedIds: current.filter((id) => id !== targetId),
      limitReached: false,
    };
  }
  const targetIsEligible = eligibleEvidenceTargets(preview).some(
    (target) => target.verification_target_id === targetId
  );
  if (!targetIsEligible || current.includes(targetId)) {
    return { selectedIds: current, limitReached: false };
  }
  if (current.length >= EVIDENCE_TARGET_MAX) {
    return { selectedIds: current, limitReached: true };
  }
  return {
    selectedIds: normalizeEvidenceSelection(preview, [...current, targetId]),
    limitReached: false,
  };
}

export function evidenceInitializationBody(
  selectedVerificationTargetIds: readonly string[],
  replaceExisting: boolean
): EvidenceInitializationRequest {
  return {
    selected_verification_target_ids: [...selectedVerificationTargetIds],
    ...(replaceExisting ? { replace_existing: true as const } : {}),
  };
}

export function evidenceResultLabel(result: EvidenceHandoffResult): string {
  return {
    pass: "Passed",
    fail: "Failed",
    skipped: "Skipped",
    not_applicable: "Not applicable",
    unrecorded: "Not recorded yet",
  }[result];
}

export function evidenceResultDescription(result: EvidenceHandoffResult): string {
  return {
    pass: "You performed the check and observed the expected behavior.",
    fail: "You performed the check and observed a problem or mismatch.",
    skipped: "You recorded that this check was not performed.",
    not_applicable: "You recorded that this check does not apply.",
    unrecorded: "No result has been saved for this check.",
  }[result];
}

export function evidenceStatusLabel(status: EvidenceStatus): string {
  return EVIDENCE_STATUS_LABELS[status];
}

export function evidenceStatusDescription(status: EvidenceStatus): string {
  return EVIDENCE_STATUS_DESCRIPTIONS[status];
}

export function evidenceKindLabel(kind: EvidenceKind): string {
  return EVIDENCE_KIND_OPTIONS.find((option) => option.value === kind)?.label ?? "Evidence";
}

export function evidenceKindOption(kind: EvidenceKind) {
  return EVIDENCE_KIND_OPTIONS.find((option) => option.value === kind) ?? EVIDENCE_KIND_OPTIONS[0];
}

export function evidenceCharacterCount(value: string): number {
  return Array.from(value).length;
}

function hasUnsafeControl(value: string): boolean {
  return Array.from(value).some((character) => {
    const code = character.codePointAt(0) ?? 0;
    return ((code >= 0 && code <= 31) || (code >= 127 && code <= 159)) &&
      character !== "\t" && character !== "\n" && character !== "\r";
  });
}

export function normalizeEvidenceEntry(entry: EvidenceEntry): EvidenceEntry {
  return { kind: entry.kind, content: entry.content };
}

export function validateEvidenceEntry(entry: EvidenceEntry): string | null {
  if (!entry.content.trim()) return "Add the Evidence content before saving.";
  if (evidenceCharacterCount(entry.content) > EVIDENCE_CONTENT_MAX) {
    return `Keep this entry within ${EVIDENCE_CONTENT_MAX.toLocaleString()} characters.`;
  }
  if (hasUnsafeControl(entry.content)) {
    return "This Evidence contains an unsupported control character.";
  }
  if (entry.kind === "repo_url" || entry.kind === "app_url") {
    if (
      !entry.content.startsWith("http://") &&
      !entry.content.startsWith("https://")
    ) {
      return "Use a complete http(s) URL.";
    }
    if (evidenceCharacterCount(entry.content) > 2_048) {
      return "Keep this URL within 2,048 characters.";
    }
  }
  if (entry.kind === "commit_hash" && !/^[0-9a-fA-F]{7,40}$/.test(entry.content)) {
    return "Use a 7–40 character hexadecimal commit identifier.";
  }
  return null;
}

export interface LinkedEvidenceTargetForm {
  status: EvidenceStatus;
  entries: EvidenceEntry[];
  explanation: string;
  unavailableReason: string;
}

export type LinkedEvidenceFormState = Record<string, LinkedEvidenceTargetForm>;

export function targetFormFromEvidence(
  evidence: LinkedEvidenceArtifact
): LinkedEvidenceFormState {
  return Object.fromEntries(
    evidence.evidence_targets.map((target) => [
      target.evidence_target_id,
      {
        status: target.evidence_status,
        entries: target.entries.map(normalizeEvidenceEntry),
        explanation: target.explanation ?? "",
        unavailableReason: target.unavailable_reason ?? "",
      },
    ])
  );
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

export function canonicalEvidenceTargetUpdate(
  target: Pick<LinkedEvidenceTarget, "evidence_target_id">,
  form: LinkedEvidenceTargetForm
): EvidenceTargetUpdateRequest {
  if (form.status === "not_addressed") {
    return {
      evidence_target_id: target.evidence_target_id,
      evidence_status: "not_addressed",
    };
  }
  if (form.status === "evidence_unavailable") {
    return {
      evidence_target_id: target.evidence_target_id,
      evidence_status: "evidence_unavailable",
      unavailable_reason: form.unavailableReason.trim(),
    };
  }
  return {
    evidence_target_id: target.evidence_target_id,
    evidence_status: "evidence_recorded",
    entries: form.entries.map(normalizeEvidenceEntry),
    explanation: optionalText(form.explanation),
  };
}

function storedTargetUpdate(target: LinkedEvidenceTarget): EvidenceTargetUpdateRequest {
  return canonicalEvidenceTargetUpdate(target, {
    status: target.evidence_status,
    entries: target.entries,
    explanation: target.explanation ?? "",
    unavailableReason: target.unavailable_reason ?? "",
  });
}

export function deriveEvidenceSavePayload(
  evidence: LinkedEvidenceArtifact,
  state: LinkedEvidenceFormState
): EvidenceSaveRequest {
  const target_updates = evidence.evidence_targets.flatMap((target) => {
    const form = state[target.evidence_target_id];
    if (!form) return [];
    const update = canonicalEvidenceTargetUpdate(target, form);
    return JSON.stringify(update) === JSON.stringify(storedTargetUpdate(target))
      ? []
      : [update];
  });
  return { target_updates };
}

export function isLinkedEvidenceDirty(
  evidence: LinkedEvidenceArtifact,
  state: LinkedEvidenceFormState
): boolean {
  if (Object.keys(state).length !== evidence.evidence_targets.length) return true;
  return evidence.evidence_targets.some((target) => {
    const form = state[target.evidence_target_id];
    return (
      !form ||
      JSON.stringify(canonicalEvidenceTargetUpdate(target, form)) !==
        JSON.stringify(storedTargetUpdate(target))
    );
  });
}

export interface EvidenceTargetValidation {
  entries?: string;
  explanation?: string;
  unavailableReason?: string;
}

export function validateEvidenceTarget(
  form: LinkedEvidenceTargetForm | undefined
): EvidenceTargetValidation {
  if (!form) return { entries: "Reload this page—the Evidence draft no longer matches." };
  const errors: EvidenceTargetValidation = {};
  if (form.status === "evidence_recorded") {
    if (form.entries.length === 0) {
      errors.entries = "Add at least one Evidence entry for this record.";
    } else if (form.entries.length > EVIDENCE_ENTRY_MAX) {
      errors.entries = `Use at most ${EVIDENCE_ENTRY_MAX} entries in this phase.`;
    } else {
      const entryError = form.entries.map(validateEvidenceEntry).find(Boolean);
      if (entryError) errors.entries = entryError;
      const identities = form.entries.map((entry) => `${entry.kind}\u0000${entry.content}`);
      if (new Set(identities).size !== identities.length) {
        errors.entries = "Remove the duplicate Evidence entry before saving.";
      }
    }
    if (evidenceCharacterCount(form.explanation) > EVIDENCE_TEXT_MAX) {
      errors.explanation = `Keep this explanation within ${EVIDENCE_TEXT_MAX.toLocaleString()} characters.`;
    } else if (hasUnsafeControl(form.explanation)) {
      errors.explanation = "This explanation contains an unsupported control character.";
    }
  }
  if (form.status === "evidence_unavailable") {
    if (!form.unavailableReason.trim()) {
      errors.unavailableReason = "Explain why supporting Evidence is unavailable.";
    } else if (evidenceCharacterCount(form.unavailableReason) > EVIDENCE_TEXT_MAX) {
      errors.unavailableReason = `Keep this reason within ${EVIDENCE_TEXT_MAX.toLocaleString()} characters.`;
    } else if (hasUnsafeControl(form.unavailableReason)) {
      errors.unavailableReason = "This reason contains an unsupported control character.";
    }
  }
  return errors;
}

function pythonJsonCharacterCount(value: unknown): number {
  if (value === null) return 4;
  if (typeof value === "string") return evidenceCharacterCount(JSON.stringify(value));
  if (typeof value === "number" || typeof value === "boolean") {
    return evidenceCharacterCount(JSON.stringify(value));
  }
  if (Array.isArray(value)) {
    return 2 + value.reduce((total, item, index) =>
      total + pythonJsonCharacterCount(item) + (index > 0 ? 2 : 0), 0);
  }
  if (isRecord(value)) {
    const entries = Object.entries(value).filter(([, item]) => item !== undefined);
    return 2 + entries.reduce((total, [key, item], index) =>
      total + pythonJsonCharacterCount(key) + 2 + pythonJsonCharacterCount(item) +
        (index > 0 ? 2 : 0), 0);
  }
  return 0;
}

export function evidenceRequestCharacterCount(payload: EvidenceSaveRequest): number {
  return pythonJsonCharacterCount(payload);
}

export function evidenceFormBlocker(
  evidence: LinkedEvidenceArtifact,
  state: LinkedEvidenceFormState
): string | null {
  let entryCount = 0;
  for (const target of evidence.evidence_targets) {
    const form = state[target.evidence_target_id];
    if (form?.status === "evidence_recorded") entryCount += form.entries.length;
    const errors = validateEvidenceTarget(form);
    const first = errors.entries ?? errors.explanation ?? errors.unavailableReason;
    if (first) return first;
  }
  if (entryCount > EVIDENCE_ENTRY_MAX) {
    return `Linked Evidence may contain at most ${EVIDENCE_ENTRY_MAX} entries in this phase.`;
  }
  const payload = deriveEvidenceSavePayload(evidence, state);
  if (evidenceRequestCharacterCount(payload) > EVIDENCE_REQUEST_MAX) {
    return "This Evidence update is too large to save. Trim pasted output and try again.";
  }
  return null;
}

export interface EvidenceProgress {
  addressed: number;
  recorded: number;
  unavailable: number;
  unaddressed: number;
  entries: number;
  total: number;
}

export function linkedEvidenceProgress(
  evidence: LinkedEvidenceArtifact,
  state: LinkedEvidenceFormState
): EvidenceProgress {
  const forms = evidence.evidence_targets.map((target) => state[target.evidence_target_id]);
  const recorded = forms.filter((form) => form?.status === "evidence_recorded").length;
  const unavailable = forms.filter((form) => form?.status === "evidence_unavailable").length;
  const total = evidence.evidence_targets.length;
  return {
    addressed: recorded + unavailable,
    recorded,
    unavailable,
    unaddressed: total - recorded - unavailable,
    entries: forms.reduce(
      (count, form) => count + (form?.status === "evidence_recorded" ? form.entries.length : 0),
      0
    ),
    total,
  };
}

export function savedLinkedEvidenceProgress(
  evidence: LinkedEvidenceArtifact
): EvidenceProgress {
  return linkedEvidenceProgress(evidence, targetFormFromEvidence(evidence));
}

export function evidenceCompletionSummary(progress: EvidenceProgress): string {
  return `${progress.addressed} of ${progress.total} Evidence records addressed`;
}

function evidenceFingerprint(evidence: LinkedEvidenceArtifact): string {
  const input = [
    evidence.saved_at ?? "unsaved",
    ...evidence.evidence_targets.map((target) => target.evidence_target_id),
  ].join("\n");
  let hash = 0x811c9dc5;
  for (const character of input) {
    hash ^= character.codePointAt(0) ?? 0;
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function linkedEvidenceDraftSurface(
  phase: number,
  evidence: LinkedEvidenceArtifact
): string {
  return `linked_evidence:active-project:${phase}:${evidenceFingerprint(evidence)}`;
}

export interface LinkedEvidenceDraft {
  fingerprint: string;
  targets: LinkedEvidenceFormState;
}

export function linkedEvidenceDraftValue(
  evidence: LinkedEvidenceArtifact,
  state: LinkedEvidenceFormState
): LinkedEvidenceDraft {
  return { fingerprint: evidenceFingerprint(evidence), targets: state };
}

export function restoreLinkedEvidenceDraft(
  evidence: LinkedEvidenceArtifact,
  value: unknown
): LinkedEvidenceFormState | null {
  if (evidence.stale || !isRecord(value) || !isRecord(value.targets)) return null;
  if (value.fingerprint !== evidenceFingerprint(evidence)) return null;
  const expectedIds = evidence.evidence_targets.map((target) => target.evidence_target_id);
  const storedIds = Object.keys(value.targets);
  if (
    expectedIds.length !== storedIds.length ||
    expectedIds.some((targetId) => !storedIds.includes(targetId))
  ) return null;
  const restored: LinkedEvidenceFormState = {};
  for (const targetId of expectedIds) {
    const candidate = value.targets[targetId];
    if (
      !isRecord(candidate) ||
      typeof candidate.status !== "string" ||
      !STATUS_SET.has(candidate.status as EvidenceStatus) ||
      !Array.isArray(candidate.entries) ||
      !candidate.entries.every(isEvidenceEntry) ||
      typeof candidate.explanation !== "string" ||
      typeof candidate.unavailableReason !== "string"
    ) return null;
    restored[targetId] = {
      status: candidate.status as EvidenceStatus,
      entries: candidate.entries.map(normalizeEvidenceEntry),
      explanation: candidate.explanation,
      unavailableReason: candidate.unavailableReason,
    };
  }
  return restored;
}

export function linkedEvidenceServerRevision(evidence: LinkedEvidenceArtifact): string {
  return JSON.stringify({
    savedAt: evidence.saved_at ?? null,
    stale: evidence.stale,
    complete: evidence.evidence_record_complete,
    fingerprint: evidenceFingerprint(evidence),
    targets: evidence.evidence_targets.map((target) => storedTargetUpdate(target)),
  });
}

export function shouldKeepEvidenceSaveNotice(
  acknowledgedRevision: string | null,
  serverRevision: string
): boolean {
  return acknowledgedRevision === serverRevision;
}

export function canRebuildEvidenceFromPreview(preview: EvidenceHandoffPreview | null): boolean {
  return preview != null && evidencePreviewState(preview) === "ready";
}

export function evidenceStepStatus(
  evidence: StoredEvidenceArtifact | null,
  verification: StoredVerificationArtifact | null
): { label: string; tone: "idle" | "draft" | "done" | "stale" } {
  if (!evidence) {
    if (!isLinkedVerificationArtifact(verification) || verification.stale) {
      return { label: "not available yet", tone: "idle" };
    }
    const recorded = linkedVerificationRecorded(
      verification,
      targetFormFromVerification(verification)
    );
    return recorded || verification.verification_targets.length === 0
      ? { label: "ready to start", tone: "draft" }
      : { label: "not available yet", tone: "idle" };
  }
  if (!isLinkedEvidenceArtifact(evidence)) return { label: "saved", tone: "done" };
  if (evidence.stale) return { label: "stale", tone: "stale" };
  if (evidence.evidence_record_complete) return { label: "record complete", tone: "done" };
  return { label: "in progress", tone: "draft" };
}

export function safeEvidenceLink(entry: EvidenceEntry): string | null {
  if (entry.kind !== "repo_url" && entry.kind !== "app_url") return null;
  return validateEvidenceEntry(entry) === null ? entry.content : null;
}
