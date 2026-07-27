import type { PromptBuilderInputs } from "./promptBuilder";

export const BOUNDED_ASSIGNMENT_OBJECTIVE_ID = "bounded_assignment_v1" as const;
export const BOUNDED_ASSIGNMENT_OBJECTIVE_VERSION = 1 as const;
export const BOUNDED_ASSIGNMENT_OBJECTIVE_NAME =
  "Keep one AI request bounded and checkable";
export const SCOPE_PRACTICE_MAX_CODE_POINTS = 800;

export interface ScopePracticeFields {
  finishCondition: string;
  excludedWork: string;
  inspectionCondition: string;
}

export interface ScopeApplicationSnapshot {
  taskText: string;
  guardrailText: string;
}

export interface ScopePracticeDraft extends ScopePracticeFields {
  applied: ScopeApplicationSnapshot | null;
}

export interface ScopePracticeSubmission {
  finish_condition: string;
  excluded_work: string;
  inspection_condition: string;
}

export interface StoredScopePractice extends ScopePracticeSubmission {
  objective_id: typeof BOUNDED_ASSIGNMENT_OBJECTIVE_ID;
  objective_version: typeof BOUNDED_ASSIGNMENT_OBJECTIVE_VERSION;
  assignment_task_id: string;
  assignment_revision: string;
}

export type ScopeFieldName = keyof ScopePracticeFields;
export type ScopeFieldErrors = Partial<Record<ScopeFieldName, string>>;

export const EMPTY_SCOPE_PRACTICE: ScopePracticeDraft = {
  finishCondition: "",
  excludedWork: "",
  inspectionCondition: "",
  applied: null,
};

const CONTROL_CHARACTER = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/u;
const SECRET_MARKERS = ["sb_secret_", "sk-or-", "AIza", "-----BEGIN "];

export function codePointLength(value: string): number {
  return Array.from(value).length;
}

export function scopePracticeHasStudentWork(
  scope: Pick<ScopePracticeFields, ScopeFieldName> | null
): boolean {
  return Boolean(
    scope &&
      [scope.finishCondition, scope.excludedWork, scope.inspectionCondition].some(
        (value) => typeof value === "string" && value.trim().length > 0
      )
  );
}

export function validateScopeField(value: string): string | null {
  if (!value.trim()) return "Add your decision for this planning piece.";
  if (codePointLength(value.trim()) > SCOPE_PRACTICE_MAX_CODE_POINTS) {
    return `Keep this response to ${SCOPE_PRACTICE_MAX_CODE_POINTS} characters or fewer.`;
  }
  if (CONTROL_CHARACTER.test(value)) {
    return "Remove unsupported control characters before continuing.";
  }
  if (SECRET_MARKERS.some((marker) => value.includes(marker))) {
    return "Remove the API key or secret before continuing.";
  }
  return null;
}

export function validateScopePractice(scope: ScopePracticeFields): {
  errors: ScopeFieldErrors;
  complete: boolean;
} {
  const errors: ScopeFieldErrors = {};
  const values: Array<[ScopeFieldName, string]> = [
    ["finishCondition", scope.finishCondition],
    ["excludedWork", scope.excludedWork],
    ["inspectionCondition", scope.inspectionCondition],
  ];
  for (const [field, value] of values) {
    const error = validateScopeField(value);
    if (error) errors[field] = error;
  }
  return { errors, complete: Object.keys(errors).length === 0 };
}

export function scopeSubmission(
  scope: ScopePracticeFields
): ScopePracticeSubmission {
  return {
    finish_condition: scope.finishCondition.trim(),
    excluded_work: scope.excludedWork.trim(),
    inspection_condition: scope.inspectionCondition.trim(),
  };
}

export function scopeFromStored(scope: StoredScopePractice): ScopePracticeDraft {
  return {
    finishCondition: scope.finish_condition,
    excludedWork: scope.excluded_work,
    inspectionCondition: scope.inspection_condition,
    applied: null,
  };
}

export function normalizeStoredScopePractice(raw: unknown): StoredScopePractice | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const candidate = raw as Record<string, unknown>;
  if (
    candidate.objective_id !== BOUNDED_ASSIGNMENT_OBJECTIVE_ID ||
    candidate.objective_version !== BOUNDED_ASSIGNMENT_OBJECTIVE_VERSION ||
    typeof candidate.assignment_task_id !== "string" ||
    !/^[0-9a-f]{64}$/.test(
      typeof candidate.assignment_revision === "string"
        ? candidate.assignment_revision
        : ""
    ) ||
    typeof candidate.finish_condition !== "string" ||
    typeof candidate.excluded_work !== "string" ||
    typeof candidate.inspection_condition !== "string"
  ) {
    return null;
  }
  return candidate as unknown as StoredScopePractice;
}

export function normalizeScopePracticeDraft(raw: unknown): ScopePracticeDraft | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const candidate = raw as Record<string, unknown>;
  const finishCondition =
    typeof candidate.finishCondition === "string" ? candidate.finishCondition : "";
  const excludedWork =
    typeof candidate.excludedWork === "string" ? candidate.excludedWork : "";
  const inspectionCondition =
    typeof candidate.inspectionCondition === "string" ? candidate.inspectionCondition : "";
  let applied: ScopeApplicationSnapshot | null = null;
  if (
    candidate.applied &&
    typeof candidate.applied === "object" &&
    !Array.isArray(candidate.applied)
  ) {
    const rawApplied = candidate.applied as Record<string, unknown>;
    if (
      typeof rawApplied.taskText === "string" &&
      typeof rawApplied.guardrailText === "string"
    ) {
      applied = {
        taskText: rawApplied.taskText,
        guardrailText: rawApplied.guardrailText,
      };
    }
  }
  return { finishCondition, excludedWork, inspectionCondition, applied };
}

export function scopeApplication(
  scope: ScopePracticeFields,
  assignment: string
): ScopeApplicationSnapshot {
  const submitted = scopeSubmission(scope);
  return {
    taskText: [
      `Selected assignment: ${assignment.trim()}`,
      `Finish condition: ${submitted.finish_condition}`,
      `Ready to inspect when: ${submitted.inspection_condition}`,
    ].join("\n"),
    guardrailText: `Excluded from this request: ${submitted.excluded_work}`,
  };
}

export function scopeApplicationIsCurrent(
  scope: ScopePracticeFields,
  applied: ScopeApplicationSnapshot | null,
  assignment: string
): boolean {
  if (!applied) return false;
  const current = scopeApplication(scope, assignment);
  return (
    applied.taskText === current.taskText &&
    applied.guardrailText === current.guardrailText
  );
}

export function promptArtifactMatchesAssignment(
  artifact: {
    assignment_task_id?: string | null;
    scope_practice?: unknown;
  } | null,
  assignment: { task_id: string },
  assignmentRevision: string
): boolean {
  if (!artifact || artifact.assignment_task_id !== assignment.task_id) return false;
  const storedScope = normalizeStoredScopePractice(artifact.scope_practice);
  return !storedScope || storedScope.assignment_revision === assignmentRevision;
}

export function scopeApplicationConflicts(
  inputs: PromptBuilderInputs,
  applied: ScopeApplicationSnapshot | null,
  proposed: ScopeApplicationSnapshot
): { task: boolean; guardrail: boolean } {
  const task = inputs.aiTask.trim();
  const guardrail = inputs.doNotChange.trim();
  return {
    task: Boolean(
      task &&
        task !== proposed.taskText &&
        (!applied || task !== applied.taskText)
    ),
    guardrail: Boolean(
      guardrail &&
        guardrail !== proposed.guardrailText &&
        (!applied || guardrail !== applied.guardrailText)
    ),
  };
}
