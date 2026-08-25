"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { getHistory } from "@/lib/v2-api";
import type { CheckResult, HistoryChangeView, HistoryResponse } from "@/lib/v2-types";

const PAGE_SIZE = 10;
const statusLabels: Record<HistoryChangeView["status"], string> = {
  active: "Active", recovering: "Recovering", completed: "Completed",
  completed_after_recovery: "Completed after recovery", cancelled: "Cancelled",
};
const resultLabels: Record<CheckResult, string> = {
  worked: "PASS", partly_worked: "PARTLY WORKED", did_not_work: "FAIL", unsure: "UNSURE",
};
const relationshipLabels: Record<HistoryChangeView["checks"][number]["relationship"], string> = {
  initial: "Initial check", retry_after_unsure: "Retry after unsure", follow_up: "Follow-up check",
};
const dateTime = (value: string) => new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium", timeStyle: "short",
}).format(new Date(value));

export default function HistoryPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try { setData(await getHistory(id, PAGE_SIZE, 0)); }
    catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Couldn't load this project history.");
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  const loadOlder = async () => {
    if (!data?.has_more || data.next_offset === null) return;
    setBusy(true); setError(null);
    try {
      const older = await getHistory(id, PAGE_SIZE, data.next_offset);
      setData({
        ...older, changes: [...data.changes, ...older.changes],
        transfer_question: data.transfer_question ?? older.transfer_question,
      });
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Couldn't load older changes.");
    } finally { setBusy(false); }
  };

  if (!data && !error) {
    return <div className="v2-page"><V2Card><V2Skeleton lines={7} /></V2Card></div>;
  }

  return (
    <div className="v2-page v2-reflection-page">
      {error && (
        <V2Notice tone="error">
          {error} <button type="button" className="v2-inline-button" onClick={() => void load()}>Refresh</button>
        </V2Notice>
      )}
      {data && (
        <>
          <header className="v2-page-header">
            <p className="v2-eyebrow">History</p>
            <h1>What happened in this project</h1>
            <p>A readable record of what you intended, handed off, checked, recovered from, and completed.</p>
          </header>
          {data.changes.length === 0 ? (
            <V2Card className="v2-reflection-empty">
              <span className="v2-empty-mark" aria-hidden="true" />
              <h2>Your project history will show up here after your first change.</h2>
              <p>Changes, Checks, and Recovery steps will become a truthful timeline. Codize will not invent what code changed.</p>
              <Link className="v2-button v2-button-primary" href={`/app/project/${id}/build`}>Start building</Link>
            </V2Card>
          ) : (
            <>
              <ol className="v2-history-list">
                {data.changes.map((change) => (
                  <li key={change.id}>
                    <article className="v2-history-card">
                      <header>
                        <div><h2>{change.goal}</h2><p>{change.completion_summary}</p></div>
                        <span className={`v2-status v2-history-status-${change.status}`}>{statusLabels[change.status]}</span>
                      </header>
                      <dl className="v2-history-intent">
                        <div><dt>Started</dt><dd>{dateTime(change.started_at)}</dd></div>
                        {change.completed_at && <div><dt>Completed</dt><dd>{dateTime(change.completed_at)}</dd></div>}
                        {change.cancelled_at && <div><dt>Cancelled</dt><dd>{dateTime(change.cancelled_at)}</dd></div>}
                        {change.done_condition && <div><dt>Done meant</dt><dd>{change.done_condition}</dd></div>}
                      </dl>
                      {change.checks.length > 0 && (
                        <section className="v2-history-section" aria-labelledby={`checks-${change.id}`}>
                          <h3 id={`checks-${change.id}`}>Checks</h3>
                          <ol className="v2-check-history">
                            {change.checks.map((check) => (
                              <li key={check.sequence}>
                                <span className={`v2-check-result v2-check-result-${check.result ?? "pending"}`}>
                                  {check.result ? resultLabels[check.result] : check.status === "not_run" ? "NOT RUN" : "PROPOSED"}
                                </span>
                                <div>
                                  <span className="v2-check-relationship">
                                    Check {check.sequence} · {relationshipLabels[check.relationship]}
                                    {check.supersedes_sequence ? ` to Check ${check.supersedes_sequence}` : ""}
                                  </span>
                                  <strong>{check.check_plan}</strong>
                                  <small>
                                    {check.plan_source === "student" ? "Proposed by you" : "Suggested by Codize"}
                                    {` · created ${dateTime(check.created_at)}`}
                                    {check.performed_at ? ` · performed ${dateTime(check.performed_at)}` : ""}
                                    {check.not_run_at ? ` · closed without running ${dateTime(check.not_run_at)}` : ""}
                                  </small>
                                  {check.student_observation && <blockquote>{check.student_observation}</blockquote>}
                                </div>
                              </li>
                            ))}
                          </ol>
                          {change.checks_truncated && <p className="v2-bounds-note">Only the first 50 Checks are shown.</p>}
                        </section>
                      )}
                      {change.recoveries.length > 0 && (
                        <section className="v2-history-section v2-history-recovery" aria-labelledby={`recovery-${change.id}`}>
                          <h3 id={`recovery-${change.id}`}>Recovery history</h3>
                          <div className="v2-recovery-episodes">
                            {change.recoveries.map((recovery) => (
                              <article className="v2-recovery-episode" key={recovery.episode_number}>
                                <header>
                                  <strong>Recovery attempt {recovery.episode_number}</strong>
                                  <span>{recovery.status.replaceAll("_", " ")}</span>
                                </header>
                                <ol>
                                  <li><strong>Observe</strong><span>You reported: {recovery.observed_symptom}</span></li>
                                  {recovery.investigation_finding && <li><strong>Investigate</strong><span>Coding agent suggested: {recovery.investigation_finding}</span></li>}
                                  {recovery.correction_summary && <li><strong>Correct</strong><span>A targeted correction was prepared: {recovery.correction_summary}</span></li>}
                                  {recovery.recheck_state && (
                                    <li><strong>Recheck</strong><span>
                                      {recovery.recheck_state === "pending"
                                        ? "A student recheck is ready, but no result is stored yet."
                                        : recovery.resolution_summary ?? "The Recovery case was resolved after a student recheck."}
                                    </span></li>
                                  )}
                                </ol>
                              </article>
                            ))}
                          </div>
                          {change.recoveries_truncated && <p className="v2-bounds-note">Only the first 10 Recovery attempts are shown.</p>}
                        </section>
                      )}
                      {change.prompts.length > 0 && (
                        <details className="v2-prompt-history">
                          <summary>Accepted prompts ({change.prompts.length}{change.prompts_truncated ? "+" : ""})</summary>
                          <ol>
                            {change.prompts.map((prompt) => (
                              <li key={prompt.id}>
                                <p><strong>#{prompt.ordinal} · {prompt.purpose === "feature" ? "Build" : prompt.purpose === "diagnostic" ? "Recovery investigation" : "Recovery correction"}</strong></p>
                                <small>
                                  {prompt.coding_agent_key.replaceAll("_", " ")} · {prompt.effort_category ?? "No effort stored"} · accepted {dateTime(prompt.accepted_at)}
                                  {prompt.handed_off_at ? ` · handed off ${dateTime(prompt.handed_off_at)}` : ""}
                                </small>
                                <pre>{prompt.content}</pre>
                              </li>
                            ))}
                          </ol>
                          {change.prompts_truncated && <p className="v2-bounds-note">Only the first 20 accepted prompts are shown.</p>}
                        </details>
                      )}
                    </article>
                  </li>
                ))}
              </ol>
              {data.has_more && (
                <button type="button" className="v2-button v2-button-secondary v2-load-older" onClick={() => void loadOlder()} disabled={busy}>
                  {busy ? "Loading…" : "Load older changes"}
                </button>
              )}
              <div className="v2-project-origin">
                <span aria-hidden="true" />
                <p><strong>{data.project_name} started</strong><small>{dateTime(data.project_created_at)}</small></p>
              </div>
              {data.transfer_question && (
                <aside className="v2-transfer-question" aria-labelledby="transfer-question-heading">
                  <p className="v2-card-label">Optional beta reflection</p>
                  <h2 id="transfer-question-heading">{data.transfer_question}</h2>
                  <p>Your answer is not saved yet. This is a reflection seam, not learner evidence.</p>
                </aside>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
