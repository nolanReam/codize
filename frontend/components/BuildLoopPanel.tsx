"use client";

import { useEffect, useRef, useState } from "react";

import { WORKFLOW_JOURNEY, type WorkflowJourneyStageId } from "@/lib/workflowJourney";

interface StageDetail {
  role: "builder" | "codize";
  description: string;
  artifact: string;
  sample: { kind: "ok" | "warn" | "dim" | "plain"; text: string }[];
}

const DETAIL_BY_STAGE: Record<WorkflowJourneyStageId, StageDetail> = {
  prompt: {
    role: "builder",
    description: "Set scope, constraints, and the checks you expect before using your AI tool.",
    artifact: "prompt_builder",
    sample: [
      { kind: "plain", text: "scope: assignment filters" },
      { kind: "plain", text: "constraint: preserve local data" },
    ],
  },
  import: {
    role: "builder",
    description: "Return with the response, diff, changed files, or your own summary.",
    artifact: "implementation_import",
    sample: [
      { kind: "plain", text: "changed: app.js, styles.css" },
      { kind: "dim", text: "student-provided material" },
    ],
  },
  change_map: {
    role: "codize",
    description: "Correct a grounded draft of what appears to have changed.",
    artifact: "change_map",
    sample: [
      { kind: "warn", text: "AI-inferred until reviewed" },
      { kind: "plain", text: "source: app.js" },
    ],
  },
  review: {
    role: "builder",
    description: "Choose what to keep, revise, remove, test, or inspect.",
    artifact: "review_board",
    sample: [
      { kind: "ok", text: "keep: filter state" },
      { kind: "warn", text: "test: refresh behavior" },
    ],
  },
  verification: {
    role: "builder",
    description: "Perform checks and record what actually happened.",
    artifact: "verification",
    sample: [
      { kind: "ok", text: "passed: add assignment" },
      { kind: "dim", text: "skipped stays skipped" },
    ],
  },
  evidence: {
    role: "builder",
    description: "Attach available support without turning a claim into proof.",
    artifact: "evidence",
    sample: [
      { kind: "plain", text: "terminal output" },
      { kind: "dim", text: "student-provided evidence" },
    ],
  },
  defense: {
    role: "codize",
    description: "Answer grounded questions about your own implementation.",
    artifact: "gate/current",
    sample: [
      { kind: "plain", text: "turn_01: why this state shape?" },
      { kind: "plain", text: "turn_03: what breaks first?" },
    ],
  },
  report: {
    role: "codize",
    description: "Open the provenance-aware record of the workflow and outcome.",
    artifact: "defense_report.md",
    sample: [
      { kind: "ok", text: "workflow record saved" },
      { kind: "dim", text: "uncertainty preserved" },
    ],
  },
};

const STAGES = WORKFLOW_JOURNEY.map((stage, index) => ({
  ...stage,
  number: String(index + 1).padStart(2, "0"),
  ...DETAIL_BY_STAGE[stage.id],
}));

const ROLE_LABEL: Record<StageDetail["role"], string> = {
  builder: "you",
  codize: "codize",
};

export default function BuildLoopPanel() {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const bucketRef = useRef(-1);
  const [mode, setMode] = useState<"static" | "scroll">("static");
  const [active, setActive] = useState(2);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const query = window.matchMedia("(max-width: 900px)");
    const apply = () => setMode(query.matches ? "static" : "scroll");
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (mode !== "scroll") return;
    let animationFrame = 0;
    const onScroll = () => {
      if (animationFrame) return;
      animationFrame = requestAnimationFrame(() => {
        animationFrame = 0;
        const element = trackRef.current;
        if (!element) return;
        const rect = element.getBoundingClientRect();
        const total = rect.height - window.innerHeight;
        const progress = total > 0 ? Math.min(1, Math.max(0, -rect.top / total)) : 0;
        const hysteresis = 0.22;
        const position = progress * STAGES.length;
        const current = bucketRef.current;
        let next: number;
        if (current < 0) next = Math.min(STAGES.length - 1, Math.floor(position));
        else if (position >= current + 1 + hysteresis) {
          next = Math.min(STAGES.length - 1, Math.floor(position - hysteresis));
        } else if (position < current - hysteresis) {
          next = Math.max(0, Math.floor(position + hysteresis));
        } else next = current;
        if (bucketRef.current !== next) {
          bucketRef.current = next;
          setActive(next);
        }
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [mode]);

  const isScroll = mode === "scroll";
  return (
    <section
      ref={trackRef}
      id="workflow"
      className={isScroll ? "bl-track" : "bl-track bl-track-static"}
      aria-label="The Codize eight-stage Journey"
    >
      <div className="bl-sticky">
        <div className="scene-head">
          <p className="eyebrow">{"// the codize journey"}</p>
          <h2>Review AI like a <em>teammate</em>, not a magic box.</h2>
          <p className="lead">Use your AI tool after Prompt Builder. Codize trains the full record around it.</p>
        </div>
        <div className="bl">
          {STAGES.map((stage, index) => {
            const isActive = index === active;
            return (
              <button
                key={stage.id}
                type="button"
                className={`bl-card ${stage.role}${isActive ? " active" : ""}`}
                aria-expanded={isActive}
                onMouseEnter={isScroll ? undefined : () => setActive(index)}
                onFocus={() => setActive(index)}
                onClick={() => setActive(index)}
              >
                <span className="bl-top">
                  <span className="bl-n">{stage.number}</span>
                  <span className={`bl-role ${stage.role}`}>{ROLE_LABEL[stage.role]}</span>
                </span>
                <span className="bl-title">{stage.label}</span>
                <span className="bl-title-side" aria-hidden="true">{stage.label}</span>
                <span className="bl-detail">
                  <span className="bl-desc">{stage.description}</span>
                  <span className="bl-sample">
                    <span className="bl-artifact">{stage.artifact}</span>
                    {stage.sample.map((line) => (
                      <span key={line.text} className={`bl-line ${line.kind}`}>{line.text}</span>
                    ))}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
        {isScroll && (
          <p className="bl-hint" aria-hidden="true">
            stage {STAGES[active].number} / 08 &middot; scroll to advance
          </p>
        )}
      </div>
    </section>
  );
}
