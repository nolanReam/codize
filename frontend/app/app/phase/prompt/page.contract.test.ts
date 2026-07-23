import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const source = fs.readFileSync(path.join(process.cwd(), "app/app/phase/prompt/page.tsx"), "utf8");

describe("Prompt Builder assignment contract", () => {
  it("keeps assignment, learning focus, scope, fields, and preview in order", () => {
    expect(source.indexOf("Current prompt assignment")).toBeLessThan(source.indexOf("Generic starters"));
    expect(source.indexOf("Current prompt assignment")).toBeLessThan(source.indexOf("Learning focus"));
    expect(source.indexOf("Learning focus")).toBeLessThan(
      source.indexOf("What will exist when this task is done?")
    );
    expect(source.indexOf("Scope checklist")).toBeLessThan(
      source.indexOf("Step 1 — Task (editable)")
    );
    expect(source.indexOf("Step 1 — Task (editable)")).toBeLessThan(
      source.indexOf("Your prompt — paste into your AI tool")
    );
    expect(source.indexOf("Your prompt — paste into your AI tool")).toBeLessThan(
      source.indexOf("Broad versus bounded example")
    );
    expect(source).toContain("Work on one focused task in this prompt");
    expect(source).toContain("Use this assignment");
  });

  it("renders the three decisions and transparent deterministic boundary", () => {
    expect(source).toContain("What will exist when this task is done?");
    expect(source).toContain("What related work are you leaving out of this request?");
    expect(source).toContain(
      "What observable result will tell you the response is ready to inspect?"
    );
    expect(source).toContain("Scope checklist complete");
    expect(source).toContain("does not score correctness");
    expect(source).not.toMatch(/Excellent Prompt|Correct scope|Mastered|Passed/);
  });

  it("applies student scope explicitly without touching Context or saving", () => {
    expect(source).toContain("Apply this scope to my Prompt");
    expect(source).toContain("Context stays exactly as written");
    expect(source).toContain("Nothing is saved automatically");
    expect(source).toContain("Replace existing Prompt text?");
    expect(source).toContain("scopeApplicationConflicts");
    expect(source).not.toContain("setTaskCompletion");
  });

  it("uses guidance depth only for presentation and keeps the example optional", () => {
    expect(source).toContain('guidanceDepth === "minimal"');
    expect(source).toContain('defaultOpen={guidanceDepth === "more"}');
    expect(source).toContain("Another project: a habit tracker");
    expect(source).toContain("Create the basic habit-entry form");
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
    expect(source).toContain("This saved Prompt predates scope practice");
    expect(source).toContain("without retroactive blocking");
  });

  it("keeps assignment failure recoverable and refreshes stale bindings on focus", () => {
    expect(source).toContain("Retry assignment");
    expect(source).toContain('window.addEventListener("focus", refreshOnFocus)');
    expect(source).toContain('<h2 id="prompt-assignment-title" className="entry-kicker">');
  });
});
