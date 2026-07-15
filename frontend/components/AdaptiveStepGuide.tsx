"use client";

import { useEffect, useId, useState } from "react";

import { useGuidedProjectNavigation } from "./GuidedProjectNavigationProvider";
import {
  guidanceStorageKey,
  readGuidanceOpen,
  writeGuidanceOpen,
} from "@/lib/guidanceDisclosure";
import type { GuidedStageId } from "@/lib/guidedProjectNavigation";
import { WORKFLOW_GUIDANCE } from "@/lib/workflowGuidance";

export default function AdaptiveStepGuide({ stage }: { stage: GuidedStageId }) {
  const { entryProfile, navigation, userId } = useGuidedProjectNavigation();
  const depth = entryProfile?.guidance_depth ?? "standard";
  const defaultOpen = depth === "more";
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  const content = WORKFLOW_GUIDANCE[stage];
  const savedStage = navigation.projectRecord.some((item) => item.stageId === stage);
  const compactSummary = depth === "standard"
    ? `${content.why} ${content.action}`
    : content.why;

  useEffect(() => {
    const key = guidanceStorageKey(userId, stage);
    const stored = readGuidanceOpen(window.localStorage, key);
    setOpen(stored ?? defaultOpen);
  }, [defaultOpen, stage, userId]);

  function toggle() {
    const next = !open;
    setOpen(next);
    writeGuidanceOpen(window.localStorage, guidanceStorageKey(userId, stage), next);
  }

  return (
    <section className={`adaptive-guide depth-${depth}`} aria-labelledby={`${contentId}-title`}>
      <div className="adaptive-guide-heading">
        <div>
          <p className="adaptive-guide-kicker">
            {savedStage ? "Step guide" : depth === "more" ? "A quick guide" : "Why this step matters"}
          </p>
          <h2 id={`${contentId}-title`}>{content.title}</h2>
        </div>
        <button
          className="adaptive-guide-toggle"
          type="button"
          aria-expanded={open}
          aria-controls={contentId}
          onClick={toggle}
        >
          {open ? "Hide guide" : "Show guide"}
        </button>
      </div>
      {!open && <p className="adaptive-guide-summary">{compactSummary}</p>}
      <div id={contentId} hidden={!open} className="adaptive-guide-body">
        <div>
          <h3>Why this step matters</h3>
          <p>{content.why}</p>
        </div>
        <div>
          <h3>What to do</h3>
          <p>{content.action}</p>
        </div>
        <div className="adaptive-guide-example">
          <h3>Example</h3>
          <p>{content.example}</p>
        </div>
        {entryProfile?.recovery_emphasis && content.recovery && (
          <p className="adaptive-guide-recovery"><strong>Patch-loop focus:</strong> {content.recovery}</p>
        )}
        {content.terms && content.terms.length > 0 && (
          <details className="help adaptive-guide-terms">
            <summary>Plain-language terms</summary>
            <dl>
              {content.terms.map(({ term, definition }) => (
                <div key={term}>
                  <dt>{term}</dt>
                  <dd>{definition}</dd>
                </div>
              ))}
            </dl>
          </details>
        )}
      </div>
    </section>
  );
}
