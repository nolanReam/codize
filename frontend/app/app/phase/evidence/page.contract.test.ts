import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/phase/evidence/page.tsx"), "utf8");

describe("Evidence page lifecycle contract", () => {
  it("loads a read-only preview but never initializes Evidence on mount", () => {
    expect(source).toContain("getEvidenceHandoffPreview");
    expect(source.match(/initializeEvidenceFromVerification\(/g)).toHaveLength(1);
    expect(source).toContain("async function initialize(selectedIds: string[], replaceExisting: boolean)");
    expect(source).not.toMatch(/useEffect\([\s\S]{0,240}initializeEvidenceFromVerification/);
    expect(source).toContain("Create Evidence workspace");
  });

  it("keeps server eligibility authoritative and starts with no selected targets", () => {
    expect(source).toContain("eligibleEvidenceTargets(preview)");
    expect(source).toContain("normalizeEvidenceSelection(preview, selected)");
    expect(source).toContain("useState<string[]>([])");
    expect(source).toContain('type="checkbox"');
    expect(source).not.toMatch(/result\s*===\s*["']pass["'][\s\S]{0,80}selectable/i);
  });

  it("shows every prerequisite and ineligible outcome honestly", () => {
    for (const copy of [
      "Complete Verification first",
      "Finish recording your Verification results",
      "Update Verification first",
      "No performed checks are available for Evidence",
      "Not available for Evidence handoff",
    ]) expect(source).toContain(copy);
    expect(source).toContain("evidenceResultLabel(target.result)");
    expect(source).toContain("evidenceResultDescription(target.result)");
  });

  it("keeps linked source context read-only and student fields semantic", () => {
    expect(source).toContain("From your Verification");
    expect(source).toContain("Check performed");
    expect(source).toContain("Recorded result");
    expect(source).toContain("What you recorded");
    expect(source).toContain("<fieldset className=\"evidence-status-picker\"");
    expect(source).toContain("Your Evidence decision");
    expect(source).not.toMatch(/value=\{target\.check_snapshot\}|onChange[\s\S]{0,100}check_snapshot/);
  });

  it("preserves manual mode and keeps replacement deliberate", () => {
    expect(source).toContain("function LegacyEvidencePanel");
    expect(source).toContain("Existing Evidence preserved");
    expect(source).toContain("`evidence:${phase.phase}`");
    expect(source).toContain("Starting from Verification replaces the current Evidence work");
    expect(source).toContain("onCreate={(ids) => initialize(ids, true)}");
  });

  it("keeps stale Evidence mounted and requires explicit replacement confirmation", () => {
    expect(source).toContain("Verification changed after this Evidence workspace was created.");
    expect(source).toContain("Rebuilding replaces the current Evidence targets, Evidence entries, explanations, and");
    expect(source).toContain("Keep current Evidence");
    expect(source).toContain("onCreate={(ids) => initialize(ids, true)}");
  });

  it("uses server completion and contains no M16C Defense or Report integration", () => {
    expect(source).toContain("evidence.evidence_record_complete");
    expect(source).toContain("Evidence record complete");
    expect(source).not.toContain('href="/app/gate"');
    expect(source).not.toContain('href="/app/report"');
    expect(source).not.toMatch(/Defense context|Defense Report|Project Defense uses/i);
  });

  it("renders plain React text without Markdown, embeds, or unsafe HTML", () => {
    expect(source).not.toContain("dangerouslySetInnerHTML");
    expect(source).not.toMatch(/ReactMarkdown|<iframe|<embed|fetch\(target\.|fetch\(entry\./);
    expect(source).toContain("target.check_snapshot");
    expect(source).toContain("entry.content");
  });
});
