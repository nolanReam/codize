import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const source = fs.readFileSync(path.join(process.cwd(), "app/app/phase/prompt/page.tsx"), "utf8");

describe("Prompt Builder assignment contract", () => {
  it("keeps the real assignment and one-task rule above generic starters", () => {
    expect(source.indexOf("Current prompt assignment")).toBeLessThan(source.indexOf("Generic starters"));
    expect(source).toContain("Work on one focused task in this prompt");
    expect(source).toContain("Use this assignment");
  });

  it("does not send student-owned decisions to Prompt Builder", () => {
    expect(source).toContain("You decide this task");
    expect(source).toContain("will not turn it into an AI prompt");
  });

  it("preserves legacy, prior, and differently bound saved Prompts", () => {
    expect(source).toContain("Legacy saved Prompt");
    expect(source).toContain("Saved Prompt for another assignment");
    expect(source).toContain("Prior saved Prompts");
    expect(source).toContain("does not fabricate a task association");
  });

  it("keeps assignment failure recoverable and refreshes stale bindings on focus", () => {
    expect(source).toContain("Retry assignment");
    expect(source).toContain('window.addEventListener("focus", refreshOnFocus)');
    expect(source).toContain('<h2 id="prompt-assignment-title" className="entry-kicker">');
  });
});
