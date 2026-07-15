import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const nav = readFileSync(resolve(process.cwd(), "components/GuidedProjectNav.tsx"), "utf8");
const provider = readFileSync(
  resolve(process.cwd(), "components/GuidedProjectNavigationProvider.tsx"),
  "utf8"
);
const layout = readFileSync(resolve(process.cwd(), "app/app/layout.tsx"), "utf8");
const home = readFileSync(resolve(process.cwd(), "app/app/page.tsx"), "utf8");
const phase = readFileSync(resolve(process.cwd(), "app/app/phase/page.tsx"), "utf8");
const workflowSteps = readFileSync(resolve(process.cwd(), "components/WorkflowSteps.tsx"), "utf8");
const model = readFileSync(resolve(process.cwd(), "lib/guidedProjectNavigation.ts"), "utf8");
const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

describe("guided project shell contract", () => {
  it("presents Project Home first, one Continue action, Journey, and Project Record", () => {
    expect(nav.indexOf("Project Home")).toBeLessThan(nav.indexOf("Continue"));
    expect(nav.indexOf("Continue")).toBeLessThan(nav.indexOf("Journey"));
    expect(nav.indexOf("Journey")).toBeLessThan(nav.indexOf("Project Record"));
    expect(nav).toContain('aria-label="Project navigation"');
    expect(nav).toContain("guided-continue-link");
    expect(nav).toContain("navigation.continueAction.href");
  });

  it("keeps lifecycle status separate from the currently open route", () => {
    expect(nav).toContain('aria-current={pathname === "/app" ? "page" : undefined}');
    expect(nav).toContain('aria-current={continueIsCurrent ? "page" : undefined}');
    expect(nav).toContain('aria-current={current ? "page" : undefined}');
    expect(nav).toContain("routeIsActive(pathname, item.href)");
    expect(nav).toContain("item.stateLabel");
    expect(nav).toContain('pathname === "/app/phase" && !continueIsCurrent');
    expect(nav).toContain("journeyCurrentId === item.id");
    expect(nav).toContain('aria-current={journeyCurrentId === item.id ? "page" : undefined}');
    expect(css).toContain(".guided-stage.viewing");
  });

  it("renders future Journey stages as semantic non-links with text state", () => {
    expect(nav).toContain('<ol className="guided-journey"');
    expect(nav).toContain('className={`guided-stage ${item.state}${journeyCurrentId === item.id ? " viewing" : ""}`}');
    expect(nav).toContain("{item.stateLabel}");
    expect(nav).not.toContain("<Link href={item.href}");
    expect(css).toContain(".guided-stage.later");
    expect(css).toContain("color: var(--ink-2)");
  });

  it("keeps saved and stale work in an accessible secondary disclosure", () => {
    expect(nav).toContain('<details className="project-record"');
    expect(nav).toContain("<summary>");
    expect(nav).toContain("These records are not independent verification");
    expect(nav).toContain("item.description");
    expect(model).toContain("Needs update");
  });

  it("announces loading and errors without replacing Project Home", () => {
    expect(nav).toContain('role="status" aria-live="polite"');
    expect(nav).toContain('role="alert"');
    expect(nav).toContain("Project progress is temporarily unavailable.");
    expect(provider).toContain('type NavigationLoadState = "loading" | "ready" | "error"');
    expect(provider).toContain("setWorkflow(null)");
    expect(phase).toContain('guided.state === "loading"');
    expect(phase).toContain('guided.state === "error"');
  });

  it("uses the shared provider and saved-state refresh for both desktop and mobile", () => {
    expect(layout).toContain("<GuidedProjectNavigationProvider>");
    expect(layout.match(/<GuidedProjectNav\s/g)).toHaveLength(2);
    expect(provider).toContain("GUIDED_NAVIGATION_REFRESH_EVENT");
    expect(provider).toContain("getEvaluation()");
    expect(provider).toContain("getWorkflow(nextEvaluation.current_phase)");
    expect(provider).toContain("getCurrentGate()");
    expect(provider).not.toMatch(/localStorage|sessionStorage/);
  });

  it("focus-manages the mobile modal drawer", () => {
    expect(layout).toContain('aria-controls="mobile-project-navigation"');
    expect(layout).toContain('role="dialog"');
    expect(layout).toContain('aria-modal="true"');
    expect(layout).toContain('event.key === "Escape"');
    expect(layout).toContain('event.key !== "Tab"');
    expect(layout).toContain("last.focus()");
    expect(layout).toContain("trigger?.focus()");
    expect(css).toContain("width: min(360px, calc(100vw - 24px))");
    expect(css).toContain("height: 100dvh");
  });

  it("aligns Project Home, Phase Workspace, and page Journey to the shared model", () => {
    expect(home).toContain("useGuidedProjectNavigation()");
    expect(home).toContain("navigation.continueAction.label");
    expect(home).toContain('<GuidedContinueAction className="btn primary" />');
    expect(phase).toContain("guided.navigation.continueAction");
    expect(phase).not.toContain("derivePhaseNextStep");
    expect(workflowSteps).toContain("useGuidedProjectNavigation()");
    expect(workflowSteps).not.toContain("sections:");
    expect(home).not.toContain("router.replace");
    expect(home).toContain("evaluation && !workflow");
  });

  it("uses the shared Continue action on completed Review and Verification pages", () => {
    const reviewPage = readFileSync(
      resolve(process.cwd(), "app/app/phase/review/page.tsx"),
      "utf8"
    );
    const verificationPage = readFileSync(
      resolve(process.cwd(), "app/app/phase/verify/page.tsx"),
      "utf8"
    );
    expect(reviewPage).toContain('<GuidedContinueAction className="btn primary" />');
    expect(verificationPage.match(/<GuidedContinueAction className="btn primary" \/>/g)).toHaveLength(2);
  });

  it("preserves visible focus, reduced motion, and text-plus-color states", () => {
    expect(css).toContain("outline: 2px solid var(--accent)");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    expect(css).toContain(".guided-stage.needs_attention");
    expect(css).toContain(".guided-stage-state");
    expect(css).toContain(".project-record li.needs_attention");
    expect(css).toMatch(/\.project-identity-label,[\s\S]*?color: var\(--ink-2\)/);
    expect(css).toMatch(/\.guided-stage-index \{[\s\S]*?color: var\(--ink-2\)/);
    expect(css).toMatch(/\.guided-stage-state \{[\s\S]*?color: var\(--ink-2\)/);
  });
});
