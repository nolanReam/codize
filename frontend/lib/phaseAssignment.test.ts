import { describe, expect, it } from "vitest";

import { assignmentSwitchProtection } from "./phaseAssignment";
import type { PromptBuilderInputs } from "./promptBuilder";

const EMPTY: PromptBuilderInputs = {
  projectGoal: "",
  phaseGoal: "",
  aiTask: "",
  files: "",
  constraints: "",
  doNotChange: "",
  planFirst: true,
  wantChecks: true,
  uncertainty: "",
};

describe("assignmentSwitchProtection", () => {
  it("does not warn for the same task or an empty new assignment", () => {
    expect(assignmentSwitchProtection("ai-1", "ai-1", EMPTY, null)).toBeNull();
    expect(assignmentSwitchProtection("ai-1", "ai-2", EMPTY, null)).toBeNull();
  });

  it("preserves an unsaved assignment-specific draft", () => {
    expect(
      assignmentSwitchProtection("ai-1", "ai-2", { ...EMPTY, aiTask: "my careful ask" }, null)
    ).toEqual({ hasDraft: true, hasSavedPrompt: false, savedPromptIsLegacy: false });
  });

  it("warns for the current task's saved Prompt but not an unrelated saved Prompt", () => {
    const current = { inputs: {}, generated_prompt: "A", assignment_task_id: "ai-1" };
    expect(assignmentSwitchProtection("ai-1", "ai-2", EMPTY, current)?.hasSavedPrompt).toBe(true);
    expect(
      assignmentSwitchProtection("ai-1", "ai-2", EMPTY, { ...current, assignment_task_id: "ai-3" })
    ).toBeNull();
  });

  it("keeps legacy Prompts explicitly unassigned", () => {
    const result = assignmentSwitchProtection(
      "ai-1",
      "human-1",
      EMPTY,
      { inputs: {}, generated_prompt: "legacy" }
    );
    expect(result).toEqual({ hasDraft: false, hasSavedPrompt: true, savedPromptIsLegacy: true });
  });
});
