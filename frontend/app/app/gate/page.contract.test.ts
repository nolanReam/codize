import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/gate/page.tsx"), "utf8");

describe("Project Defense M16C.2 contract", () => {
  it("does not expose a formal start action when server readiness is false", () => {
    expect(source).toContain("gate.readiness?.formal_ready === false");
    expect(source).toContain("Not ready for formal Project Defense yet");
    expect(source).toContain("defense-prerequisites");
    expect(source).toContain("continueAction={guided.navigation.continueAction}");
    expect(source).not.toContain('not_started: { label: "READY TO DEFEND"');
  });
  it("keeps the existing gate lifecycle and answer limits", () => {
    for (const call of ["startGate", "submitGateAnchor", "submitGateAnswer", "evaluateGate"]) {
      expect(source).toContain(call);
    }
    expect(source).toContain("isAnchor ? 2000 : 8000");
    expect(source).toContain("useDraft");
    expect(source).toContain("Nothing is graded until the final answer.");
  });

  it("never submits context, provenance, source state, snapshots, or generated answers", () => {
    expect(source).not.toMatch(/body:\s*\{[\s\S]*?workflow_context/);
    expect(source).not.toMatch(/body:\s*\{[\s\S]*?snapshot/);
    expect(source).not.toMatch(/body:\s*\{[\s\S]*?provenance/);
    expect(source).not.toMatch(/setInput\([^)]*(evidence|verification|expected)/i);
    expect(source).not.toMatch(/suggested answer|answer with evidence|expected concepts/i);
  });

  it("shows stable-attempt truth only before a new attempt and uses phase-scoped Report links", () => {
    expect(source).toContain("A stable record for this attempt");
    expect(source).toContain("Later workflow edits do not rewrite this active Defense attempt.");
    expect(source).toContain("/app/report?phase=");
    expect(source).not.toContain("This Defense uses the project record captured when the attempt began.");
  });
});
