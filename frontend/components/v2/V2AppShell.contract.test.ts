import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "components/v2/V2AppShell.tsx"), "utf8");
const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

describe("V2 app shell navigation contract", () => {
  it("carries explicit project context through Character and Settings", () => {
    expect(source).toContain('new URLSearchParams(window.location.search).get("project")');
    expect(source).toContain("const projectContext = projectId ? `?project=${encodeURIComponent(projectId)}` : \"\";");
    expect(source).toContain("const characterHref = `/app/character${projectContext}`;");
    expect(source).toContain("const settingsHref = `/app/settings${projectContext}`;");
  });

  it("exposes active state to assistive technology on primary and account navigation", () => {
    expect(source.match(/aria-current=/g)?.length).toBeGreaterThanOrEqual(4);
    expect(source).toContain('characterActive ? "v2-nav-link is-active" : "v2-nav-link"');
    expect(source).toContain('settingsActive ? "v2-nav-link is-active" : "v2-nav-link"');
  });

  it("keeps the mobile project and account summary touch target at least 44px tall", () => {
    expect(css).toMatch(/\.v2-mobile-menu summary\s*\{[^}]*min-height:\s*44px/);
  });
});
