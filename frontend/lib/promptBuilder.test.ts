import { describe, expect, it } from "vitest";

import { buildPrompt, promptInputsHaveStudentWork, type PromptBuilderInputs } from "./promptBuilder";

const INPUTS: PromptBuilderInputs = {
  projectGoal: "a volleyball league tracker",
  phaseGoal: "the match-creation endpoint",
  aiTask: "add a POST /matches route that validates team ids",
  files: "app/routes/matches.py",
  constraints: "FastAPI, async handlers",
  doNotChange: "main.py or the database schema",
  planFirst: true,
  wantChecks: true,
  uncertainty: "the nested team validation",
};

describe("buildPrompt", () => {
  it("is deterministic", () => {
    expect(buildPrompt(INPUTS)).toEqual(buildPrompt(INPUTS));
  });

  it("includes every provided input in the prompt", () => {
    const { prompt } = buildPrompt(INPUTS);
    for (const text of [
      "volleyball league tracker",
      "match-creation endpoint",
      "POST /matches",
      "app/routes/matches.py",
      "FastAPI, async handlers",
      "Do NOT change: main.py",
      "the nested team validation",
    ]) {
      expect(prompt).toContain(text);
    }
  });

  it("adds plan-first and verification lines only when asked", () => {
    const withBoth = buildPrompt(INPUTS).prompt;
    expect(withBoth).toContain("Before writing any code");
    expect(withBoth).toContain("manually verify");

    const without = buildPrompt({ ...INPUTS, planFirst: false, wantChecks: false }).prompt;
    expect(without).not.toContain("Before writing any code");
    expect(without).not.toContain("manually verify");
  });

  it("always fences scope and surfaces assumptions", () => {
    const { prompt } = buildPrompt({ ...INPUTS, planFirst: false, wantChecks: false });
    expect(prompt).toContain("Do not touch anything outside the scope");
    expect(prompt).toContain("assumption");
  });

  it("stays under the backend's 8000-char cap", () => {
    const huge = { ...INPUTS, constraints: "x".repeat(20000) };
    expect(buildPrompt(huge).prompt.length).toBeLessThanOrEqual(7900);
  });

  it("produces a contrasting bad prompt and a non-empty explanation", () => {
    const { badPrompt, whyStronger, prompt } = buildPrompt(INPUTS);
    expect(badPrompt).toContain("Make it work");
    expect(badPrompt.length).toBeLessThan(prompt.length);
    expect(whyStronger).toContain("scopes the request");
  });
});

describe("promptInputsHaveStudentWork", () => {
  it("ignores default toggles but detects authored fields", () => {
    const empty = { ...INPUTS, projectGoal: "", phaseGoal: "", aiTask: "", files: "", constraints: "", doNotChange: "", uncertainty: "" };
    expect(promptInputsHaveStudentWork(empty)).toBe(false);
    expect(promptInputsHaveStudentWork({ ...empty, aiTask: "one bounded task" })).toBe(true);
  });
});
