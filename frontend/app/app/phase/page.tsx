"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import WorkflowSteps from "@/components/WorkflowSteps";
import { ApiError, getCurrentPhase, getPhases, getWorkflow, setTaskCompletion } from "@/lib/api";
import { phaseGuide } from "@/lib/phaseGuide";
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
          Your project isn&rsquo;t set up yet — answer the five intake questions and Codize builds
          your roadmap.
        </div>
        <Link href="/app/intake" className="btn primary">
          Start with intake
        </Link>
      </>
    );
  }

  const capturedCount = sections
    ? Object.values(sections).filter((s) => s != null).length
    : 0;

  // The one obvious next step: the first workflow artifact not yet captured,
  // or the gate once all four are in. Order mirrors the Build Loop.
  const WORKFLOW_ORDER: {
    key: keyof WorkflowSections;
    label: string;
    href: string;
    hint: string;
  }[] = [
    {
      key: "prompt_builder",
      label: "Plan your prompt",
      href: "/app/phase/prompt",
      hint: "Turn this phase into one clear ask for your AI tool.",
    },
    {
      key: "review_board",
      label: "Review what the AI did",
      href: "/app/phase/review",
      hint: "Back from your AI tool? Note what it changed before building on it.",
    },
    {
      key: "evidence",
      label: "Save one piece of proof",
      href: "/app/phase/evidence",
      hint: "A test output, a screenshot note, a commit — one is enough.",
    },
    {
      key: "verification",
      label: "Run a quick check",
      href: "/app/phase/verify",
      hint: "Mark what you actually checked. Skipped is allowed.",
    },
  ];
  const nextStep = sections
    ? WORKFLOW_ORDER.find((s) => sections[s.key] == null) ?? null
    : WORKFLOW_ORDER[0];

  return (
    <Async loading={loading} error={error} onRetry={load}>
      {phase && (
        <>
          <div className="spread">
            <div>
              <h1 className="page-title">
                Phase {phase.phase}: {phase.phase_title}
              </h1>
              <p className="page-sub" style={{ marginBottom: 10 }}>{phase.core_concept}</p>
              <details className="help" style={{ maxWidth: 640 }}>
                <summary>What does this phase mean in plain words?</summary>
                <div className="help-body">
                  <p>{phaseGuide(phase.phase_title).meaning}</p>
                  <p>
                    The Prompt Builder has tap-to-use starter asks for exactly this phase — you
                    don&rsquo;t need to figure out what to ask AI on your own.
                  </p>
                </div>
              </details>
            </div>
            <div className="row">
              <span className="pill accent">
                Build tasks: {phase.completed_task_count}/{phase.total_task_count}
              </span>
              <span className={`pill ${capturedCount === 4 ? "ok" : ""}`}>
                Workflow: {capturedCount}/4 captured
              </span>
            </div>
          </div>

          <div className="workspace">
            <div>
              {/* The one obvious next step for this phase. */}
              <div className="card" style={{ borderColor: "var(--accent)" }}>
                <h3>Next step</h3>
                {nextStep ? (
                  <>
                    <p style={{ fontSize: 16, fontWeight: 600 }}>{nextStep.label}</p>
                    <p className="muted" style={{ marginTop: 4 }}>{nextStep.hint}</p>
                    <div className="row" style={{ marginTop: 12 }}>
                      <Link href={nextStep.href} className="btn primary">
                        {nextStep.label} →
                      </Link>
                    </div>
                  </>
                ) : (
                  <>
                    <p style={{ fontSize: 16, fontWeight: 600 }}>
                      All four artifacts captured — defend this phase.
                    </p>
                    <div className="row" style={{ marginTop: 12 }}>
                      <Link href="/app/gate" className="btn primary">
                        Start the defense →
                      </Link>
                    </div>
                  </>
                )}
                <div style={{ marginTop: 12 }}>
                  <WorkflowSteps sections={sections} />
                </div>
              </div>

              <div className="card-grid" style={{ marginTop: 14 }}>
                <div className="card">
                  <h3>AI-appropriate tasks</h3>
                  <p className="muted" style={{ marginBottom: 8 }}>
                    Fine to hand to your AI tool.
                  </p>
                  {phase.ai_appropriate_tasks.map((t) => (
                    <label className="task" key={t.task_id}>
                      <input
                        type="checkbox"
                        checked={t.completed}
                        onChange={() => toggleTask(t)}
                      />
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
                    These are yours.
                  </p>
                  {phase.human_required_tasks.map((t) => (
                    <label className="task" key={t.task_id}>
                      <input
                        type="checkbox"
                        checked={t.completed}
                        onChange={() => toggleTask(t)}
                      />
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
                Tick these yourself as you finish building. Only the gate advances the phase.
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
            </div>

            <aside className="ws-rail" aria-label="Progress and roadmap">
              <GuideCard title="Two kinds of progress">
                <p>
                  <strong>Build tasks</strong> ({phase.completed_task_count}/
                  {phase.total_task_count}) = the actual building — the checkboxes, ticked by
                  you.
                </p>
                <p>
                  <strong>Workflow</strong> ({capturedCount}/4) = what you&rsquo;ve captured in
                  Codize about that work. Doing one doesn&rsquo;t tick the other.
                </p>
              </GuideCard>
              {phases && (
                <div className="card">
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
            </aside>
          </div>
        </>
      )}
    </Async>
  );
}
