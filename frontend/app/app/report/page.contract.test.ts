import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/report/page.tsx"), "utf8");

describe("Defense Report M16C.2 route contract", () => {
  it("fetches the authoritative Report and does not rebuild it from workflow page state", () => {
    expect(source).toContain("getDefenseReport");
    expect(source).toContain("buildReportMarkdown(report)");
    for (const forbidden of ["getWorkflow", "getCurrentGate", "getCurrentPhase", "getIntakeStatus"]) {
      expect(source).not.toContain(forbidden);
    }
  });

  it("announces loading, supports retry, and protects the lifecycle", () => {
    expect(source).toContain("Preparing your Defense Report…");
    expect(source).toContain('role="status"');
    expect(source).toContain('role="alert"');
    expect(source).toContain("Retry Report");
    expect(source).toContain("reportIsReady");
    expect(source).toContain("Continue Project Defense");
    expect(source).toContain("Start Project Defense");
  });

  it("does not submit or generate Report context", () => {
    expect(source).not.toMatch(/method:\s*["']POST["']/);
    expect(source).not.toMatch(/workflow_context\s*:/);
    expect(source).not.toMatch(/truth_notice\s*:/);
    expect(source).not.toMatch(/provider|model|prompt|score|threshold|expected concept/i);
  });
});
