import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/project/[id]/build/page.tsx"), "utf8");
const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

describe("V2 Build foundation contract", () => {
  it("renders every backend-owned Phase 3A stage without inventing return or completion", () => {
    for (const stage of [
      "choose_agent",
      "edit_prompt",
      "choose_effort",
      "review_prompt",
      "ready_to_handoff",
      "waiting_for_return",
    ]) {
      expect(source).toContain(`build_stage === "${stage}"`);
    }
    expect(source).not.toContain("It worked");
    expect(source).not.toContain("Complete change");
  });

  it("reloads authoritative state after version conflicts", () => {
    expect(source).toContain("reason.status === 409");
    expect(source).toContain("await load()");
  });

  it("keeps effort selection semantic and unselected by default", () => {
    expect(source).toContain('type="radio"');
    expect(source).toContain('useState<EffortCategory | "">("")');
  });

  it("keeps the approved companion, message, and single-column stage composition", () => {
    expect(source).toContain('<div className="v2-build-character">');
    expect(source).toContain('<V2Character size="mini" />');
    expect(source).toContain('<section className="v2-agent-stage"');
    expect(css).toContain(".v2-build-page { width: min(1124px, 100%); margin: 0; }");
    expect(css).toContain(".v2-conversation { display: flex; width: min(820px, 100%);");
    expect(css).toContain(".v2-character-message { display: grid; grid-template-columns: 36px minmax(0, 560px); width: min(720px, 100%);");
    expect(css).toContain(".v2-agent-stage { width: min(760px, 100%); margin: 0; }");
    expect(css).toContain(".v2-agent-grid { display: grid; grid-template-columns: 1fr;");
    expect(css).not.toMatch(/\.v2-agent-grid\s*\{[^}]*repeat\(2/);
  });
});
