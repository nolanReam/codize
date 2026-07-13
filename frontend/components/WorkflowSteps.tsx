"use client";

import Link from "next/link";

import { changeMapStepStatus } from "@/lib/changeMap";
import { reviewStepStatus } from "@/lib/review";
import type { StoredChangeMap, WorkflowSections } from "@/lib/types";

// The Codize Build Loop as navigable steps. "Generate" is deliberately not a
// page — that step happens in the student's external AI tool.
const STEPS: {
  label: string;
  href: string | null;
  section: keyof WorkflowSections | null;
  changeMap?: boolean;
  review?: boolean;
  note?: string;
}[] = [
  { label: "Plan + Prompt", href: "/app/phase/prompt", section: "prompt_builder" },
  { label: "Generate", href: null, section: null, note: "in your AI tool" },
  { label: "Bring Back", href: "/app/phase/import", section: "implementation_import" },
  { label: "Change Map", href: "/app/phase/change-map", section: null, changeMap: true },
  { label: "Review", href: "/app/phase/review", section: "review_board", review: true },
  { label: "Verify", href: "/app/phase/verify", section: "verification" },
  { label: "Evidence", href: "/app/phase/evidence", section: "evidence" },
  { label: "Explain", href: "/app/gate", section: null, note: "the gate" },
  { label: "Commit / Reflect", href: "/app/report", section: null, note: "defense report" },
];

export default function WorkflowSteps({
  sections,
  changeMap,
  current,
}: {
  sections: WorkflowSections | null;
  changeMap?: StoredChangeMap | null;
  current?: string;
}) {
  return (
    <div className="loop">
      {STEPS.map((step, idx) => {
        const mapStatus = step.changeMap ? changeMapStepStatus(changeMap ?? null) : null;
        const linkedReviewStatus = step.review
          ? reviewStepStatus(sections?.review_board ?? null, changeMap ?? null)
          : null;
        const done = step.changeMap
          ? mapStatus?.tone === "done"
          : step.review
            ? linkedReviewStatus?.tone === "done"
          : step.section != null && sections?.[step.section] != null;
        const dotTone = step.changeMap
          ? mapStatus?.tone
          : step.review
            ? linkedReviewStatus?.tone
            : done
              ? "done"
              : "idle";
        const note = mapStatus?.label ?? linkedReviewStatus?.label ?? step.note;
        const inner = (
          <>
            <span className={`dot ${dotTone}`} />
            <span className="n">{String(idx + 1).padStart(2, "0")}</span>
            <span>{step.label}</span>
            {note && <span className="n">({note})</span>}
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
