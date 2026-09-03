import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/project/[id]/build/page.tsx"), "utf8");
const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

describe("V2 Build foundation contract", () => {
  it("resolves completed refresh, active work, empty projects, and request errors explicitly", () => {
    expect(source).toContain("resolveLoadedBuildStatus(false, Boolean(latest))");
    expect(source).toContain("resolveLoadedBuildStatus(true, false)");
    expect(source).toContain('setLoadStatus("error")');
    expect(source).toContain('loadStatus === "error"');
    expect(source).toContain("Build couldn’t load");
    expect(source).not.toContain("!data && !empty && !error");
  });
  it("renders the backend-owned manual loop from confirmation through completion", () => {
    for (const stage of [
      "choose_agent",
      "edit_prompt",
      "choose_effort",
      "review_prompt",
      "ready_to_handoff",
      "waiting_for_return",
      "confirm_change",
      "intervention",
      "perform_check",
      "propose_check",
      "check_unsure",
      "check_failed",
      "understand",
      "ready_to_complete",
    ]) {
      expect(source).toContain(`build_stage === "${stage}"`);
    }
    expect(source).toContain("It worked");
    expect(source).toContain("Complete change");
    expect(source).toContain("recordCheck(");
  });

  it("reloads authoritative state after version conflicts", () => {
    expect(source).toContain("reason.status === 409");
    expect(source).toContain("await load()");
  });

  it("keeps effort selection semantic and unselected by default", () => {
    expect(source).toContain('type="radio"');
    expect(source).toContain('useState<EffortCategory | "">("")');
  });

  it("announces effort feedback exactly once through its visible status notice", () => {
    expect(source).toContain("setEffortMessage(result.feedback.message)");
    expect(source).not.toContain("setAnnouncement(result.feedback.message)");
    expect(source).toContain('effortMessage && data.build.build_stage !== "choose_effort"');
    expect(source).toContain("data.build.effort_feedback?.message ?? effortMessage");
  });

  it("renders one durable adaptive teaching task with progressive help", () => {
    expect(source).toContain("data.build.teaching.mode");
    expect(source).toContain('data.build.teaching.risk === "slowdown"');
    expect(source).toContain('data.build.teaching.hint_level === "none" ? "Need help?" : "Show me more"');
    expect(source).toContain("requestTeachingHelp(");
    expect(source).toContain("respondToTeaching(");
    expect(source).toContain("createStudentCheckPlan(");
    expect(source).toContain("data.build.teaching.can_request_help &&");
    expect(source).toContain('data.build.verification_plan_source === "codize"');
    expect(source).not.toContain('data.build.learner_statuses.testing === "recently_independent"');
    expect(source).not.toContain("mastery");
  });

  it("owns retry-stable teaching command identities at the interaction level", () => {
    expect(source).toContain("const teachingCommands = useRef(new Map");
    for (const operation of ["confirm-change", "effort", "teaching-help", "teaching-response", "check-plan"]) {
      expect(source).toContain(`"${operation}",`);
    }
  });

  it("keeps contextual Recovery in Build as Observe, Investigate, Correct, Recheck", () => {
    for (const stage of [
      "recovery_symptom",
      "recovery_investigate",
      "recovery_investigation_handoff",
      "recovery_investigation_return",
      "recovery_correct",
      "recovery_correction_handoff",
      "recovery_correction_return",
      "recovery_recheck",
    ]) {
      expect(source).toContain(`build_stage === "${stage}"`);
    }
    for (const label of ["Observe", "Investigate", "Correct", "Recheck"]) {
      expect(source).toContain(label);
    }
    expect(source).toContain("Student observed:");
    expect(source).toContain("Coding AI suggested:");
    expect(source).toContain("not a verified root cause");
    expect(source).toContain("personally observe");
    expect(source).toContain('submitRecoveryRecheck("unsure")');
    expect(css).toContain(".v2-recovery-progress");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
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
