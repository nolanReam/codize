import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const learning = readFileSync(resolve(process.cwd(), "app/app/project/[id]/learning/page.tsx"), "utf8");
const history = readFileSync(resolve(process.cwd(), "app/app/project/[id]/history/page.tsx"), "utf8");
const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

describe("V2 Learning and History UI contract", () => {
  it("renders backend-owned learner descriptors and transparent recent evidence", () => {
    expect(learning).toContain("getLearning(id)");
    expect(learning).toContain("Why this status");
    expect(learning).toContain("support_explanation");
    expect(learning).not.toContain("evidence.id");
    expect(learning).not.toContain("evidence.project_id");
    expect(learning).not.toContain("evidence.current_change_id");
    expect(learning).toContain("not permanent badges");
    expect(learning).not.toMatch(/\bXP\b|\bstreaks?\b|\bmastery\b|\bpercentages?\b/i);
  });

  it("keeps all Check results and Recovery provenance inside each change", () => {
    expect(history).toContain("change.checks.map");
    expect(history).toContain("check.sequence");
    expect(history).toContain("key={check.sequence}");
    expect(history).not.toContain("check.id");
    expect(history).toContain("check.not_run_at");
    expect(history).toContain("relationshipLabels[check.relationship]");
    expect(history).toContain('did_not_work: "FAIL"');
    expect(history).toContain('unsure: "UNSURE"');
    expect(history).toContain("Coding agent suggested:");
    expect(history).toContain("change.recoveries.map");
    expect(history).toContain("recovery.recheck_state &&");
    expect(history).toContain("Accepted prompts");
    expect(history).not.toContain("Root cause:");
  });

  it("provides bounded pagination, honest empty states, and a non-persistent transfer seam", () => {
    expect(history).toContain("Load older changes");
    expect(history).toContain("will not invent what code changed");
    expect(history).toContain("Your answer is not saved yet");
    expect(learning).toContain("Nothing appears here just because you opened the page");
  });

  it("stacks cards and timeline content for narrow mobile screens", () => {
    expect(css).toContain(".v2-learning-grid { grid-template-columns: 1fr; }");
    expect(css).toContain(".v2-check-history li { grid-template-columns: 1fr; }");
    expect(css).toContain(".v2-history-recovery ol { grid-template-columns: 1fr; }");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
  });
});
