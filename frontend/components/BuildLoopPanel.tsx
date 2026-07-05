"use client";

import { useState } from "react";

// The Codize Build Loop as an interactive instrument panel: one stage expands
// at a time (hover / focus / click), the rest compress. Desktop is a
// horizontal expanding rail; under 900px it becomes a vertical accordion.
// Pure CSS transitions — reduced motion makes the expansion instant.

interface WorkflowStage {
  id: string;
  number: string;
  title: string;
  role: "builder" | "ai-tool" | "codize";
  description: string;
  artifact: string;
  sample: { kind: "ok" | "warn" | "dim" | "plain"; text: string }[];
}

const STAGES: WorkflowStage[] = [
  {
    id: "plan",
    number: "01",
    title: "Plan",
    role: "builder",
    description: "Decide the architecture before the AI writes a line.",
    artifact: "plan.md",
    sample: [
      { kind: "plain", text: "goal: study planner MVP" },
      { kind: "plain", text: "stack: fastapi + supabase" },
      { kind: "dim", text: "no-touch: auth/, migrations/" },
    ],
  },
  {
    id: "prompt",
    number: "02",
    title: "Prompt",
    role: "builder",
    description: "Ask with scope, constraints, and no-touch zones.",
    artifact: "prompt_builder",
    sample: [
      { kind: "plain", text: "scope: one endpoint, one table" },
      { kind: "plain", text: "constraint: RLS stays on" },
      { kind: "dim", text: "do not edit: models.py" },
    ],
  },
  {
    id: "generate",
    number: "03",
    title: "Generate",
    role: "ai-tool",
    description: "Your AI tool creates the first pass. It always did.",
    artifact: "diff",
    sample: [
      { kind: "plain", text: "+214 lines across 6 files" },
      { kind: "warn", text: "unreviewed until you read it" },
    ],
  },
  {
    id: "review",
    number: "04",
    title: "Review",
    role: "codize",
    description: "Read the diff. Accept, reject, or edit — deliberately.",
    artifact: "review_board",
    sample: [
      { kind: "ok", text: "accepted: routes/tasks.py" },
      { kind: "warn", text: "rejected: rewrite of auth.py" },
      { kind: "dim", text: "reason: out of scope" },
    ],
  },
  {
    id: "verify",
    number: "05",
    title: "Verify",
    role: "codize",
    description: "Prove behavior with evidence, not vibes.",
    artifact: "verification_lab",
    sample: [
      { kind: "ok", text: "✓ pytest — 14/14" },
      { kind: "ok", text: "✓ manual: login flow" },
      { kind: "dim", text: "evidence: commit 8f3ac21" },
    ],
  },
  {
    id: "explain",
    number: "06",
    title: "Explain",
    role: "codize",
    description: "Defend what changed in a live gate.",
    artifact: "gate/current",
    sample: [
      { kind: "plain", text: "turn_01: why this schema?" },
      { kind: "plain", text: "turn_03: what breaks first?" },
      { kind: "ok", text: "verdict: PASS" },
    ],
  },
  {
    id: "commit",
    number: "07",
    title: "Commit / Reflect",
    role: "builder",
    description: "Ship it with a Defense Report behind it.",
    artifact: "defense_report.md",
    sample: [
      { kind: "ok", text: "report exported" },
      { kind: "dim", text: "next phase unlocked" },
    ],
  },
];

const ROLE_LABEL: Record<WorkflowStage["role"], string> = {
  builder: "you",
  "ai-tool": "your AI tool",
  codize: "codize",
};

export default function BuildLoopPanel() {
  const [active, setActive] = useState(3); // open on Review — Codize's value

  return (
    <div className="bl">
      {STAGES.map((stage, i) => {
        const isActive = i === active;
        return (
          <button
            key={stage.id}
            type="button"
            className={`bl-card ${stage.role}${isActive ? " active" : ""}`}
            aria-expanded={isActive}
            onMouseEnter={() => setActive(i)}
            onFocus={() => setActive(i)}
            onClick={() => setActive(i)}
          >
            <span className="bl-top">
              <span className="bl-n">{stage.number}</span>
              <span className={`bl-role ${stage.role}`}>{ROLE_LABEL[stage.role]}</span>
            </span>
            <span className="bl-title">{stage.title}</span>
            <span className="bl-title-side" aria-hidden="true">
              {stage.title}
            </span>
            <span className="bl-detail">
              <span className="bl-desc">{stage.description}</span>
              <span className="bl-sample">
                <span className="bl-artifact">{stage.artifact}</span>
                {stage.sample.map((s) => (
                  <span key={s.text} className={`bl-line ${s.kind}`}>
                    {s.text}
                  </span>
                ))}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
