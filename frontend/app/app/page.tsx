"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import WorkflowSteps from "@/components/WorkflowSteps";
import { ApiError, getEvaluation, getIntakeStatus, getWorkflow } from "@/lib/api";
import type { Evaluation, WorkflowSections } from "@/lib/types";

const STATE_PILL: Record<string, { label: string; cls: string }> = {
  in_progress: { label: "IN PROGRESS", cls: "accent" },
  gate_ready: { label: "GATE READY", cls: "warn" },
  cooldown: { label: "GATE COOLDOWN", cls: "danger" },
  complete: { label: "ROADMAP COMPLETE", cls: "ok" },
};

function sectionPill(present: boolean) {
  return <span className={`pill ${present ? "ok" : ""}`}>{present ? "saved" : "not started"}</span>;
}

// The Project Cockpit — the dashboard for your (currently one) project. A
// brand-new user never lands here: the spec routes signup straight into
// intake question 1, so this page always has a project to show.
export default function CockpitPage() {
  const router = useRouter();
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [sections, setSections] = useState<WorkflowSections | null>(null);
  const [purpose, setPurpose] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const ev = await getEvaluation();
      // Spec: a new user goes straight to intake question 1 — no dashboard.
      if (ev.state === "not_started" || ev.state === "intake_needed" || ev.state === "roadmap_needed") {
        router.replace("/app/intake");
        return;
      }
      setEvaluation(ev);
      const [workflow, intake] = await Promise.allSettled([
        getWorkflow(ev.current_phase ?? 1),
        getIntakeStatus(),
      ]);
      if (workflow.status === "fulfilled") setSections(workflow.value.sections);
      if (intake.status === "fulfilled") setPurpose(intake.value.answers?.purpose ?? null);
      setLoading(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your workspace.");
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const pill = evaluation ? STATE_PILL[evaluation.state] : undefined;
  const savedCount = sections
    ? Object.values(sections).filter((s) => s != null).length
    : 0;

  return (
    <>
      <div className="spread">
        <div>
          <h1 className="page-title">Project Cockpit</h1>
          <p className="page-sub">Your project at a glance — where you are, and what to do next.</p>
        </div>
        <div className="row">
          {pill && <span className={`pill ${pill.cls}`}>{pill.label}</span>}
          <button
            className="btn small"
            disabled
            title="One project per account for now — multi-project support is planned."
          >
            + New project
          </button>
        </div>
      </div>

      <Async loading={loading} error={error} onRetry={load}>
        {evaluation && (
          <div className="workspace">
            <div>
              <div className="card" style={{ borderColor: "var(--border-strong)" }}>
                <h3>Your project</h3>
                {purpose ? (
                  <p style={{ fontSize: 16, fontWeight: 600 }}>&ldquo;{purpose}&rdquo;</p>
                ) : (
                  <p className="empty">Your intake purpose will appear here.</p>
                )}
                <div className="kv" style={{ marginTop: 10 }}>
                  <span className="k">Phase</span>
                  <span>
                    {evaluation.current_phase} of {evaluation.total_phases} —{" "}
                    {evaluation.phase_title}
                  </span>
                </div>
                <div className="kv">
                  <span className="k">Phases passed</span>
                  <span>{evaluation.completed_phases}</span>
                </div>
                <div className="kv">
                  <span className="k">Phase tasks</span>
                  <span>
                    {evaluation.completed_task_count} / {evaluation.total_task_count} done
                  </span>
                </div>
                <div className="row" style={{ marginTop: 14 }}>
                  <Link href="/app/phase" className="btn primary">
                    Continue project
                  </Link>
                  {(evaluation.state === "gate_ready" || evaluation.state === "cooldown") && (
                    <Link href="/app/gate" className="btn">
                      Project Defense
                    </Link>
                  )}
                </div>
              </div>

              <div className="card" style={{ marginTop: 14 }}>
                <h3>Next action</h3>
                <p style={{ fontSize: 16 }}>{evaluation.next_action}</p>
              </div>

              <div className="card-grid" style={{ marginTop: 14 }}>
                <div className="card">
                  <h3>Gate</h3>
                  {evaluation.recent_gate ? (
                    <>
                      <div className="kv">
                        <span className="k">Latest</span>
                        <span className={`pill ${
                          evaluation.recent_gate.outcome === "passed"
                            ? "ok"
                            : evaluation.recent_gate.outcome === "failed"
                              ? "danger"
                              : "warn"
                        }`}>
                          {evaluation.recent_gate.outcome}
                        </span>
                      </div>
                      {evaluation.recent_gate.summary && (
                        <p className="muted" style={{ marginTop: 8 }}>
                          {evaluation.recent_gate.summary}
                        </p>
                      )}
                      {evaluation.state === "cooldown" &&
                        evaluation.cooldown_seconds_remaining != null && (
                          <p className="muted" style={{ marginTop: 8 }}>
                            Retry available in ~
                            {Math.ceil(evaluation.cooldown_seconds_remaining / 60)} min.
                          </p>
                        )}
                    </>
                  ) : (
                    <p className="empty">No gate attempts on this phase yet.</p>
                  )}
                </div>

                <div className="card">
                  <h3>Unlocks</h3>
                  {evaluation.unlocks && evaluation.unlocks.length > 0 ? (
                    evaluation.unlocks.map((u) => (
                      <div className="kv" key={u.id}>
                        <span className="k">Phase {u.phase}</span>
                        <span>{u.description}</span>
                      </div>
                    ))
                  ) : (
                    <p className="empty">Nothing unlocked yet. Keep building well.</p>
                  )}
                </div>
              </div>

              <div className="card" style={{ marginTop: 14 }}>
                <h3>Build Loop — Phase {evaluation.current_phase}</h3>
                <WorkflowSteps sections={sections} />
                <div className="row">
                  <span className="muted">Prompt Builder</span>
                  {sectionPill(sections?.prompt_builder != null)}
                  <span className="muted">Review Board</span>
                  {sectionPill(sections?.review_board != null)}
                  <span className="muted">Evidence</span>
                  {sectionPill(sections?.evidence != null)}
                  <span className="muted">Verification</span>
                  {sectionPill(sections?.verification != null)}
                </div>
              </div>

              <div className="card" style={{ marginTop: 14 }}>
                <h3>Project Defense Report</h3>
                <p className="muted">
                  {savedCount} of 4 workflow artifacts captured for this phase. Your report
                  assembles from your intake, phases, artifacts, gate outcome, and unlocks — and
                  you can copy or download it as Markdown for a demo or interview.
                </p>
                <div className="row" style={{ marginTop: 12 }}>
                  <Link href="/app/report" className="btn">
                    Open Defense Report
                  </Link>
                  <Link href="/app/gate" className="btn">
                    Project Defense
                  </Link>
                </div>
              </div>
            </div>

            <aside className="ws-rail" aria-label="Guidance">
              <GuideCard title="Feeling lost?">
                <p>
                  That&rsquo;s normal on day one. Open <strong>How Codize works</strong> in the
                  sidebar for the whole loop in nine short steps.
                </p>
                <p>
                  The short version: <strong>Continue project</strong> takes you to your current
                  phase. Everything else follows from there.
                </p>
              </GuideCard>
              <GuideCard title="What these words mean">
                <details className="help">
                  <summary>Phase</summary>
                  <div className="help-body">
                    <p>
                      One slice of your project (like &ldquo;login&rdquo; or &ldquo;database&rdquo;).
                      Your roadmap is a fixed sequence of phases; you&rsquo;re always working
                      exactly one.
                    </p>
                  </div>
                </details>
                <details className="help">
                  <summary>Build Loop</summary>
                  <div className="help-body">
                    <p>
                      The work rhythm inside each phase: plan your AI prompt → generate in your
                      AI tool → review what changed → collect evidence → verify it works →
                      defend it.
                    </p>
                  </div>
                </details>
                <details className="help">
                  <summary>Artifact</summary>
                  <div className="help-body">
                    <p>
                      Anything you save in Codize along the way — your prompt, your review notes,
                      your evidence, your verification results. They become your Defense Report.
                    </p>
                  </div>
                </details>
                <details className="help">
                  <summary>Project Defense (the gate)</summary>
                  <div className="help-body">
                    <p>
                      A short conversation at the end of each phase where you explain what you
                      built in your own words. Passing it opens the next phase. It&rsquo;s not a
                      quiz on textbook facts — it&rsquo;s about <em>your</em> project.
                    </p>
                  </div>
                </details>
                <details className="help">
                  <summary>Unlock</summary>
                  <div className="help-body">
                    <p>
                      A bonus (like a pre-built component) Codize grants when you&rsquo;re building
                      consistently well. You can&rsquo;t grind for them — just keep understanding
                      what you ship.
                    </p>
                  </div>
                </details>
              </GuideCard>
              <GuideCard title="More projects?">
                <p>
                  Codize supports one project per account right now, so you can finish what you
                  started. Multi-project support is planned.
                </p>
              </GuideCard>
            </aside>
          </div>
        )}
      </Async>
    </>
  );
}
