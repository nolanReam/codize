import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const home = readFileSync(resolve(process.cwd(), "app/app/project/[id]/page.tsx"), "utf8");
const projects = readFileSync(resolve(process.cwd(), "app/app/projects/page.tsx"), "utf8");
const setup = readFileSync(resolve(process.cwd(), "components/v2/V2ProjectSetupForm.tsx"), "utf8");

describe("V2 draft setup resumability contract", () => {
  it("makes persisted drafts discoverable and routes creation before setup", () => {
    expect(projects).toContain('project.lifecycle_state === "draft" ? "Continue setup"');
    expect(projects).toContain("router.push(`/app/project/${created.project.project_id}`)");
    expect(projects).not.toContain("establishManualProject(created.project.project_id");
  });

  it("renders both accepted draft resume steps on explicit Project Home", () => {
    expect(home).toContain('state.project.setup_resume_step === "idea_capture"');
    expect(home).toContain('state.project.setup_resume_step === "existing_project_context"');
    expect(home).toContain("<V2ProjectSetupForm project={state.project} onComplete={load} />");
    expect(setup).toContain("Project ID:");
    expect(setup).toContain("project.version");
    expect(setup).toContain("project.setup_draft?.project_context");
    expect(setup).toContain("project.setup_draft?.initial_change_label");
    expect(setup).toContain("project.setup_draft?.done_condition");
    expect(setup).toContain("saveSetupDraft(");
    expect(setup).toContain("Save progress");
    expect(setup).toContain("draftCommand.current?.signature");
    expect(setup).toContain("reason.status === 409");
    expect(setup).toContain("await onComplete()");
    expect(setup).not.toContain("localStorage");
  });
});
