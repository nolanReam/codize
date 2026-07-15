import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "components/AdaptiveEntry.tsx"), "utf8");
const intake = readFileSync(resolve(process.cwd(), "app/app/intake/page.tsx"), "utf8");

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
    expect(source).toContain('href="/app/phase/import"');
    expect(source).not.toMatch(/textarea|input.*latest AI response/i);
  });

  it("announces entry progress, errors, and the recommendation", () => {
    expect(source).toContain('role="status" aria-live="polite"');
    expect(source).toContain('role="alert"');
    expect(source).toContain('type="button"');
  });
});
