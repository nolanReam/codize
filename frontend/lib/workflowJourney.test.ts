import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { GUIDED_JOURNEY } from "./guidedProjectNavigation";
import { WORKFLOW_JOURNEY } from "./workflowJourney";

const EXPECTED = [
  "Prompt Builder",
  "Bring Back What Changed",
  "Change Map",
  "Review",
  "Verification",
  "Evidence",
  "Project Defense",
  "Defense Report",
];

describe("canonical eight-stage Journey", () => {
  it("is exact, ordered, and shared by guided navigation", () => {
    expect(WORKFLOW_JOURNEY).toHaveLength(8);
    expect(WORKFLOW_JOURNEY.map((stage) => stage.label)).toEqual(EXPECTED);
    expect(GUIDED_JOURNEY).toBe(WORKFLOW_JOURNEY);
  });

  it("drives tutorial, compact overview, and landing panel", () => {
    for (const file of [
      "components/Tutorial.tsx",
      "components/LoopOverview.tsx",
      "components/BuildLoopPanel.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).toContain("WORKFLOW_JOURNEY.map");
    }
    const landing = readFileSync(resolve(process.cwd(), "components/BuildLoopPanel.tsx"), "utf8");
    expect(landing).not.toMatch(/title:\s*["'](?:Plan|Generate|Commit \/ Reflect)["']/);
  });
});
