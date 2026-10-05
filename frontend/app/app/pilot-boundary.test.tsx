// @vitest-environment happy-dom
import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AppShell from "./layout";
import ProjectsPage from "./projects/page";
import { acknowledgeReconnection, getReconnection } from "../../lib/api";
import { getProjectRefs } from "../../lib/v2-api";

const navigation = vi.hoisted(() => ({ pathname: "/app/projects", replace: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => navigation.pathname,
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }) }));
vi.mock("next/link", () => ({ default: (props: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a {...props} /> }));
vi.mock("../../lib/supabase", () => ({ getSupabase: () => ({ auth: {
  getSession: async () => ({ data: { session: { user: { id: "user-1", email: "test@example.invalid" } } } }),
  onAuthStateChange: () => ({ data: { sub: undefined, subscription: { unsubscribe: vi.fn() } } }),
} }) }));
vi.mock("../../lib/api", () => ({ getReconnection: vi.fn(), acknowledgeReconnection: vi.fn(), ApiError: class extends Error {} }));
vi.mock("../../lib/v2-api", () => ({ getProjectRefs: vi.fn(), createV2Project: vi.fn(),
  getV2Project: vi.fn().mockResolvedValue({ display_name: "Test project" }) }));
vi.mock("../../components/GuidedProjectNavigationProvider", () => ({
  default: () => { throw new Error("Legacy navigation mounted on V2"); },
  useGuidedProjectNavigation: vi.fn(),
}));

let root: Root;
let container: HTMLDivElement;
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  navigation.pathname = "/app/projects";
  container = document.createElement("div"); document.body.append(container);
  root = createRoot(container);
  sessionStorage.clear();
});
afterEach(() => { act(() => root.unmount()); document.body.replaceChildren(); vi.clearAllMocks(); vi.unstubAllGlobals(); });

describe("V2 frontend legacy isolation", () => {
  it.each(["/app/projects", "/app/project/id", "/app/project/id/plan", "/app/project/id/build",
    "/app/project/id/learning", "/app/project/id/history", "/app/character", "/app/settings"])(
    "renders %s without legacy navigation or reconnection processing", async path => {
      navigation.pathname = path;
      await act(async () => root.render(<AppShell><p>V2 content</p></AppShell>));
      expect(container.textContent).toContain("V2 content");
      expect(getReconnection).not.toHaveBeenCalled();
      expect(acknowledgeReconnection).not.toHaveBeenCalled();
      expect(container.querySelector('a[href="/app"]')).toBeNull();
      expect(container.querySelector('a[href^="/app/phase"]')).toBeNull();
    }
  );
  it.each([false, true])("renders picker entries returned by the backend (pilot=%s)", async pilot => {
    const refs = [{ workflow_version: "v2" as const, project_id: "v2-id", display_name: "V2 project",
      open_mode: "explicit" as const, lifecycle_state: "draft" as const, setup_resume_step: "idea_capture" as const }];
    vi.mocked(getProjectRefs).mockResolvedValue({ projects: pilot ? refs : [
      { workflow_version: "v1", project_id: "v1-id", display_name: "Legacy project",
        open_mode: "legacy_active_only", lifecycle_state: null, setup_resume_step: null }, ...refs] });
    await act(async () => root.render(<AppShell><ProjectsPage /></AppShell>));
    expect(container.querySelector('a[href="/app/project/v2-id"]')).not.toBeNull();
    expect(container.querySelector('a[href="/app"]') === null).toBe(pilot);
    expect(container.textContent?.includes("Legacy project")).toBe(!pilot);
    expect(getReconnection).not.toHaveBeenCalled();
  });
});
