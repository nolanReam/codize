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
const model = readFileSync(resolve(process.cwd(), "lib/guidedProjectNavigation.ts"), "utf8");
const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

describe("M18B.1 one-home guided shell contract", () => {
  it("removes Phase Workspace from the shared desktop and mobile navigation", () => {
    expect(layout.match(/<GuidedProjectNav\s/g)).toHaveLength(2);
    expect(nav).not.toContain("Phase Workspace");
    expect(nav).not.toContain('href="/app/phase"');
    expect(nav.indexOf("Project Home")).toBeLessThan(nav.indexOf("Continue"));
    expect(nav.indexOf("Continue")).toBeLessThan(nav.indexOf("Journey"));
    expect(nav.indexOf("Journey")).toBeLessThan(nav.indexOf("Project Record"));
  });

  it("redirects the compatibility Phase Workspace route to the current-phase section", () => {
    expect(phase).toContain('import { redirect } from "next/navigation"');
    expect(phase).toContain('redirect("/app#current-phase")');
    expect(phase).not.toContain('"use client"');
    expect(home).toContain('hash !== "#current-phase" && hash !== "#current-work"');
    expect(home).toContain('scrollIntoView({ block: "start" })');
    expect(home).toContain('window.addEventListener("hashchange", restoreHomeAnchor)');
  });

  it("makes Project Home own phase purpose, ordered current work, roadmap, and history access", () => {
    expect(home).toContain('id="current-phase"');
    expect(home).toContain("phaseGuide(phase.phase_title).meaning");
    expect(home).toContain('id="current-work"');
    expect(home).toContain('className="current-work-list"');
    expect(home).toContain('task.owner === "ai" ? "Use AI" : "You decide"');
    expect(home).toContain('className="card project-roadmap"');
    expect(home).toContain('id="project-record-access-title"');
    expect(home).not.toContain("explanation_gate_targets");
    expect(home).not.toContain("unlock_condition");
  });

  it("renders one intended dominant Continue control and no duplicate full Journey on Home", () => {
    expect(home.match(/<GuidedContinueAction className="btn primary" \/>/g)).toHaveLength(1);
    expect(home).toContain("navigation.continueAction.label");
    expect(home).not.toContain("<WorkflowSteps");
    expect(home).not.toContain("<LoopOverview");
    expect(home).not.toContain('aria-label="Project journey"');
  });

  it("hides future lifecycle and record navigation until a roadmap workflow exists", () => {
    expect(nav).toContain('const activeWorkflow = state === "ready" && navigation.workflow !== null');
    expect(nav.match(/\{activeWorkflow && \(/g)).toHaveLength(3);
    expect(nav).toContain('aria-labelledby={`${idPrefix}-help`}');
    expect(nav).toContain("How Codize works");
    expect(nav).toContain("navigation.continueAction.href");
    expect(model).toContain('journey: laterJourney("Finish project setup to open this stage.")');
  });

  it("keeps the canonical Journey compact and Project Record secondary", () => {
    expect(nav).toContain('className="guided-journey-disclosure"');
    expect(nav).toContain('<ol className="guided-journey">');
    expect(nav).toContain("navigation.journey.map");
    expect(nav).toContain('className="project-record"');
    expect(nav).toContain("These records are not independent verification");
    expect(nav).toContain("item.description");
    expect(model).toContain("Needs update");
  });

  it("keeps lifecycle state separate from the open route", () => {
    expect(nav).toContain('aria-current={pathname === "/app" ? "page" : undefined}');
    expect(nav).toContain('!navigation.continueAction.href.includes("#")');
    expect(nav).toContain("routeIsActive(pathname, item.href)");
    expect(nav).toContain("journeyCurrentId === item.id");
    expect(css).toContain(".guided-stage.viewing");
  });

  it("keeps provider loading/error recovery and mutation refresh contracts", () => {
    expect(nav).toContain('role="status" aria-live="polite"');
    expect(nav).toContain('role="alert"');
    expect(provider).toContain('type NavigationLoadState = "loading" | "ready" | "error"');
    expect(provider).toContain("GUIDED_NAVIGATION_REFRESH_EVENT");
    expect(provider).toContain("getEvaluation()");
    expect(provider).toContain("getWorkflow(nextEvaluation.current_phase)");
    expect(provider).toContain("getCurrentGate()");
    expect(provider).not.toMatch(/localStorage|sessionStorage/);
  });

  it("preserves mobile drawer focus behavior and removes the absent closed relationship", () => {
    expect(layout).toContain('aria-controls={mobileOpen ? "mobile-project-navigation" : undefined}');
    expect(layout).toContain('aria-haspopup="dialog"');
    expect(layout).toContain('role="dialog"');
    expect(layout).toContain('aria-modal="true"');
    expect(layout).toContain('event.key === "Escape"');
    expect(layout).toContain('event.key !== "Tab"');
    expect(layout).toContain("last.focus()");
    expect(layout).toContain("trigger?.focus()");
    expect(nav).toContain('name={mobileDisclosureGroup}');
    expect(css).toContain("width: min(360px, calc(100vw - 24px))");
    expect(css).toContain("height: 100dvh");
  });

  it("uses native keyboard controls and visible text-plus-color state", () => {
    expect(nav).toContain("<summary>");
    expect(home).toContain('type="checkbox"');
    expect(home).toContain("aria-describedby={statusId}");
    expect(css).toContain("outline: 2px solid var(--accent)");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    expect(css).toContain(".guided-stage.needs_attention");
    expect(css).toContain(".guided-stage-state");
    expect(css).toMatch(/\.mobile-menu-button \{[\s\S]*?min-height: 44px/);
    expect(css).toMatch(/\.current-work-task \{[\s\S]*?min-height: 52px/);
  });
});
