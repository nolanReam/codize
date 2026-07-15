import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/phase/review/page.tsx"), "utf8");

describe("Review page lifecycle contract", () => {
  it("never initializes on mount and keeps initialization behind explicit actions", () => {
    expect(source.match(/initializeReviewFromChangeMap\(/g)).toHaveLength(1);
    expect(source).toContain("async function initialize(replaceExisting: boolean)");
    expect(source).toContain("onStart={() => void initialize(false)}");
    expect(source).not.toMatch(/useEffect\([\s\S]{0,160}initializeReviewFromChangeMap/);
    expect(source).toContain("if (!wf.phase || initializing) return false");
  });

  it("sends replacement only through a deliberate warning flow", () => {
    expect(source).toContain("Rebuilding replaces the current Review targets and decisions");
    expect(source).toContain("onReplace={() => initialize(true)}");
    expect(source).toContain("Keep current Review");
    expect(source).toContain('role="alert">{error}');
    expect(source).toContain("error.status === 409 && !replaceExisting");
    expect(source).toContain("showFullReviewInitializationState(initializing, Boolean(wf.stored))");
  });

  it("navigates to Verification without prefilling or creating downstream records", () => {
    expect(source).toContain('href="/app/phase/verify"');
    expect(source).toContain("Continue Verification");
    expect(source).not.toMatch(/saveWorkflowSection\([^)]*verification|createEvidence|verification suggestion/i);
  });

  it("keeps the legacy Review form and prevention-first copy", () => {
    expect(source).toContain("function LegacyReviewBoard");
    expect(source).toContain("Existing Review preserved");
    expect(source).toContain("Review implementation choices before continuing.");
    expect(source).not.toMatch(/AI approved|implementation approved|AI recommends keeping/i);
  });
});
