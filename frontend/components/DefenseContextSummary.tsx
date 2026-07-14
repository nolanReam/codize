import React from "react";

import {
  DEFENSE_TRUNCATION_EXPLANATION,
  orderedWorkflowSources,
  sourcePillClass,
  sourceStatePresentation,
} from "../lib/defenseContext";
import type { DefenseContextSummary as DefenseContextSummaryType } from "../lib/types";

export type DefenseContextSummaryState = "loading" | "ready" | "error";

export default function DefenseContextSummary({
  summary,
  state,
  onRetry,
}: {
  summary: DefenseContextSummaryType | null;
  state: DefenseContextSummaryState;
  onRetry: () => void;
}) {
  return (
    <section className="defense-context-summary" aria-labelledby="defense-record-heading">
      <h3 id="defense-record-heading">Project record for this Defense</h3>
      <p>
        Codize uses your saved project record to ask more relevant questions. You still explain
        the implementation in your own words.
      </p>
      <p className="muted">
        Your project record provides context. It does not answer the questions for you or
        guarantee a passing result.
      </p>

      {state === "loading" && (
        <p className="defense-context-status muted" role="status" aria-live="polite">
          Checking your project record…
        </p>
      )}

      {state === "error" && (
        <div className="defense-context-status" role="alert">
          <p>
            <strong>Project-record details are temporarily unavailable.</strong>
          </p>
          <p className="muted">
            You can retry loading the context. Your saved workflow work has not been changed.
          </p>
          <button className="btn small" type="button" onClick={onRetry}>
            Retry project record
          </button>
        </div>
      )}

      {state === "ready" && summary && (
        <>
          <ul className="defense-source-list" aria-label="Workflow sources available to Defense">
            {orderedWorkflowSources(summary).map((source) => {
              const presentation = sourceStatePresentation(source.state);
              return (
                <li key={source.source_id}>
                  <div className="defense-source-heading">
                    <strong>{source.label}</strong>
                    <span className={`pill ${sourcePillClass(source.state)}`}>
                      {presentation.label}
                    </span>
                  </div>
                  <p className="muted">{presentation.description}</p>
                  {source.truncated && (
                    <p className="defense-source-truncation">Long details shortened</p>
                  )}
                </li>
              );
            })}
          </ul>
          {(summary.has_truncation || summary.workflow_sources.some((source) => source.truncated)) && (
            <p className="defense-truncation-note">{DEFENSE_TRUNCATION_EXPLANATION}</p>
          )}
        </>
      )}
    </section>
  );
}
