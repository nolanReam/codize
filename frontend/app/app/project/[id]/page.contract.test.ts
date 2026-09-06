import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const home = readFileSync(resolve(process.cwd(), "app/app/project/[id]/page.tsx"), "utf8");
const projects = readFileSync(resolve(process.cwd(), "app/app/projects/page.tsx"), "utf8");
const setup = readFileSync(resolve(process.cwd(), "components/v2/V2ProjectSetupForm.tsx"), "utf8");
const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

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

  it("focuses and describes every incomplete setup field after validation", () => {
    expect(setup).toContain('const validationErrorId = "v2-project-setup-validation-error"');
    expect(setup).toContain("const contextRef = useRef<HTMLTextAreaElement>(null)");
    expect(setup).toContain("const changeRef = useRef<HTMLInputElement>(null)");
    expect(setup).toContain("const doneRef = useRef<HTMLTextAreaElement>(null)");
    expect(setup).toContain("const firstInvalidField = invalid.context");
    expect(setup).toContain("firstInvalidField?.focus()");
    expect(setup).toContain("aria-invalid={invalidFields.context || undefined}");
    expect(setup).toContain("aria-invalid={invalidFields.change || undefined}");
    expect(setup).toContain("aria-invalid={invalidFields.done || undefined}");
    expect(setup).toContain("aria-describedby={invalidFields.context ? validationErrorId : undefined}");
    expect(setup).toContain("aria-describedby={invalidFields.change ? validationErrorId : undefined}");
    expect(setup).toContain("aria-describedby={invalidFields.done ? validationErrorId : undefined}");
    expect(setup).toContain("<div id={validationErrorId}>");
  });

  it("keeps the current change dominant and long user titles readable", () => {
    expect(home).toContain('<V2Character size="small" />');
    expect(home).toContain('<h1 className="v2-user-title">{state.project.display_name}</h1>');
    expect(home).toContain('<h2 className="v2-user-title">{upNext.title}</h2>');
    expect(css).toContain(".v2-up-next-card { width: min(760px, 100%); padding: 32px; border-left-width: 3px;");
    expect(css).toMatch(/\.v2-page-header h1\.v2-user-title,\s*\.v2-build-header h1\.v2-user-title,\s*\.v2-card :is\(h1, h2\)\.v2-user-title\s*\{[^}]*overflow-wrap:\s*anywhere;?[^}]*\}/);
  });
});
