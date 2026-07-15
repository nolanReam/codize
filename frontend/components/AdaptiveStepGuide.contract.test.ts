import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "components/AdaptiveStepGuide.tsx"), "utf8");

describe("AdaptiveStepGuide contract", () => {
  it("uses one accessible disclosure for every typed workflow stage", () => {
    expect(source).toContain("WORKFLOW_GUIDANCE[stage]");
    expect(source).toContain("aria-expanded={open}");
    expect(source).toContain("aria-controls={contentId}");
    expect(source).toContain("hidden={!open}");
  });

  it("adapts explanation depth without hiding workflow functionality", () => {
    expect(source).toContain('depth === "more"');
    expect(source).toContain('depth === "standard"');
    expect(source).toContain("compactSummary");
    expect(source).not.toMatch(/router|redirect|disabled=.*depth|fetch\(/);
  });

  it("shows recovery copy only from the saved recovery emphasis", () => {
    expect(source).toContain("entryProfile?.recovery_emphasis && content.recovery");
  });
});
