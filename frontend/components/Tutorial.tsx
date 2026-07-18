"use client";

import { useEffect, useRef } from "react";

import { WORKFLOW_JOURNEY, type WorkflowJourneyStageId } from "@/lib/workflowJourney";

export const TUTORIAL_SEEN_KEY = "codize:tutorial-seen";

const BODY_BY_STAGE: Record<WorkflowJourneyStageId, string> = {
  prompt: "Plan one scoped ask, then use that prompt in your own AI tool.",
  import: "Return with the response, diff, changed files, or your own summary.",
  change_map: "Correct Codize's draft of what appears to have changed; it is not proof.",
  review: "Record what you decide to keep, revise, remove, test, or inspect.",
  verification: "Perform checks and record passed, failed, skipped, or not-applicable results honestly.",
  evidence: "Add available support for recorded results without overstating it.",
  defense: "Explain your implementation in your own words after the phase record is ready.",
  report: "Open the provenance-aware record of your workflow and Defense outcome.",
};

export default function Tutorial({ onClose }: { onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="How Codize works"
        onClick={(event) => event.stopPropagation()}
      >
        <span className="pill accent">How Codize works</span>
        <p className="muted" style={{ marginTop: 14 }}>
          After five intake questions and a phase roadmap, every phase follows the same eight-stage
          Journey. Reopen this map anytime from Help.
        </p>
        <ol className="tutorial-steps">
          {WORKFLOW_JOURNEY.map((stage) => (
            <li key={stage.id}>
              <span>
                <strong>{stage.label}.</strong> {BODY_BY_STAGE[stage.id]}
              </span>
            </li>
          ))}
        </ol>
        <button
          ref={closeRef}
          className="btn primary"
          style={{ width: "100%", marginTop: 12 }}
          onClick={onClose}
        >
          Got it &mdash; let&rsquo;s build
        </button>
      </div>
    </div>
  );
}
