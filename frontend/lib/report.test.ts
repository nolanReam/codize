import { describe, expect, it } from "vitest";

import {
  buildReportMarkdown,
  defenseStatus,
  deriveInterviewQuestions,
  deriveSkills,
  deriveWeakSpots,
  type ReportInput,
} from "./report";
import type { Evaluation, GateCurrent, PhaseView, WorkflowSections } from "./types";

const evaluation: Evaluation = {
  state: "in_progress",
  project_status: "active",
  next_action: "Build phase 2, then defend it.",
  current_phase: 2,
  phase_title: "Data Model",
  total_phases: 7,
  completed_phases: 0,
  completed_task_count: 3,
  total_task_count: 6,
  recent_gate: { outcome: "in_progress", summary: null },
};

const phase: PhaseView = {
  phase: 2,
  phase_title: "Data Model",
  core_concept: "Model the tasks and members tables with ownership.",
  ai_appropriate_tasks: [],
  human_required_tasks: [],
  explanation_gate_targets: ["ownership", "foreign keys"],
  gate_depth: "standard",
  unlock_condition: "",
  functional_unlock: "",
  is_current: true,
  completed_task_count: 3,
  total_task_count: 6,
};

const fullSections: WorkflowSections = {
  prompt_builder: {
    inputs: {},
    generated_prompt: "Design a schema for tasks and members with RLS.",
    why_stronger: "It scopes the task and names the constraints.",
    bad_prompt_comparison: "make me a database",
  },
  review_board: {
    files_changed: ["app/models.py", "app/routes/tasks.py"],
    ai_generated: "the Task model and the POST route",
    accepted: "the model",
    rejected: "an auth rewrite",
    edited_manually: "renamed a field",
    ai_assumptions: "assumed every task has a due date",
    least_confident: "the list query",
    out_of_scope_changes: null,
  },
  evidence: {
    entries: [{ kind: "test_output", content: "3 passed in 0.2s" }],
    summary: "the create + fetch cycle passes",
  },
  verification: {
    checks: [
      { check: "app_runs_locally", result: "pass", note: "uvicorn boots" },
      { check: "rls_wrong_user_checked", result: "pass", note: "user B gets 404" },
    ],
    explanation: "It shows ownership isolation works.",
  },
};

const gate: GateCurrent = { phase: 2, phase_title: "Data Model", state: "not_started" };

function makeInput(overrides: Partial<ReportInput> = {}): ReportInput {
  return {
    evaluation,
    answers: { purpose: "Help my study group track expenses.", scope: "small", stack: "FastAPI", self_assessment: "Sometimes", timeline: "6 weeks" },
    archetypeId: 2,
    phase,
    sections: fullSections,
    gate,
    ...overrides,
  };
}

describe("defenseStatus", () => {
  it("reports not_attempted when the gate has not started", () => {
    expect(defenseStatus(makeInput())).toBe("not_attempted");
  });
  it("reports passed when the current phase's gate state is passed", () => {
    expect(defenseStatus(makeInput({ gate: { ...gate, state: "passed" } }))).toBe("passed");
  });
  it("does NOT mark the current phase passed just because a prior phase's gate passed", () => {
    // On phase 2 with phase 1 already passed, the current phase's gate reads
    // not_started — its defense hasn't happened yet.
    const input = makeInput({
      evaluation: { ...evaluation, completed_phases: 1, recent_gate: { outcome: "passed", summary: "Phase 1 passed" } },
      gate: { ...gate, state: "not_started" },
    });
    expect(defenseStatus(input)).toBe("not_attempted");
  });
});

describe("buildReportMarkdown", () => {
  it("includes the real purpose and archetype", () => {
    const md = buildReportMarkdown(makeInput());
    expect(md).toContain("Help my study group track expenses.");
    expect(md).toContain("REST API Backend");
    expect(md).toContain("Design a schema for tasks and members with RLS.");
  });

  it("labels verification as self-reported and never leaks a numeric score", () => {
    const md = buildReportMarkdown(makeInput());
    expect(md.toLowerCase()).toContain("self-reported");
    // No "score: <n>" style leakage.
    expect(md).not.toMatch(/score[":\s]+\d/i);
  });

  it("marks missing sections honestly instead of inventing evidence", () => {
    const md = buildReportMarkdown(
      makeInput({ sections: { prompt_builder: null, review_board: null, evidence: null, verification: null } })
    );
    expect(md).toContain("No engineered prompt saved for this phase.");
    expect(md).toContain("No verification checks recorded for this phase.");
    expect(md).toContain("No evidence attached for this phase.");
  });

  it("says the gate is not attempted when it hasn't been", () => {
    const md = buildReportMarkdown(makeInput());
    expect(md).toContain("Defense not yet attempted");
  });

  it("labels skipped and N/A checks honestly, never as evidence (M13E.2)", () => {
    const md = buildReportMarkdown(
      makeInput({
        sections: {
          ...fullSections,
          verification: {
            checks: [
              { check: "app_runs_locally", result: "pass", note: "uvicorn boots" },
              { check: "smoke_test", result: "skipped", note: null },
              { check: "auth_boundary_checked", result: "not_applicable", note: "no auth yet" },
            ],
            explanation: null,
          },
        },
      })
    );
    expect(md).toContain("**skipped — not checked yet**");
    expect(md).toContain("**n/a — doesn't apply**");
    // The raw enum value never leaks into the export.
    expect(md).not.toContain("**not_applicable**");
  });

  it("ends with a single trailing newline and no giant gaps", () => {
    const md = buildReportMarkdown(makeInput());
    expect(md.endsWith("\n")).toBe(true);
    expect(md).not.toMatch(/\n{3,}/);
  });
});

describe("deriveSkills", () => {
  it("marks planning/prompting/reviewing/verification demonstrated when artifacts exist", () => {
    const skills = deriveSkills(makeInput());
    const by = Object.fromEntries(skills.map((s) => [s.skill, s.demonstrated]));
    expect(by["Planning"]).toBe(true);
    expect(by["Prompting"]).toBe(true);
    expect(by["Reviewing AI output"]).toBe(true);
    expect(by["Verification"]).toBe(true);
    expect(by["Security awareness"]).toBe(true); // rls check present
    expect(by["Explanation / defense"]).toBe(false); // gate not passed
  });

  it("credits explanation/defense once any phase gate has been passed", () => {
    const skills = deriveSkills(makeInput({ evaluation: { ...evaluation, completed_phases: 1 } }));
    const explanation = skills.find((s) => s.skill === "Explanation / defense");
    expect(explanation?.demonstrated).toBe(true);
  });

  it("marks nothing demonstrated when no artifacts exist", () => {
    const skills = deriveSkills(
      makeInput({ sections: { prompt_builder: null, review_board: null, evidence: null, verification: null } })
    );
    expect(skills.every((s) => !s.demonstrated)).toBe(true);
  });
});

describe("deriveWeakSpots", () => {
  it("flags every missing artifact and the un-attempted gate", () => {
    const weak = deriveWeakSpots(
      makeInput({ sections: { prompt_builder: null, review_board: null, evidence: null, verification: null } })
    );
    expect(weak.join(" ")).toContain("Prompt Builder");
    expect(weak.join(" ")).toContain("Review Board");
    expect(weak.join(" ")).toContain("Evidence Panel");
    expect(weak.join(" ")).toContain("Verification Lab");
    expect(weak.join(" ")).toContain("hasn’t been attempted");
  });

  it("is empty of gaps when everything is present and the gate passed", () => {
    const weak = deriveWeakSpots(makeInput({ gate: { ...gate, state: "passed" } }));
    expect(weak).toHaveLength(0);
  });
});

describe("deriveInterviewQuestions", () => {
  it("weaves in changed files and always covers data flow + verification", () => {
    const qs = deriveInterviewQuestions(makeInput());
    expect(qs.join(" ")).toContain("data flow");
    expect(qs.join(" ")).toContain("app/models.py");
    expect(qs.some((q) => q.toLowerCase().includes("verify"))).toBe(true);
  });
});
