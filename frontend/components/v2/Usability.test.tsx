// @vitest-environment happy-dom

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LearningPage from "../../app/app/project/[id]/learning/page";
import V2ProjectSetupForm from "./V2ProjectSetupForm";
import { establishManualProject, getLearning } from "../../lib/v2-api";
import type { LearningResponse, V2ProjectView } from "../../lib/v2-types";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "project-1" }) }));
vi.mock("next/link", () => ({ default: (props: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a {...props} /> }));
vi.mock("../../lib/v2-api", () => ({ getLearning: vi.fn(), establishManualProject: vi.fn(), saveSetupDraft: vi.fn() }));

const project: V2ProjectView = {
  workflow_version: "v2", project_id: "project-1", display_name: "Team tracker",
  lifecycle_state: "draft", setup_resume_step: "idea_capture", setup_draft: null,
  coding_agent_key: null, plan_version: 1, version: 1, first_version_completed_at: null,
  created_at: "2026-09-01T00:00:00Z", updated_at: "2026-09-01T00:00:00Z",
};
const learning: LearningResponse = {
  workflow_version: "v2", project_id: "project-1", recent_evidence_limit: 3,
  competencies: [{ key: "done", name: "Define done", description: "Give your AI a result you can check.",
    status: "guided", status_explanation: "You named a clear result with help.", support_direction: "more",
    recent_evidence: [{ observed_behavior: "Named the expected player form result.",
      support_explanation: "Used a clue to make the result specific.", project_name: "Team tracker",
      current_change_goal: "Add a player", observed_at: "2026-09-01T00:00:00Z" }] }],
};
let root: Root;
let container: HTMLDivElement;
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  container = document.createElement("div"); document.body.append(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); document.body.replaceChildren(); vi.clearAllMocks(); vi.unstubAllGlobals(); });

describe("beginner project setup wording", () => {
  it.each(["idea_capture", "existing_project_context"])("asks what to build or improve for %s", async step => {
    await act(async () => root.render(<V2ProjectSetupForm project={{ ...project, setup_resume_step: step }} onComplete={vi.fn()} />));
    const input = container.querySelector<HTMLInputElement>('input[name="change"]')!;
    expect(input.closest("label")?.textContent?.trim()).toBe("What do you want to build or improve first?");
    expect(input.placeholder).toBe("For example, add a form for entering players");
    expect(container.textContent).not.toContain("first change");
    await act(async () => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("what you want to build or improve");
    expect(document.activeElement).toBe(container.querySelector('[name="context"]'));
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(document.getElementById(input.getAttribute("aria-describedby")!)?.textContent).toContain("how you’ll check it");
    expect(establishManualProject).not.toHaveBeenCalled();
  });

  it("keeps existing saved domain values and setup submission unchanged", async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    const draft = { project_context: "A team tracker", initial_change_label: "Add a player form", done_condition: "Add Alex and see Alex in the list" };
    await act(async () => root.render(<V2ProjectSetupForm project={{ ...project, setup_draft: draft }} onComplete={onComplete} />));
    await act(async () => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(establishManualProject).toHaveBeenCalledWith("project-1", 1, expect.any(String), draft.project_context, expect.any(String), draft.initial_change_label, draft.done_condition);
    expect(onComplete).toHaveBeenCalledOnce();
  });
});

describe("Learning information hierarchy", () => {
  it("keeps the scan summary outside a closed native disclosure and all deeper explanation inside", async () => {
    vi.mocked(getLearning).mockResolvedValue(learning);
    await act(async () => root.render(<LearningPage />));
    const card = container.querySelector("article")!;
    const details = card.querySelector("details")!;
    expect(details.open).toBe(false);
    expect(details.querySelector("summary")?.textContent).toBe("Why this status");
    expect(card.querySelector("h2")?.textContent).toBe("Define done");
    expect(card.querySelector(":scope > p")?.textContent).toBe(learning.competencies[0].description);
    expect(card.querySelector(".v2-status")?.textContent).toBe("Guided");
    expect(card.querySelectorAll(":scope > p")).toHaveLength(1);
    expect(details.textContent).toContain(learning.competencies[0].status_explanation);
    expect(details.textContent).toContain("Codize is currently giving more help here.");
    expect(details.textContent).toContain(learning.competencies[0].recent_evidence[0].support_explanation);
    details.open = true;
    expect(details.querySelector("li strong")?.textContent).toBe("Named the expected player form result.");
    expect(details.querySelector("small")?.textContent).toContain("Team tracker · Add a player");
    details.open = false;
    expect(details.querySelectorAll("li")).toHaveLength(1);
    expect(container.querySelector('a[href="/app/project/project-1/build"]')).not.toBeNull();
  });
});
