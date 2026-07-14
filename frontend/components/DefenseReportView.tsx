import React from "react";

import {
  changeMapProvenanceLabel,
  defenseOutcomeLabel,
  defenseOutcomeTone,
  evidenceStatusPresentation,
  reportCategoryLabel,
  reportEvidenceKindLabel,
  reportSourceSummaries,
  reviewDecisionPresentation,
  safeEvidenceHref,
  sourceHasReportContent,
  verificationResultPresentation,
  workflowContextSourcePresentation,
} from "../lib/report";
import { sourcePillClass, sourceStatePresentation } from "../lib/defenseContext";
import type {
  DefenseReport,
  ReportEvidenceEntry,
  ReportManualReviewContext,
  WorkflowArtifactState,
} from "../lib/types";

function SourceState({ state, truncated }: { state: WorkflowArtifactState; truncated: boolean }) {
  const presentation = sourceStatePresentation(state);
  return (
    <div className="report-source-state">
      <span className={`pill ${sourcePillClass(state)}`}>{presentation.label}</span>
      {truncated && <span className="report-truncated-label">Long details shortened</span>}
    </div>
  );
}

function EmptySource({ state }: { state: WorkflowArtifactState }) {
  return <p className="empty report-empty-source">{sourceStatePresentation(state).description}</p>;
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="report-detail">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function EvidenceEntryView({ entry }: { entry: ReportEvidenceEntry }) {
  const href = safeEvidenceHref(entry);
  return (
    <li className="report-evidence-entry">
      <span className="report-kicker">{reportEvidenceKindLabel(entry.kind)}</span>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="report-safe-link">
          {entry.content}
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      ) : (
        <span className="report-plain-text">{entry.content}</span>
      )}
    </li>
  );
}

function ManualReview({ manual }: { manual: ReportManualReviewContext }) {
  return (
    <div className="report-item">
      <div className="report-item-heading">
        <strong>Earlier manual Review record</strong>
        <span className="pill">Manual record</span>
      </div>
      <dl className="report-details">
        <Detail label="Files changed" value={manual.files_changed.join(", ") || null} />
        <Detail label="AI generated" value={manual.ai_generated} />
        <Detail label="Accepted" value={manual.accepted} />
        <Detail label="Rejected" value={manual.rejected} />
        <Detail label="Edited manually" value={manual.edited_manually} />
        <Detail label="AI assumptions" value={manual.ai_assumptions} />
        <Detail label="Least confident" value={manual.least_confident} />
        <Detail label="Out-of-scope changes" value={manual.out_of_scope_changes} />
      </dl>
    </div>
  );
}

export default function DefenseReportView({ report }: { report: DefenseReport }) {
  const context = report.workflow_context;
  const contextSource = workflowContextSourcePresentation(report.workflow_context_source);

  return (
    <article className="defense-report" aria-label={`Defense Report for phase ${report.phase_number}`}>
      <section className="report-hero" aria-labelledby="report-outcome-heading">
        <div>
          <p className="report-kicker">Phase {report.phase_number}</p>
          <h2 id="report-outcome-heading">{report.phase_title}</h2>
          <p>
            This report brings together your saved workflow record, your Project Defense
            responses, and the evaluator outcome.
          </p>
        </div>
        <span className={`pill report-outcome-pill ${defenseOutcomeTone(report.defense.state)}`}>
          {defenseOutcomeLabel(report.defense.state)}
        </span>
      </section>

      <section className="report-context-source" aria-labelledby="report-context-source-heading">
        <p className="report-kicker">Workflow context source</p>
        <h2 id="report-context-source-heading">{contextSource.label}</h2>
        <p>{contextSource.description}</p>
      </section>

      <aside className="report-truth-notice" aria-labelledby="report-truth-heading">
        <h2 id="report-truth-heading">How to read this report</h2>
        <p>{report.truth_notice}</p>
      </aside>

      <section className="report-section" aria-labelledby="report-record-heading">
        <div className="report-section-heading">
          <div>
            <p className="report-kicker">Project record</p>
            <h2 id="report-record-heading">What was available</h2>
          </div>
          <SourceState state={context.state} truncated={context.content_truncated} />
        </div>
        <ul className="report-source-overview">
          {reportSourceSummaries(context).map((source) => (
            <li key={source.sourceId}>
              <div className="report-source-overview-heading">
                <strong>{source.label}</strong>
                <SourceState state={source.state} truncated={source.truncated} />
              </div>
              <p>{source.stateDescription}</p>
            </li>
          ))}
        </ul>
        {context.content_truncated && (
          <p className="report-global-note">
            Some long details were shortened to keep the Defense context and Report focused. The
            saved project record itself was not changed.
          </p>
        )}
        {context.content_redacted && (
          <p className="report-global-note">
            Sensitive-looking values were removed from this Report view; the workflow source
            states above remain unchanged.
          </p>
        )}
      </section>

      <section className="report-section" aria-labelledby="report-change-map-heading">
        <div className="report-section-heading">
          <div>
            <p className="report-kicker">Source 01</p>
            <h2 id="report-change-map-heading">Change Map</h2>
          </div>
          <SourceState state={context.change_map.state} truncated={context.change_map.truncated} />
        </div>
        {sourceHasReportContent("change_map", context) ? (
          <ol className="report-item-list">
            {context.change_map.items.map((item, index) => (
              <li
                className={`report-item${item.student_decision === "rejected" ? " rejected" : ""}`}
                key={`${item.category}-${index}`}
              >
                <div className="report-item-heading">
                  <strong>{changeMapProvenanceLabel(item.origin, item.student_decision)}</strong>
                  <span className="pill">{reportCategoryLabel(item.category)}</span>
                </div>
                <p className="report-plain-text">{item.text}</p>
                <dl className="report-details">
                  <Detail label="Uncertainty" value={item.uncertainty_reason} />
                  <Detail label="Student note" value={item.student_note} />
                </dl>
              </li>
            ))}
          </ol>
        ) : (
          <EmptySource state={context.change_map.state} />
        )}
      </section>

      <section className="report-section" aria-labelledby="report-review-heading">
        <div className="report-section-heading">
          <div>
            <p className="report-kicker">Source 02</p>
            <h2 id="report-review-heading">Review</h2>
          </div>
          <SourceState state={context.review.state} truncated={context.review.truncated} />
        </div>
        {sourceHasReportContent("review", context) ? (
          <div className="report-item-list">
            {context.review.items.map((item, index) => {
              const decision = reviewDecisionPresentation(item.review_decision);
              return (
                <div className="report-item" key={`${item.category}-${index}`}>
                  <div className="report-item-heading">
                    <strong>{decision.label}</strong>
                    <span className="pill">{reportCategoryLabel(item.category)}</span>
                  </div>
                  <p className="report-plain-text">{item.reviewed_text}</p>
                  <p className="muted">{decision.description}</p>
                  <dl className="report-details">
                    <Detail label="Student rationale" value={item.student_rationale} />
                    <Detail label="Student revision" value={item.student_revision} />
                  </dl>
                </div>
              );
            })}
            {context.review.manual && <ManualReview manual={context.review.manual} />}
          </div>
        ) : (
          <EmptySource state={context.review.state} />
        )}
      </section>

      <section className="report-section" aria-labelledby="report-verification-heading">
        <div className="report-section-heading">
          <div>
            <p className="report-kicker">Source 03</p>
            <h2 id="report-verification-heading">Verification</h2>
          </div>
          <SourceState state={context.verification.state} truncated={context.verification.truncated} />
        </div>
        <p className="report-section-intro">
          These are student-recorded results. A passed result is not independent proof.
        </p>
        {sourceHasReportContent("verification", context) ? (
          <div className="report-item-list">
            {context.verification.checks.map((check, index) => {
              const result = verificationResultPresentation(check.result);
              return (
                <div className="report-item" key={`${check.check}-${index}`}>
                  <div className="report-item-heading">
                    <strong>{check.check}</strong>
                    <span
                      className={`pill ${
                        check.result === "pass"
                          ? "ok"
                          : check.result === "fail"
                            ? "danger"
                            : check.result === "unrecorded"
                              ? ""
                              : "warn"
                      }`}
                    >
                      {result.label}
                    </span>
                  </div>
                  <p className="muted">{result.description}</p>
                  <dl className="report-details">
                    <Detail label="What happened" value={check.result_notes} />
                  </dl>
                </div>
              );
            })}
            {context.verification.student_explanation && (
              <div className="report-item">
                <strong>Student explanation</strong>
                <p className="report-plain-text">{context.verification.student_explanation}</p>
              </div>
            )}
          </div>
        ) : (
          <EmptySource state={context.verification.state} />
        )}
      </section>

      <section className="report-section" aria-labelledby="report-evidence-heading">
        <div className="report-section-heading">
          <div>
            <p className="report-kicker">Source 04</p>
            <h2 id="report-evidence-heading">Evidence</h2>
          </div>
          <SourceState state={context.evidence.state} truncated={context.evidence.truncated} />
        </div>
        <p className="report-section-intro">
          Verification context, student-provided Evidence, and student explanations remain
          separate below. Evidence is not independent proof.
        </p>
        {sourceHasReportContent("evidence", context) ? (
          <div className="report-item-list">
            {context.evidence.records.map((record, index) => {
              const evidence = evidenceStatusPresentation(record.evidence_status);
              const result = verificationResultPresentation(record.verification_result);
              return (
                <div className="report-item" key={`${record.check_context}-${index}`}>
                  <div className="report-item-heading">
                    <strong>{reportCategoryLabel(record.category)}</strong>
                    <span
                      className={`pill ${
                        record.evidence_status === "evidence_recorded"
                          ? "accent"
                          : record.evidence_status === "evidence_unavailable"
                            ? "warn"
                            : ""
                      }`}
                    >
                      {evidence.label}
                    </span>
                  </div>
                  <div className="report-verification-context">
                    <span className="report-kicker">Verification context — not Evidence</span>
                    <p>{record.check_context}</p>
                    <dl className="report-details">
                      <Detail label="Recorded result" value={result.label} />
                      <Detail label="Result notes" value={record.verification_notes} />
                    </dl>
                  </div>
                  {record.stale_support_omitted ? (
                    <div className="notice info">
                      <strong>Evidence needs updating</strong>
                      <p>
                        This Evidence record was created from an older Verification state and was
                        not used as current supporting Evidence.
                      </p>
                    </div>
                  ) : (
                    <>
                      {record.entries.length > 0 && (
                        <div className="report-evidence-block">
                          <h3>Student-provided Evidence</h3>
                          <ul className="report-evidence-list">
                            {record.entries.map((entry, entryIndex) => (
                              <EvidenceEntryView entry={entry} key={`${entry.kind}-${entryIndex}`} />
                            ))}
                          </ul>
                        </div>
                      )}
                      {record.student_explanation && (
                        <div className="report-student-explanation">
                          <h3>What the student said this Evidence shows</h3>
                          <p className="report-plain-text">{record.student_explanation}</p>
                        </div>
                      )}
                      {record.evidence_status === "evidence_unavailable" && (
                        <div className="report-unavailable">
                          <h3>Evidence unavailable</h3>
                          <p className="report-plain-text">{record.unavailable_reason}</p>
                          <p className="muted">
                            This explanation is part of the project record, but it is not Evidence.
                          </p>
                        </div>
                      )}
                      {record.evidence_status === "not_addressed" && (
                        <p className="empty">Evidence not addressed.</p>
                      )}
                    </>
                  )}
                </div>
              );
            })}
            {(context.evidence.manual_entries.length > 0 || context.evidence.manual_summary) && (
              <div className="report-item">
                <div className="report-item-heading">
                  <strong>Earlier manual Evidence record</strong>
                  <span className="pill">Manual record</span>
                </div>
                <p className="muted">
                  This record has no linked Verification provenance. It remains student-provided
                  Evidence, not independent proof.
                </p>
                <ul className="report-evidence-list">
                  {context.evidence.manual_entries.map((entry, index) => (
                    <EvidenceEntryView entry={entry} key={`${entry.kind}-${index}`} />
                  ))}
                </ul>
                {context.evidence.manual_summary && (
                  <div className="report-student-explanation">
                    <h3>Student summary</h3>
                    <p className="report-plain-text">{context.evidence.manual_summary}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <EmptySource state={context.evidence.state} />
        )}
      </section>

      <section className="report-section" aria-labelledby="report-defense-heading">
        <div className="report-section-heading">
          <div>
            <p className="report-kicker">Student explanation</p>
            <h2 id="report-defense-heading">Project Defense</h2>
          </div>
          <span className={`pill ${defenseOutcomeTone(report.defense.state)}`}>
            {defenseOutcomeLabel(report.defense.state)}
          </span>
        </div>
        {report.defense.turns.length ? (
          <ol className="report-transcript">
            {report.defense.turns.map((turn) => (
              <li key={turn.turn}>
                <div className="report-transcript-part">
                  <span className="report-kicker">Question {turn.turn}</span>
                  <p>{turn.question}</p>
                </div>
                <div className="report-transcript-part response">
                  <span className="report-kicker">Your response</span>
                  <p>{turn.answer ?? "No response was recorded."}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty">No student-safe Defense transcript is available.</p>
        )}
      </section>

      <section className="report-outcome" aria-labelledby="report-final-outcome-heading">
        <p className="report-kicker">Evaluator outcome</p>
        <h2 id="report-final-outcome-heading">{defenseOutcomeLabel(report.defense.state)}</h2>
        <p>
          {report.defense.evaluator_outcome === "PASS"
            ? "You completed Project Defense under Codize’s current evaluation criteria."
            : "This attempt did not pass. The outcome applies to this Defense attempt, not to every part of the project."}
        </p>
        {report.defense.evaluator_reason && (
          <dl className="report-details">
            <Detail label="Recorded evaluator feedback" value={report.defense.evaluator_reason} />
          </dl>
        )}
      </section>
    </article>
  );
}
