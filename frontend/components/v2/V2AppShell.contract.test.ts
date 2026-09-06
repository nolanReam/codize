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

  it("keeps destination labels while rendering restrained decorative icons", () => {
    for (const destination of ["project", "build", "learning", "history"]) {
      expect(source).toContain(`icon: "${destination}"`);
    }
    expect(source).toContain('<V2NavIcon name="character" />');
    expect(source).toContain('<V2NavIcon name="settings" />');
    expect(source).toContain('className="v2-nav-icon"');
    expect(source).toContain('aria-hidden="true"');
    expect(source).toContain('focusable="false"');
    expect(source).not.toContain("v2-nav-dot");
  });

  it("keeps the mobile project and account summary touch target at least 44px tall", () => {
    expect(css).toMatch(/\.v2-mobile-menu summary\s*\{[^}]*min-height:\s*44px/);
  });

  it("gives every mobile account-menu action its visible label as an accessible name", () => {
    expect(source).toContain('<Link href="/app/projects" aria-label="Switch project">Switch project</Link>');
    expect(source).toContain('<Link href={characterHref} aria-label="Character"');
    expect(source).toContain('<Link href={settingsHref} aria-label="Settings"');
    expect(source).toContain('<button type="button" aria-label="Sign out" onClick={onSignOut}>Sign out</button>');
  });
});
