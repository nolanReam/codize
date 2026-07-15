import { describe, expect, it } from "vitest";

import { GUIDED_JOURNEY } from "./guidedProjectNavigation";
import { WORKFLOW_GUIDANCE } from "./workflowGuidance";

describe("shared adaptive workflow guidance", () => {
  it("covers every existing M16N stage without creating another journey", () => {
    expect(Object.keys(WORKFLOW_GUIDANCE)).toEqual(GUIDED_JOURNEY.map((stage) => stage.id));
  });

  it("preserves trust language for Change Map, Verification, Evidence, Defense, and Report", () => {
    expect(WORKFLOW_GUIDANCE.change_map.action).toContain("do not prove");
    expect(WORKFLOW_GUIDANCE.review.action).toContain("does not mean Verified");
    expect(WORKFLOW_GUIDANCE.verification.action).toContain("Codize did not observe");
    expect(WORKFLOW_GUIDANCE.verification.action).toContain("Skipped and Not applicable");
    expect(WORKFLOW_GUIDANCE.evidence.action).toContain("unavailable Evidence stays unavailable");
    expect(WORKFLOW_GUIDANCE.defense.action).toContain("do not answer for you");
    expect(WORKFLOW_GUIDANCE.defense.action).toContain("Evidence does not guarantee PASS");
    expect(WORKFLOW_GUIDANCE.report.action).toContain("PASS/FAIL");
  });

  it("keeps recovery emphasis contextual and static", () => {
    expect(WORKFLOW_GUIDANCE.import.recovery).toContain("most recent AI change");
    expect(WORKFLOW_GUIDANCE.prompt.recovery).toBeUndefined();
    expect(JSON.stringify(WORKFLOW_GUIDANCE)).not.toMatch(/provider|model|generated example/i);
  });
});
