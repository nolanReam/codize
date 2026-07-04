"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
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
          <p className="page-sub">Where you are, what&rsquo;s proven, and what to do next.</p>
        </div>
        {pill && <span className={`pill ${pill.cls}`}>{pill.label}</span>}
      </div>

      <Async loading={loading} error={error} onRetry={load}>
        {evaluation && (
          <>
            <div className="card">
              <h3>Next action</h3>
              <p style={{ fontSize: 16 }}>{evaluation.next_action}</p>
              <div className="row" style={{ marginTop: 12 }}>
                <Link href="/app/phase" className="btn primary">
                  Open Phase {evaluation.current_phase} workspace
                </Link>
                {(evaluation.state === "gate_ready" || evaluation.state === "cooldown") && (
                  <Link href="/app/gate" className="btn">
                    Project Defense
                  </Link>
                )}
              </div>
            </div>

            <div className="card-grid" style={{ marginTop: 14 }}>
              <div className="card">
                <h3>Mission</h3>
                {purpose ? (
                  <p>&ldquo;{purpose}&rdquo;</p>
                ) : (
                  <p className="empty">Your intake purpose will appear here.</p>
                )}
              </div>

              <div className="card">
                <h3>Position</h3>
                <div className="kv">
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
              </div>

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
                assembles from your intake, phases, artifacts, gate outcome, and unlocks — and you
                can copy or download it as Markdown for a demo or interview.
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
          </>
        )}
      </Async>
    </>
  );
}
