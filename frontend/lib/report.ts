// Project Defense Report assembly (M13C.2) — pure, client-side, no LLM. The
// report is built entirely from data the backend already exposes to the owner
// (intake, phase, workflow artifacts, gate state, evaluation). It never invents
// evidence and never surfaces private backend data: raw gate scores, evaluator
// reasoning, hidden thresholds, and internal prompts are not in any input here
// by backend design, and nothing here reconstructs them.

import type {
  Evaluation,
  GateCurrent,
  PhaseView,
  VerificationCheckId,
  WorkflowSections,
} from "./types";

// The three fixed archetypes (spec-fixed — there is never a fourth).
export const ARCHETYPE_NAMES: Record<number, string> = {
  1: "AI-Powered App",
  2: "REST API Backend",
  3: "Full-Stack Web App",
};

// Human labels for the fixed 8-check verification enum (mirrors the Verification Lab).
export const VERIFICATION_LABELS: Record<VerificationCheckId, string> = {
  app_runs_locally: "The app runs locally",
  smoke_test: "Ran at least one smoke test",
  api_route_checked: "The relevant API route responds correctly",
  ui_flow_checked: "The relevant UI flow works",
  failure_case_tested: "Tested at least one failure case",
  auth_boundary_checked: "Auth boundary checked",
  secret_exposure_checked: "No secrets exposed in frontend/repo",
  rls_wrong_user_checked: "Wrong-user access blocked (RLS)",
};

const SECURITY_CHECKS: VerificationCheckId[] = [
  "auth_boundary_checked",
  "secret_exposure_checked",
  "rls_wrong_user_checked",
];

export interface ReportInput {
  evaluation: Evaluation;
  answers: Record<string, string | null> | null;
  archetypeId: number | null;
  phase: PhaseView | null;
  sections: WorkflowSections | null;
  gate: GateCurrent | null;
}

// --- defense status (safe, no score/reasoning leakage) -----------------------

export type DefenseStatus =
  | "passed"
  | "cooldown"
  | "in_progress"
  | "not_attempted";

// Status of the CURRENT phase's defense only. On non-final phases a pass
// advances the phase, so the current phase's gate reads "not_started" again —
// which is honest: this phase hasn't been defended yet. Prior passes are shown
// separately as the "latest gate note", never conflated into this label.
export function defenseStatus(input: ReportInput): DefenseStatus {
  const state = input.gate?.state;
  if (state === "passed") return "passed";
  if (state === "cooldown") return "cooldown";
  if (state === "in_progress") return "in_progress";
  return "not_attempted";
}

export function defenseLabel(status: DefenseStatus): string {
  switch (status) {
    case "passed":
      return "Defense passed for this phase";
    case "cooldown":
      return "Recent attempt didn’t pass — in cooldown";
    case "in_progress":
      return "Defense in progress";
    case "not_attempted":
      return "Defense not yet attempted";
  }
}

// --- skills demonstrated -----------------------------------------------------

export interface SkillRow {
  skill: string;
  demonstrated: boolean;
  note: string;
}

export function deriveSkills(input: ReportInput): SkillRow[] {
  const s = input.sections;
  const prompt = s?.prompt_builder ?? null;
  const review = s?.review_board ?? null;
  const verification = s?.verification ?? null;
  // Project-level: has the student passed any gate so far? (Current-phase
  // defenseStatus resets after each pass; completed_phases carries the history.)
  const anyGatePassed = (input.evaluation.completed_phases ?? 0) > 0 || defenseStatus(input) === "passed";

  const securityTouched =
    (verification?.checks ?? []).some(
      (c) => SECURITY_CHECKS.includes(c.check) && c.result !== "not_applicable"
    ) || (review?.out_of_scope_changes ?? "").trim().length > 0;

  return [
    {
      skill: "Planning",
      demonstrated: prompt != null,
      note: prompt ? "Scoped the work in a deliberate prompt before generating." : "No planned prompt saved for this phase.",
    },
    {
      skill: "Prompting",
      demonstrated: !!prompt?.generated_prompt,
      note: prompt?.generated_prompt
        ? "Engineered a constraint-driven prompt rather than a vague ask."
        : "No engineered prompt on record.",
    },
    {
      skill: "Reviewing AI output",
      demonstrated: review != null,
      note: review
        ? "Recorded what the AI generated and what was accepted, rejected, or edited."
        : "No review of the AI’s output recorded.",
    },
    {
      skill: "Verification",
      demonstrated: (verification?.checks ?? []).length > 0,
      note: verification?.checks?.length
        ? `Ran ${verification.checks.length} self-reported check(s).`
        : "No verification checks recorded.",
    },
    {
      skill: "Explanation / defense",
      demonstrated: anyGatePassed,
      note: anyGatePassed
        ? "Passed the Interrogation Gate for at least one phase."
        : "No Interrogation Gate passed yet.",
    },
    {
      skill: "Security awareness",
      demonstrated: securityTouched,
      note: securityTouched
        ? "Considered auth / secrets / ownership as part of the work."
        : "No security-specific checks recorded yet.",
    },
  ];
}

// --- weak spots / next actions -----------------------------------------------

export function deriveWeakSpots(input: ReportInput): string[] {
  const gaps: string[] = [];
  const s = input.sections;
  if (!s?.prompt_builder) gaps.push("No engineered prompt saved for this phase (Prompt Builder).");
  if (!s?.review_board) gaps.push("The AI’s output for this phase hasn’t been reviewed (Review Board).");
  if (!s?.evidence || (s.evidence.entries ?? []).length === 0)
    gaps.push("No evidence attached yet (Evidence Panel).");
  if (!s?.verification || (s.verification.checks ?? []).length === 0)
    gaps.push("No verification checks recorded (Verification Lab).");
  else {
    const failed = s.verification.checks.filter((c) => c.result === "fail");
    if (failed.length)
      gaps.push(
        `${failed.length} verification check(s) recorded as failing — worth resolving before defending.`
      );
  }

  const status = defenseStatus(input);
  if (status === "not_attempted") gaps.push("The Interrogation Gate hasn’t been attempted for this phase.");
  if (status === "cooldown") gaps.push("A recent gate attempt didn’t pass; review your work before retrying.");

  return gaps;
}

// --- interview / defense questions (derived, no LLM) -------------------------

export function deriveInterviewQuestions(input: ReportInput): string[] {
  const questions: string[] = [];
  const phaseTitle = input.phase?.phase_title ?? input.evaluation.phase_title;
  const files = input.sections?.review_board?.files_changed ?? [];
  const assumptions = input.sections?.review_board?.ai_assumptions ?? null;
  const archetype = input.archetypeId ? ARCHETYPE_NAMES[input.archetypeId] : null;

  questions.push("Walk me through your project’s data flow, end to end.");
  if (phaseTitle) questions.push(`In “${phaseTitle}”, what did you build and why is it structured that way?`);
  questions.push("What did the AI generate that you had to verify yourself, and how did you verify it?");
  if (files.length)
    questions.push(
      `You changed ${files.slice(0, 3).join(", ")}${files.length > 3 ? ", …" : ""}. What breaks if one of those changes?`
    );
  else questions.push("What would break if the route or table you worked on changed?");
  questions.push("How do you know this feature actually works — not just that it looks done?");
  if (assumptions && assumptions.trim())
    questions.push("You noted an assumption the AI made. Was it correct, and how did you check?");
  else questions.push("What assumption did the AI make that you had to catch?");
  if (archetype === "Full-Stack Web App" || archetype === "AI-Powered App")
    questions.push("Where does user input reach the database or the UI, and how is it validated?");
  if (archetype === "REST API Backend" || archetype === "Full-Stack Web App")
    questions.push("How does your ownership / RLS model stop one user from reading another’s data?");

  return questions;
}

// --- markdown assembly -------------------------------------------------------

function line(label: string, value: string | null | undefined): string {
  return value && value.trim() ? `- **${label}:** ${value.trim()}` : `- **${label}:** _Not provided_`;
}

function section(title: string, body: string[]): string {
  return [`## ${title}`, "", ...body, ""].join("\n");
}

export function buildReportMarkdown(input: ReportInput): string {
  const { evaluation, answers, phase, sections } = input;
  const archetype = input.archetypeId ? ARCHETYPE_NAMES[input.archetypeId] : null;
  const status = defenseStatus(input);
  const out: string[] = [];

  out.push("# Project Defense Report", "");
  out.push(
    "_Assembled by Codize from your own submitted workflow. Verification below is self-reported; " +
      "this report is a record of what you did and can explain, not a guarantee that the project works._",
    ""
  );
  out.push(`_Generated ${new Date().toISOString()}_`, "");

  // 1. Project Overview
  out.push(
    section("1. Project Overview", [
      line("Problem being solved (and who it helps)", answers?.purpose ?? null),
      line("Scope", answers?.scope ?? null),
      line("Stack", answers?.stack ?? null),
      line("Archetype", archetype),
      line(
        "Current phase",
        evaluation.current_phase != null
          ? `Phase ${evaluation.current_phase} of ${evaluation.total_phases ?? "?"} — ${
              phase?.phase_title ?? evaluation.phase_title ?? ""
            }`.trim()
          : null
      ),
      line("Core concept for this phase", phase?.core_concept ?? null),
    ])
  );

  // 2. AI Workflow Evidence
  const pb = sections?.prompt_builder ?? null;
  const rb = sections?.review_board ?? null;
  const workflowBody: string[] = [];
  if (pb) {
    workflowBody.push("**Engineered prompt**", "", "```", (pb.generated_prompt || "").trim(), "```", "");
    if (pb.why_stronger?.trim()) workflowBody.push(line("Why the prompt is stronger", pb.why_stronger), "");
  } else {
    workflowBody.push("_No engineered prompt saved for this phase._", "");
  }
  if (rb) {
    workflowBody.push(
      line("Files changed", (rb.files_changed ?? []).join(", ") || null),
      line("What the AI generated", rb.ai_generated),
      line("Accepted", rb.accepted),
      line("Rejected", rb.rejected),
      line("Edited manually", rb.edited_manually),
      line("AI assumptions identified", rb.ai_assumptions),
      line("Least confident about", rb.least_confident),
      line("Out-of-scope changes", rb.out_of_scope_changes)
    );
  } else {
    workflowBody.push("_The AI’s output for this phase hasn’t been reviewed yet._");
  }
  out.push(section("2. AI Workflow Evidence", workflowBody));

  // 3. Verification Evidence
  const ver = sections?.verification ?? null;
  const ev = sections?.evidence ?? null;
  const verBody: string[] = [];
  if (ver?.checks?.length) {
    verBody.push("**Self-reported checks**", "");
    for (const c of ver.checks) {
      const label = VERIFICATION_LABELS[c.check] ?? c.check;
      const note = c.note?.trim() ? ` — ${c.note.trim()}` : "";
      verBody.push(`- ${label}: **${c.result}**${note}`);
    }
    verBody.push("");
    if (ver.explanation?.trim()) verBody.push(line("What this verification proves", ver.explanation), "");
  } else {
    verBody.push("_No verification checks recorded for this phase._", "");
  }
  if (ev?.entries?.length) {
    verBody.push("**Submitted evidence**", "");
    for (const entry of ev.entries) {
      const oneLine = entry.content.replace(/\s+/g, " ").trim();
      const clipped = oneLine.length > 300 ? `${oneLine.slice(0, 300)}…` : oneLine;
      verBody.push(`- \`${entry.kind}\`: ${clipped}`);
    }
    verBody.push("");
    if (ev.summary?.trim()) verBody.push(line("What the evidence shows", ev.summary), "");
  } else {
    verBody.push("_No evidence attached for this phase._");
  }
  out.push(section("3. Verification Evidence", verBody));

  // 4. Project Defense Status
  const defenseBody: string[] = [line("Defense status", defenseLabel(status))];
  if (status === "cooldown" && input.gate?.cooldown_seconds_remaining != null) {
    defenseBody.push(
      line(
        "Retry available in",
        `about ${Math.max(1, Math.ceil(input.gate.cooldown_seconds_remaining / 60))} minute(s)`
      )
    );
  }
  if (evaluation.recent_gate?.summary) defenseBody.push(line("Latest gate note", evaluation.recent_gate.summary));
  defenseBody.push("", "_The gate’s numeric score and private evaluator reasoning are intentionally not shown._");
  out.push(section("4. Project Defense Status", defenseBody));

  // 5. Skills Demonstrated
  out.push(
    section(
      "5. Skills Demonstrated",
      deriveSkills(input).map((row) => `- ${row.demonstrated ? "✅" : "⬜"} **${row.skill}** — ${row.note}`)
    )
  );

  // 6. Weak Spots / Next Actions
  const weak = deriveWeakSpots(input);
  const weakBody = weak.length ? weak.map((w) => `- ${w}`) : ["- No obvious gaps for this phase — nice."];
  weakBody.push("", line("Recommended next action", evaluation.next_action));
  out.push(section("6. Weak Spots / Next Actions", weakBody));

  // 7. Interview / Defense Questions
  out.push(
    section(
      "7. Interview / Defense Questions",
      deriveInterviewQuestions(input).map((q) => `- ${q}`)
    )
  );

  return out.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
}
