import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const source = fs.readFileSync(path.join(process.cwd(), "app/app/page.tsx"), "utf8");

describe("Project Home assignment contract", () => {
  it("distinguishes recommendation, selection, and ownership", () => {
    expect(source).toContain("Recommended assignment");
    expect(source).toContain("Selected assignment");
    expect(source).toContain("Use AI");
    expect(source).toContain("You decide");
  });

  it("keeps switching deliberate and explains preservation", () => {
    expect(source).toContain("Choose another task");
    expect(source).toContain("Switch task");
    expect(source).toContain("Nothing will be merged into the new task");
    expect(source).toContain("Current assignment:");
    expect(source).toContain("Next assignment:");
  });

  it("keeps task completion separate from assignment selection", () => {
    expect(source).toContain("Phase task checklist");
    expect(source).toContain("Saved workflow records do not complete them automatically");
  });
});
