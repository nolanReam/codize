"use client";

import { useGuidedProjectNavigation } from "./GuidedProjectNavigationProvider";

// Compact page-level orientation driven by the same saved-state model as the
// desktop and mobile shell. It is deliberately not a second set of module
// links: the global Continue action owns forward navigation, while completed
// work remains available through Project Record.
export default function WorkflowSteps() {
  const { navigation, state } = useGuidedProjectNavigation();
  if (state === "error") {
    return (
      <p className="muted" role="status">
        Project progress is temporarily unavailable. Your current page remains open.
      </p>
    );
  }
  return (
    <ol className="loop guided-loop" aria-label="Project journey" aria-busy={state === "loading"}>
      {(state === "loading" ? [] : navigation.journey).map((step, index) => (
        <li className={`step ${step.state}`} key={step.id}>
          <span className={`dot ${step.state}`} aria-hidden="true" />
          <span className="n">{String(index + 1).padStart(2, "0")}</span>
          <span>{step.label}</span>
          <span className="n">({step.stateLabel})</span>
        </li>
      ))}
      {state === "loading" && <li className="loading" role="status">Loading project journey</li>}
    </ol>
  );
}
