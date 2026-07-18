import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "components/AdaptiveEntry.tsx"), "utf8");
const intake = readFileSync(resolve(process.cwd(), "app/app/intake/page.tsx"), "utf8");
const home = readFileSync(resolve(process.cwd(), "app/app/page.tsx"), "utf8");
const provider = readFileSync(
  resolve(process.cwd(), "components/GuidedProjectNavigationProvider.tsx"),
  "utf8"
);

describe("M17 adaptive entry UI contract", () => {
  it("uses native one-question fieldsets and no default student answer", () => {
    expect(source.match(/<fieldset/g)).toHaveLength(3);
    expect(source).toContain("<legend");
    expect(source).toContain('type="radio"');
    expect(source).toContain("useState<EntrySituation | null>");
    expect(source).toContain("useState<CodingConfidence | null>");
  });

  it("hides the AI-change decision outside the already-building path", () => {
    expect(source).toContain('situation === "already_building"');
    expect(source).toContain('setAiChanged(null)');
    expect(source).toContain('void save({ ai_changed_files: aiChanged }, "recommendation")');
  });

  it("submits only student-owned entry choices", () => {
    expect(source).toContain("{ current_situation: situation }");
    expect(source).toContain("{ coding_confidence: confidence }");
    expect(source).not.toMatch(/onSave\([^)]*(recommended_start|guidance_depth|stale|defense)/);
    expect(intake).toContain("updateEntryProfile(updates)");
  });

  it("uses one recommendation action and the existing Import destination", () => {
    expect(source).toContain("Continue project details");
    expect(source).toContain("Review choices");
    expect(source).toContain('href="/app/phase/import"');
    expect(source).not.toMatch(/textarea|input.*latest AI response/i);
  });

  it("reacts when same-route navigation opens the Quick Start query", () => {
    expect(home).toContain("useSearchParams");
    expect(home).toContain('searchParams.get("quick-start") === "1"');
    expect(home).not.toContain("new URLSearchParams(window.location.search)");
  });

  it("keeps setup status honest and makes pre-workflow profile errors retryable", () => {
    expect(home).toContain("{evaluation && workflow && (");
    expect(home).toContain('error={state === "error"');
    expect(home).not.toContain("DEFENSE READY");
    expect(provider).toContain("getEntryProfile(),");
    expect(
      provider.match(/getEntryProfile\(\)\.catch\(\(\) => \(\{ profile: null \}\)\)/g)
    ).toHaveLength(1);
  });

  it("announces entry progress, errors, and the recommendation", () => {
    expect(source).toContain('role="status" aria-live="polite"');
    expect(source).toContain('role="alert"');
    expect(source).toContain('type="button"');
  });
});
