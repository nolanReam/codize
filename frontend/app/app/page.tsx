"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import Async from "@/components/Async";
import { GuidedContinueAction } from "@/components/GuidedProjectNav";
import { useGuidedProjectNavigation } from "@/components/GuidedProjectNavigationProvider";
import GuideCard from "@/components/GuideCard";
import LoopOverview from "@/components/LoopOverview";
import WorkflowSteps from "@/components/WorkflowSteps";

// `/app` remains the stable route while the visible student-facing name is
// Project Home. The one-project selection contract and disabled new-project
// action are unchanged.
export default function ProjectHomePage() {
  const router = useRouter();
  const { state, error, navigation, evaluation, workflow, refresh } =
    useGuidedProjectNavigation();

  useEffect(() => {
    if (
      state === "ready" &&
      evaluation &&
      (evaluation.state === "not_started" ||
        evaluation.state === "intake_needed" ||
        evaluation.state === "roadmap_needed")
    ) {
      router.replace("/app/intake");
    }
  }, [evaluation, router, state]);

  const pill = state === "ready" && evaluation
    ? evaluation.state === "complete" || navigation.continueAction.stageId === "report"
      ? { label: "ROADMAP COMPLETE", cls: "ok" }
      : evaluation.state === "cooldown"
        ? { label: "DEFENSE COOLDOWN", cls: "warn" }
        : navigation.continueAction.stageId === "defense"
          ? {
              label: navigation.continueAction.label.startsWith("Continue")
                ? "DEFENSE ACTIVE"
                : navigation.continueAction.label.startsWith("Try")
                  ? "DEFENSE RETRY"
                  : "DEFENSE READY",
              cls: "warn",
            }
          : { label: "IN PROGRESS", cls: "accent" }
    : undefined;
  const savedCount = workflow
    ? Object.values(workflow.sections).filter((section) => section != null).length
    : 0;

  return (
    <>
      <div className="spread">
        <div>
          <h1 className="page-title">Project Home</h1>
          <p className="page-sub">Your project, current step, and saved record.</p>
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

      <Async
        loading={state === "loading"}
        error={state === "error" ? error ?? "Project progress is temporarily unavailable." : null}
        onRetry={refresh}
      >
        {evaluation && workflow && (
          <div className="workspace">
            <div>
              <div className="card primary">
                <h3>Continue</h3>
                <p style={{ fontSize: 17, fontWeight: 600 }}>
                  {navigation.continueAction.label}
                </p>
                <p className="muted" style={{ marginTop: 4 }}>
                  {navigation.continueAction.reason}
                </p>
                <div className="row" style={{ marginTop: 12 }}>
                  <GuidedContinueAction className="btn primary" />
                </div>
                <LoopOverview />
              </div>

              <div className="card" style={{ marginTop: 14 }}>
                <h3>Active project</h3>
                <p style={{ fontSize: 16, fontWeight: 600, overflowWrap: "anywhere" }}>
                  &ldquo;{navigation.projectLabel}&rdquo;
                </p>
                <div className="kv" style={{ marginTop: 10 }}>
                  <span className="k">Phase</span>
                  <span>
                    {evaluation.current_phase} of {evaluation.total_phases} — {evaluation.phase_title}
                  </span>
                </div>
                <div className="kv">
                  <span className="k">Build tasks</span>
                  <span>
                    {evaluation.completed_task_count} / {evaluation.total_task_count} done
                  </span>
                </div>
                <div className="kv">
                  <span className="k">Workflow</span>
                  <span>{savedCount} / 5 captured this phase</span>
                </div>
                {evaluation.recent_gate && (
                  <div className="kv">
                    <span className="k">Latest Defense</span>
                    <span
                      className={`pill ${
                        evaluation.recent_gate.outcome === "passed"
                          ? "ok"
                          : evaluation.recent_gate.outcome === "failed"
                            ? "danger"
                            : "warn"
                      }`}
                    >
                      {evaluation.recent_gate.outcome}
                    </span>
                  </div>
                )}
              </div>

              <div className="card" style={{ marginTop: 14 }}>
                <h3>Journey — Phase {evaluation.current_phase}</h3>
                <WorkflowSteps />
                <p className="muted">
                  Completed work stays available in Project Record. Complete means saved, not independently verified.
                </p>
              </div>

              {evaluation.unlocks && evaluation.unlocks.length > 0 && (
                <div className="card" style={{ marginTop: 14 }}>
                  <h3>Unlocked</h3>
                  {evaluation.unlocks.map((unlock) => (
                    <div className="kv" key={unlock.id}>
                      <span className="k">Phase {unlock.phase}</span>
                      <span>{unlock.description}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <aside className="ws-rail" aria-label="Guidance">
              <GuideCard title="Project Home">
                <p>
                  Continue follows the earliest saved step that needs work. Opening an older record does not change it.
                </p>
              </GuideCard>
              <GuideCard title="Two kinds of progress">
                <p>
                  Build tasks track the work you perform. Workflow records capture what you planned, reviewed, tested, and recorded.
                </p>
                <p>Only Project Defense advances the roadmap phase.</p>
              </GuideCard>
              <GuideCard title="More projects?">
                <p>
                  Codize supports one project per account right now. The existing project remains selected here.
                </p>
              </GuideCard>
            </aside>
          </div>
        )}
      </Async>
    </>
  );
}
