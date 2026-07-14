import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/phase/verify/page.tsx"), "utf8");

describe("Verification page lifecycle contract", () => {
  it("never initializes on mount and keeps initialization behind explicit actions", () => {
    expect(source.match(/initializeVerificationFromReview\(/g)).toHaveLength(1);
    expect(source).toContain("async function initialize(replaceExisting: boolean)");
    expect(source).toContain("onStart={() => void initialize(false)}");
    expect(source).not.toMatch(/useEffect\([\s\S]{0,180}initializeVerificationFromReview/);
    expect(source).toContain("if (!wf.phase || initializing) return false");
  });

  it("sends replacement only through a deliberate warning flow", () => {
    expect(source).toContain("Rebuilding replaces the current Verification targets, edited checks, results, and notes");
    expect(source).toContain("onReplace={() => initialize(true)}");
    expect(source).toContain("Keep current Verification");
    expect(source).toContain('role="alert"');
    expect(source).toContain("error.status === 409 && !replaceExisting");
    expect(source).toContain(
      "showFullVerificationInitializationState(initializing, Boolean(wf.stored))"
    );
  });

  it("continues to Evidence by navigation only", () => {
    expect(source).toContain('href="/app/phase/evidence"');
    expect(source).toContain("Continue to Evidence");
    expect(source).not.toMatch(/saveWorkflowSection\([^)]*evidence|createEvidence|prefillEvidence/i);
  });

  it("preserves the legacy manual Verification UI and draft surface", () => {
    expect(source).toContain("function LegacyVerificationLab");
    expect(source).toContain("Existing Verification preserved");
    expect(source).toContain("`verification:${phase.phase}`");
    expect(source).toContain("What does this verification prove?");
  });

  it("uses prevention-first copy and never claims Codize performed a check", () => {
    expect(source).toContain("Test implementation choices before continuing.");
    expect(source).toContain("Codize suggested the checks. You perform them");
    expect(source).not.toMatch(/Codize verified|AI approved|implementation is correct|AI tested your project/i);
  });
});
