import { describe, expect, it } from "vitest";

import {
  BOUNDED_ASSIGNMENT_OBJECTIVE_ID,
  BOUNDED_ASSIGNMENT_OBJECTIVE_NAME,
  EMPTY_SCOPE_PRACTICE,
  normalizeScopePracticeDraft,
  scopeApplication,
  scopeApplicationConflicts,
  scopeApplicationIsCurrent,
  scopeSubmission,
  validateScopePractice,
  type ScopePracticeDraft,
} from "./boundedAssignment";
import type { PromptBuilderInputs } from "./promptBuilder";

const SCOPE: ScopePracticeDraft = {
  finishCondition: "A study-session form exists.",
  excludedWork: "Accounts and reminders stay for later.",
  inspectionCondition: "The form structure is visible on the page.",
  applied: null,
};

const INPUTS: PromptBuilderInputs = {
  projectGoal: "StudyFlow",
  phaseGoal: "",
  aiTask: "",
  files: "",
  constraints: "",
  doNotChange: "",
  planFirst: true,
  wantChecks: true,
  uncertainty: "",
};

describe("bounded assignment authority", () => {
  it("uses one stable objective without a score or mastery claim", () => {
    expect(BOUNDED_ASSIGNMENT_OBJECTIVE_ID).toBe("bounded_assignment_v1");
    expect(BOUNDED_ASSIGNMENT_OBJECTIVE_NAME).toBe(
      "Keep one AI request bounded and checkable"
    );
    expect(BOUNDED_ASSIGNMENT_OBJECTIVE_NAME).not.toMatch(/score|master|pass/i);
  });

  it("checks only deterministic presence and bounded safe text", () => {
    expect(validateScopePractice(SCOPE)).toEqual({ errors: {}, complete: true });
    expect(validateScopePractice({ ...SCOPE, finishCondition: " " })).toMatchObject({
      complete: false,
      errors: { finishCondition: expect.any(String) },
    });
    expect(
      validateScopePractice({ ...SCOPE, excludedWork: "x".repeat(801) }).errors
        .excludedWork
    ).toContain("800");
    expect(
      validateScopePractice({ ...SCOPE, inspectionCondition: "route\u0000ready" })
        .errors.inspectionCondition
    ).toContain("control");
    expect(
      validateScopePractice({ ...SCOPE, finishCondition: "key sb_secret_example" })
        .errors.finishCondition
    ).toContain("secret");
  });

  it("trims only final submissions while drafts preserve ordinary line breaks", () => {
    const draft = { ...SCOPE, finishCondition: "  first line\nsecond line  " };
    expect(scopeSubmission(draft).finish_condition).toBe("first line\nsecond line");
    expect(draft.finishCondition).toBe("  first line\nsecond line  ");
  });
});
describe("apply scope to Prompt", () => {
  it("uses the student's decisions once without fabricating Context", () => {
    const applied = scopeApplication(SCOPE);
    expect(applied.taskText).toContain(SCOPE.finishCondition);
    expect(applied.taskText).toContain(SCOPE.inspectionCondition);
    expect(applied.guardrailText).toContain(SCOPE.excludedWork);
    expect(applied.taskText).not.toContain(INPUTS.projectGoal);
  });

  it("is idempotent and detects only non-empty field conflicts", () => {
    const applied = scopeApplication(SCOPE);
    expect(scopeApplicationIsCurrent(SCOPE, applied)).toBe(true);
    expect(scopeApplicationConflicts(INPUTS, null, applied)).toEqual({
      task: false,
      guardrail: false,
    });
    expect(
      scopeApplicationConflicts(
        { ...INPUTS, aiTask: applied.taskText, doNotChange: applied.guardrailText },
        applied,
        applied
      )
    ).toEqual({ task: false, guardrail: false });
    expect(
      scopeApplicationConflicts(
        { ...INPUTS, aiTask: "Keep my manual Task", doNotChange: "Keep this fence" },
        applied,
        applied
      )
    ).toEqual({ task: true, guardrail: true });
  });
});

describe("local draft compatibility", () => {
  it("normalizes corrupt shapes without treating them as authority", () => {
    expect(normalizeScopePracticeDraft("{bad")).toBeNull();
    expect(
      normalizeScopePracticeDraft({
        finishCondition: 42,
        excludedWork: ["wrong"],
        inspectionCondition: "visible",
        applied: { taskText: false, guardrailText: "x" },
      })
    ).toEqual({
      ...EMPTY_SCOPE_PRACTICE,
      inspectionCondition: "visible",
    });
  });
});
