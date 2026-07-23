"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { QuickStartPanel, StartingPathSummary } from "@/components/AdaptiveEntry";
import Async from "@/components/Async";
import { GuidedContinueAction } from "@/components/GuidedProjectNav";
import { useGuidedProjectNavigation } from "@/components/GuidedProjectNavigationProvider";
import GuideCard from "@/components/GuideCard";
import {
  ApiError,
  getCurrentPhase,
  getPhases,
  selectCurrentAssignment,
  setTaskCompletion,
} from "@/lib/api";
import {
  draftKey,
  promptAssignmentDraftSurface,
  readDraft,
} from "@/lib/drafts";
import { phaseGuide } from "@/lib/phaseGuide";
import { assignmentSwitchProtection } from "@/lib/phaseAssignment";
import type { PromptBuilderInputs } from "@/lib/promptBuilder";
import type {
  PhaseAssignmentState,
  PhaseList,
  PhaseView,
  PromptBuilderArtifact,
  TaskEntry,
} from "@/lib/types";

type PhaseLoadState = "idle" | "loading" | "ready" | "error";
type CurrentWorkItem = TaskEntry & { owner: "ai" | "student" };

// `/app` is the sole global orientation dashboard. It owns current phase work;
// the former `/app/phase` route is now only a compatibility redirect.
export default function ProjectHomePage() {
  return (
    <Suspense fallback={<p className="muted" role="status" aria-live="polite">Loading Project Home…</p>}>
      <ProjectHomeContent />
    </Suspense>
  );
}

function ProjectHomeContent() {
  const guided = useGuidedProjectNavigation();
  const { state, error, navigation, evaluation, workflow, entryProfile, assignment, userId, refresh } = guided;
  const searchParams = useSearchParams();
  const showQuickStart = searchParams.get("quick-start") === "1";
  const [phase, setPhase] = useState<PhaseView | null>(null);
  const [phases, setPhases] = useState<PhaseList | null>(null);
  const [phaseState, setPhaseState] = useState<PhaseLoadState>("idle");
  const [phaseError, setPhaseError] = useState<string | null>(null);
  const [roadmapError, setRoadmapError] = useState<string | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskBusy, setTaskBusy] = useState<string | null>(null);
  const restoredAnchorRef = useRef<string | null>(null);
  const currentPhaseNumber = evaluation?.current_phase;

  const loadPhase = useCallback(async () => {
    if (currentPhaseNumber == null) return;
    setPhaseState("loading");
    setPhaseError(null);
    setRoadmapError(null);
    const [currentResult, listResult] = await Promise.allSettled([
      getCurrentPhase(),
      getPhases(),
    ]);
    if (currentResult.status === "rejected") {
      const caught = currentResult.reason;
      setPhaseError(
        caught instanceof ApiError ? caught.message : "Current phase work is temporarily unavailable."
      );
      setPhaseState("error");
      return;
    }
    setPhase(currentResult.value);
    setPhaseState("ready");
    if (listResult.status === "fulfilled") {
      setPhases(listResult.value);
    } else {
      setPhases(null);
      setRoadmapError("The roadmap is temporarily unavailable.");
    }
  }, [currentPhaseNumber]);

  useEffect(() => {
    if (workflow && currentPhaseNumber != null) void loadPhase();
  }, [currentPhaseNumber, loadPhase, workflow]);

  useEffect(() => {
    const restoreHomeAnchor = () => {
      const hash = window.location.hash;
      if (hash !== "#current-phase" && hash !== "#current-work") {
        restoredAnchorRef.current = null;
        return;
      }
      if (phaseState !== "ready" || restoredAnchorRef.current === hash) return;
      document.querySelector<HTMLElement>(hash)?.scrollIntoView({ block: "start" });
      restoredAnchorRef.current = hash;
    };

    restoreHomeAnchor();
    window.addEventListener("hashchange", restoreHomeAnchor);
    return () => window.removeEventListener("hashchange", restoreHomeAnchor);
  }, [phaseState]);

  async function toggleTask(task: TaskEntry) {
    if (!phase || taskBusy) return;
    setTaskBusy(task.task_id);
    setTaskError(null);
    try {
      setPhase(await setTaskCompletion(phase.phase, task.task_id, !task.completed));
      await refresh();
    } catch (caught) {
      setTaskError(caught instanceof ApiError ? caught.message : "Couldn't update that task.");
    } finally {
      setTaskBusy(null);
    }
  }

  const currentWork = useMemo<CurrentWorkItem[]>(
    () =>
      phase
        ? [
            ...phase.ai_appropriate_tasks.map((task) => ({ ...task, owner: "ai" as const })),
            ...phase.human_required_tasks.map((task) => ({ ...task, owner: "student" as const })),
          ]
        : [],
    [phase]
  );
  const savedCount = workflow
    ? Object.values(workflow.sections).filter((section) => section != null).length
    : 0;
  const currentStageIndex = navigation.continueAction.stageId
    ? navigation.journey.findIndex((stage) => stage.id === navigation.continueAction.stageId)
    : -1;
  const latestRecord = navigation.projectRecord.at(-1);

  return (
    <>
      <header className="project-home-header">
        <div>
          <h1 className="page-title">Project Home</h1>
          <p className="project-home-identity">{navigation.projectLabel}</p>
        </div>
      </header>

      <Async
        loading={state === "loading"}
        error={state === "error" ? error ?? "Project progress is temporarily unavailable." : null}
        onRetry={refresh}
      >
        {evaluation && !workflow && (
          <div className="workspace project-home-setup">
            <div>
              <ContinueCard
                heading={
                  evaluation.state === "not_started" && !entryProfile
                    ? "Let’s find the right place to start"
                    : entryProfile?.completed
                      ? "Finish your project details"
                      : entryProfile
                        ? "Continue finding your starting point"
                        : "Continue project setup"
                }
                intro={
                  evaluation.state === "not_started" && !entryProfile
                    ? "Answer a few short questions. Codize will recommend one starting point."
                    : undefined
                }
              />
              {entryProfile?.completed && <StartingPathSummary profile={entryProfile} />}
            </div>
            <aside className="ws-rail" aria-label="Guidance">
              <GuideCard title="Project Home">
                <p>Project Home stays available while you finish the required setup.</p>
              </GuideCard>
            </aside>
          </div>
        )}

        {evaluation && workflow && (
          <div className="project-home-dashboard">
            <section id="current-phase" className="project-phase-summary" aria-labelledby="current-phase-title">
              {phaseState === "loading" || phaseState === "idle" ? (
                <p className="muted" role="status" aria-live="polite">Loading current phase…</p>
              ) : phaseState === "error" ? (
                <div className="notice error" role="alert">
                  {phaseError}
                  <button className="btn small" type="button" onClick={() => void loadPhase()}>
                    Retry
                  </button>
                </div>
              ) : phase ? (
                <>
                  <p className="entry-kicker">Current phase · {phase.phase} of {evaluation.total_phases}</p>
                  <h2 id="current-phase-title">{phase.phase_title}</h2>
                  <p className="project-phase-purpose">{phaseGuide(phase.phase_title).meaning}</p>
                  <p className="muted project-phase-concept">Focus: {phase.core_concept}</p>
                </>
              ) : null}
            </section>

            {showQuickStart && entryProfile?.recovery_emphasis ? (
              <QuickStartPanel />
            ) : (
              <ContinueCard heading="Continue" />
            )}

            <section id="current-work" className="card current-work" aria-labelledby="current-work-title">
              <div className="current-work-heading">
                <div>
                  <p className="entry-kicker">Current phase work</p>
                  <h2 id="current-work-title">What to handle now</h2>
                </div>
                {phase && (
                  <span className="current-work-count">
                    {phase.completed_task_count} of {phase.total_task_count} done
                  </span>
                )}
              </div>

              {phaseState === "loading" || phaseState === "idle" ? (
                <p className="muted" role="status" aria-live="polite">Loading current work…</p>
              ) : phaseState === "error" ? (
                <p className="muted">Current work will return when the phase reload succeeds.</p>
              ) : currentWork.length > 0 ? (
                <>
                  {assignment && (
                    <AssignmentPanel
                      assignment={assignment}
                      tasks={currentWork}
                      userId={userId}
                      savedPrompt={workflow.sections.prompt_builder}
                      onChanged={refresh}
                    />
                  )}
                  <h3 className="current-work-secondary-title">Phase task checklist</h3>
                  <ol className="current-work-list" aria-label="Ordered current phase work">
                  {currentWork.map((task) => {
                    const statusId = `task-status-${task.task_id}`;
                    return (
                      <li
                        id={`phase-task-${task.task_id}`}
                        key={task.task_id}
                        className={task.completed ? "complete" : undefined}
                      >
                        <label className="task current-work-task">
                          <input
                            type="checkbox"
                            checked={task.completed}
                            disabled={taskBusy !== null}
                            aria-describedby={statusId}
                            onChange={() => void toggleTask(task)}
                          />
                          <span>
                            <span className={`tag ${task.owner}`}>
                              {task.owner === "ai" ? "Use AI" : "You decide"}
                            </span>
                            <span className={task.completed ? "done" : undefined}>{task.description}</span>
                            <span id={statusId} className="task-state">
                              {taskBusy === task.task_id ? "Saving…" : task.completed ? "Done" : "To do"}
                            </span>
                          </span>
                        </label>
                      </li>
                    );
                  })}
                  </ol>
                </>
              ) : (
                <p className="empty">No build tasks are listed for this phase.</p>
              )}
              {taskError && <div className="notice error" role="alert">{taskError}</div>}
              <p className="muted current-work-note">
                Check off build tasks yourself. Saved workflow records do not complete them automatically.
              </p>
            </section>

            <section className="home-workflow-position" aria-labelledby="workflow-position-title">
              <div>
                <p className="entry-kicker">Current workflow position</p>
                <h2 id="workflow-position-title">
                  {currentStageIndex >= 0
                    ? navigation.journey[currentStageIndex].label
                    : "Current phase work"}
                </h2>
              </div>
              <div className="home-workflow-meta" aria-label="Workflow progress details">
                {currentStageIndex >= 0 && (
                  <span>
                    Stage {currentStageIndex + 1} of {navigation.journey.length} · {navigation.journey[currentStageIndex].stateLabel}
                  </span>
                )}
                <span>{savedCount} of 5 workflow records captured</span>
              </div>
            </section>

            <details className="card project-roadmap">
              <summary>
                <span>Roadmap</span>
                <span>
                  Phase {evaluation.current_phase} of {evaluation.total_phases}
                </span>
              </summary>
              <div className="project-roadmap-body">
                {roadmapError ? (
                  <div className="notice info" role="status">
                    {roadmapError}
                    <button className="btn small" type="button" onClick={() => void loadPhase()}>
                      Retry
                    </button>
                  </div>
                ) : phases ? (
                  <ol>
                    {phases.phases.map((item) => (
                      <li key={item.phase} className={item.is_current ? "current" : undefined}>
                        <span className="mono">Phase {item.phase}</span>
                        <span>{item.phase_title}</span>
                        <span>{item.completed_task_count}/{item.total_task_count} tasks</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="muted">Loading roadmap…</p>
                )}
                {evaluation.unlocks && evaluation.unlocks.length > 0 && (
                  <div className="project-unlocks">
                    <h3>Unlocked</h3>
                    <ul>
                      {evaluation.unlocks.map((unlock) => (
                        <li key={unlock.id}>Phase {unlock.phase}: {unlock.description}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>

            <section className="project-record-access" aria-labelledby="project-record-access-title">
              <div>
                <p className="entry-kicker">History</p>
                <h2 id="project-record-access-title">Project Record</h2>
                <p className="muted">
                  {navigation.projectRecord.length > 0
                    ? `${navigation.projectRecord.length} saved record${navigation.projectRecord.length === 1 ? "" : "s"}. Complete means saved, not independently verified.`
                    : "Saved workflow history will appear here as you work."}
                </p>
              </div>
              {latestRecord && (
                <Link className="btn" href={latestRecord.href}>
                  View latest saved work
                </Link>
              )}
            </section>

            <section className="project-home-controls" aria-label="Preferences and project controls">
              {entryProfile?.completed ? (
                <StartingPathSummary profile={entryProfile} />
              ) : (
                <div className="starting-path-summary">
                  <div>
                    <p className="entry-kicker">Guidance</p>
                    <h3>Standard guidance</h3>
                  </div>
                  <Link className="text-link" href="/app/intake?preferences=1">
                    Update guidance preferences
                  </Link>
                </div>
              )}
              <button
                className="btn small"
                disabled
                title="One project per account for now — multi-project support is planned."
              >
                + New project
              </button>
            </section>
          </div>
        )}
      </Async>
    </>
  );
}

type PendingSelection = {
  task: CurrentWorkItem;
  navigate: boolean;
  hasDraft: boolean;
  hasSavedPrompt: boolean;
  savedPromptIsLegacy: boolean;
};

function AssignmentPanel({
  assignment,
  tasks,
  userId,
  savedPrompt,
  onChanged,
}: {
  assignment: PhaseAssignmentState;
  tasks: CurrentWorkItem[];
  userId: string;
  savedPrompt: PromptBuilderArtifact | null;
  onChanged: () => Promise<void>;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingSelection | null>(null);
  const active = assignment.assignment;

  function workToPreserve(next: CurrentWorkItem, navigate: boolean): PendingSelection | null {
    if (!active || active.task_id === next.task_id) return null;
    const local = readDraft<PromptBuilderInputs>(
      window.localStorage,
      draftKey(userId, promptAssignmentDraftSurface(assignment.phase, active.task_id))
    );
    const protection = assignmentSwitchProtection(
      active.task_id,
      next.task_id,
      local,
      savedPrompt
    );
    if (!protection) return null;
    return {
      task: next,
      navigate,
      ...protection,
    };
  }

  async function commitSelection(task: CurrentWorkItem, navigate: boolean) {
    setBusy(true);
    setError(null);
    try {
      await selectCurrentAssignment(task.task_id);
      await onChanged();
      setPending(null);
      if (navigate) router.push("/app/phase/prompt");
      else if (task.owner === "student") {
        document.getElementById(`phase-task-${task.task_id}`)?.scrollIntoView({ block: "center" });
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Couldn't select that task.");
    } finally {
      setBusy(false);
    }
  }

  function choose(task: CurrentWorkItem, navigate = false) {
    const preservation = workToPreserve(task, navigate);
    if (preservation) {
      setPending(preservation);
      return;
    }
    void commitSelection(task, navigate);
  }

  function openAssignment() {
    if (!active) return;
    const task = tasks.find((candidate) => candidate.task_id === active.task_id);
    if (!task) return;
    if (active.owner === "ai") {
      if (assignment.state === "selected") router.push("/app/phase/prompt");
      else choose(task, true);
      return;
    }
    if (assignment.state === "selected") {
      document.getElementById(`phase-task-${active.task_id}`)?.scrollIntoView({ block: "center" });
    } else {
      choose(task);
    }
  }

  const incomplete = tasks.filter((task) => !task.completed && task.task_id !== active?.task_id);
  const completed = tasks.filter((task) => task.completed && task.task_id !== active?.task_id);

  return (
    <div className="phase-assignment" aria-labelledby="phase-assignment-title">
      {active ? (
        <>
          <p className="entry-kicker">
            {assignment.state === "selected" ? "Selected assignment" : "Recommended assignment"}
          </p>
          <div className="phase-assignment-heading">
            <h3 id="phase-assignment-title">{active.description}</h3>
            <span className={`tag assignment-owner ${active.owner}`}>{active.owner_label}</span>
          </div>
          <p className="phase-assignment-reason"><strong>Why now?</strong> {active.reason}</p>
          {active.owner === "student" && (
            <p className="muted">
              Make or document this decision yourself before asking AI to implement dependent work.
              Codize will not send this decision to Prompt Builder.
            </p>
          )}
          <div className="row phase-assignment-actions">
            <button className="btn primary" type="button" disabled={busy} onClick={openAssignment}>
              {busy
                ? "Selecting…"
                : active.owner === "ai"
                  ? assignment.state === "selected" ? "Continue to Prompt Builder" : "Build this prompt"
                  : "Review this decision"}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="entry-kicker">Current assignment</p>
          <h3 id="phase-assignment-title">
            {assignment.state === "phase_complete" ? "All phase tasks are marked done" : "No valid phase task is available"}
          </h3>
          <p className="muted">
            {assignment.state === "phase_complete"
              ? "You can revisit a completed task below. Task completion does not advance the phase."
              : "Reload the roadmap before building another prompt; Codize will not invent a replacement task."}
          </p>
        </>
      )}

      {assignment.invalidated_selection && (
        <div className="notice info" role="status">
          The prior selection no longer resolves in this phase. Codize chose a fresh current-phase recommendation without rebinding old work.
        </div>
      )}
      {assignment.previous_selection && (
        <p className="muted assignment-previous">
          Completed: {assignment.previous_selection.description}. Its Prompt and local draft keep their original task binding.
        </p>
      )}

      {pending && (
        <div className="notice warn assignment-switch-warning" role="alertdialog" aria-labelledby="assignment-switch-title">
          <strong id="assignment-switch-title">Switch to “{pending.task.description}”?</strong>
          <p>Current assignment: “{active?.description}”. Next assignment: “{pending.task.description}”.</p>
          <p>
            {pending.hasDraft && "Your unsaved draft for the current assignment stays saved on this device. "}
            {pending.hasSavedPrompt && (pending.savedPromptIsLegacy
              ? "Your legacy saved Prompt stays unassigned. "
              : "Your saved Prompt keeps its current assignment. ")}
            Nothing will be merged into the new task.
          </p>
          <div className="row">
            <button className="btn" type="button" disabled={busy} onClick={() => setPending(null)}>Cancel</button>
            <button className="btn primary" type="button" disabled={busy} onClick={() => void commitSelection(pending.task, pending.navigate)}>
              {busy ? "Switching…" : "Switch task"}
            </button>
          </div>
        </div>
      )}
      {error && <div className="notice error" role="alert">{error}</div>}

      {(incomplete.length > 0 || completed.length > 0) && (
        <details className="assignment-chooser">
          <summary>Choose another task</summary>
          <div className="assignment-chooser-body">
            <p className="muted">Choose one current-phase task. Opening this list never changes the assignment.</p>
            {incomplete.length > 0 && (
              <ul aria-label="Incomplete current-phase tasks">
                {incomplete.map((task) => (
                  <AssignmentChoice key={task.task_id} task={task} busy={busy} onChoose={choose} />
                ))}
              </ul>
            )}
            {completed.length > 0 && (
              <details className="completed-assignment-choices">
                <summary>Revisit completed tasks</summary>
                <ul aria-label="Completed current-phase tasks">
                  {completed.map((task) => (
                    <AssignmentChoice key={task.task_id} task={task} busy={busy} onChoose={choose} />
                  ))}
                </ul>
              </details>
            )}
          </div>
        </details>
      )}
    </div>
  );
}

function AssignmentChoice({
  task,
  busy,
  onChoose,
}: {
  task: CurrentWorkItem;
  busy: boolean;
  onChoose: (task: CurrentWorkItem) => void;
}) {
  return (
    <li>
      <div>
        <span className={`tag assignment-owner ${task.owner}`}>
          {task.owner === "ai" ? "Use AI" : "You decide"}
        </span>
        <span>{task.description}</span>
        <span className="task-state">{task.completed ? "Completed · revisit" : "To do"}</span>
      </div>
      <button className="btn small" type="button" disabled={busy} onClick={() => onChoose(task)}>
        {task.completed ? "Revisit" : "Select"}
      </button>
    </li>
  );
}

function ContinueCard({ heading, intro }: { heading: string; intro?: string }) {
  const { navigation } = useGuidedProjectNavigation();
  return (
    <section className="card primary project-home-continue" aria-labelledby="project-home-continue-title">
      <h2 id="project-home-continue-title">{heading}</h2>
      {intro && <p className="muted">{intro}</p>}
      <p className="project-home-continue-label">{navigation.continueAction.label}</p>
      <p className="muted">{navigation.continueAction.reason}</p>
      <div className="row">
        <GuidedContinueAction className="btn primary" />
      </div>
    </section>
  );
}
