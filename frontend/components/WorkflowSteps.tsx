"use client";

import Link from "next/link";

import type { WorkflowSections } from "@/lib/types";

// The Codize Build Loop as navigable steps. "Generate" is deliberately not a
// page — that step happens in the student's external AI tool.
const STEPS: {
  label: string;
  href: string | null;
  section: keyof WorkflowSections | null;
  note?: string;
}[] = [
  { label: "Plan + Prompt", href: "/app/phase/prompt", section: "prompt_builder" },
  { label: "Generate", href: null, section: null, note: "in your AI tool" },
  { label: "Bring Back", href: "/app/phase/import", section: "implementation_import" },
  { label: "Review", href: "/app/phase/review", section: "review_board" },
  { label: "Verify", href: "/app/phase/evidence", section: "evidence" },
  { label: "Prove", href: "/app/phase/verify", section: "verification" },
  { label: "Explain", href: "/app/gate", section: null, note: "the gate" },
  { label: "Commit / Reflect", href: "/app/report", section: null, note: "defense report" },
];

export default function WorkflowSteps({
  sections,
  current,
}: {
  sections: WorkflowSections | null;
  current?: string;
}) {
  return (
    <div className="loop">
      {STEPS.map((step, idx) => {
        const done = step.section != null && sections?.[step.section] != null;
        const inner = (
          <>
            <span className={`dot${done ? " done" : ""}`} />
            <span className="n">{String(idx + 1).padStart(2, "0")}</span>
            <span>{step.label}</span>
            {step.note && <span className="n">({step.note})</span>}
          </>
        );
        const cls = `step${current === step.label ? " current" : ""}`;
        return (
          <span key={step.label} style={{ display: "contents" }}>
            {idx > 0 && <span className="sep">→</span>}
            {step.href ? (
              <Link href={step.href} className={cls}>
                {inner}
              </Link>
            ) : (
              <span className={cls}>{inner}</span>
            )}
          </span>
        );
      })}
    </div>
  );
}
