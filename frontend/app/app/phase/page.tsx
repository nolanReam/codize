"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import WorkflowSteps from "@/components/WorkflowSteps";
import { ApiError, getCurrentPhase, getPhases, getWorkflow, setTaskCompletion } from "@/lib/api";
import type { PhaseList, PhaseView, TaskEntry, WorkflowSections } from "@/lib/types";

// The Phase Workspace, framed around the Build Loop — the tasks are the
// phase's raw material; the loop is how you work through them with AI.
export default function PhaseBoardPage() {
  const [phase, setPhase] = useState<PhaseView | null>(null);
  const [phases, setPhases] = useState<PhaseList | null>(null);
  const [sections, setSections] = useState<WorkflowSections | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notReady, setNotReady] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotReady(false);
    try {
      const current = await getCurrentPhase();
      setPhase(current);
      const [list, workflow] = await Promise.allSettled([getPhases(), getWorkflow(current.phase)]);
      if (list.status === "fulfilled") setPhases(list.value);
      if (workflow.status === "fulfilled") setSections(workflow.value.sections);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) setNotReady(true);
      else setError(err instanceof ApiError ? err.message : "Couldn't load the phase workspace.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleTask(task: TaskEntry) {
    if (!phase) return;
    setTaskError(null);
    try {
      setPhase(await setTaskCompletion(phase.phase, task.task_id, !task.completed));
    } catch (err) {
      setTaskError(err instanceof ApiError ? err.message : "Couldn't update that task.");
    }
  }

  if (notReady) {
    return (
      <>
        <h1 className="page-title">Phase Workspace</h1>
        <div className="notice info">
          No active roadmap yet. Finish intake and generate your roadmap first.
        </div>
        <Link href="/app/intake" className="btn primary">
          Go to intake
        </Link>
      </>
    );
  }

  return (
    <Async loading={loading} error={error} onRetry={load}>
      {phase && (
        <>
          <div className="spread">
            <div>
              <h1 className="page-title">
                Phase {phase.phase}: {phase.phase_title}
              </h1>
              <p className="page-sub">{phase.core_concept}</p>
            </div>
            <span className="pill accent">
              {phase.completed_task_count}/{phase.total_task_count} tasks
            </span>
          </div>

          <div className="card">
            <h3>The Build Loop — how to work this phase</h3>
            <WorkflowSteps sections={sections} />
            <p className="muted">
              Plan and prompt in Codize, generate in your AI tool, then come back to review what
              changed, capture evidence, verify behavior, and defend it at the gate.
            </p>
          </div>

          <div className="card-grid" style={{ marginTop: 14 }}>
            <div className="card">
              <h3>AI-appropriate tasks</h3>
              <p className="muted" style={{ marginBottom: 8 }}>
                Fine to delegate — but review what comes back (that&rsquo;s the Review step).
              </p>
              {phase.ai_appropriate_tasks.map((t) => (
                <label className="task" key={t.task_id}>
                  <input type="checkbox" checked={t.completed} onChange={() => toggleTask(t)} />
                  <span className={t.completed ? "done" : ""}>
                    <span className="tag">AI</span>
                    {t.description}
                  </span>
                </label>
              ))}
            </div>
            <div className="card">
              <h3>Human-required tasks</h3>
              <p className="muted" style={{ marginBottom: 8 }}>
                These are yours. Delegating them is how the 80% Trap starts.
              </p>
              {phase.human_required_tasks.map((t) => (
                <label className="task" key={t.task_id}>
                  <input type="checkbox" checked={t.completed} onChange={() => toggleTask(t)} />
                  <span className={t.completed ? "done" : ""}>
                    <span className="tag">YOU</span>
                    {t.description}
                  </span>
                </label>
              ))}
            </div>
          </div>
          {taskError && <div className="notice error">{taskError}</div>}
          <p className="muted" style={{ marginTop: 8 }}>
            Ticking tasks never advances the phase — only passing the Interrogation Gate does.
          </p>

          <div className="card" style={{ marginTop: 14 }}>
            <h3>This phase&rsquo;s gate</h3>
            <div className="kv">
              <span className="k">You&rsquo;ll defend</span>
              <span>{phase.explanation_gate_targets.join(" · ")}</span>
            </div>
            <div className="kv">
              <span className="k">To advance</span>
              <span>{phase.unlock_condition}</span>
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <Link href="/app/gate" className="btn">
                Gate status
              </Link>
            </div>
          </div>

          {phases && (
            <div className="card" style={{ marginTop: 14 }}>
              <h3>Roadmap</h3>
              {phases.phases.map((p) => (
                <div className="kv" key={p.phase}>
                  <span className="k mono">
                    {p.is_current ? "▶" : p.phase < phases.current_phase ? "✓" : "·"} Phase{" "}
                    {p.phase}
                  </span>
                  <span className={p.is_current ? "" : "muted"}>
                    {p.phase_title}{" "}
                    <span className="muted">
                      ({p.completed_task_count}/{p.total_task_count})
                    </span>
                  </span>
                </div>
              ))}
              <p className="muted" style={{ marginTop: 8 }}>
                Later phases open by passing gates, in order.
              </p>
            </div>
          )}
        </>
      )}
    </Async>
  );
}
