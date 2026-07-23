"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import AdaptiveStepGuide from "@/components/AdaptiveStepGuide";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { ApiError, getCurrentAssignment, getIntakeStatus, selectCurrentAssignment } from "@/lib/api";
import {
  legacyPromptDraftSurface,
  promptAssignmentDraftSurface,
  useDraft,
} from "@/lib/drafts";
import { phaseGuide } from "@/lib/phaseGuide";
import { buildPrompt, type PromptBuilderInputs } from "@/lib/promptBuilder";
import { useWorkflowSection } from "@/lib/useWorkflowSection";
import type { PhaseAssignmentState, PromptBuilderArtifact } from "@/lib/types";

const EMPTY: PromptBuilderInputs = {
  projectGoal: "",
  phaseGoal: "",
  aiTask: "",
  files: "",
  constraints: "",
  doNotChange: "",
  planFirst: true,
  wantChecks: true,
  uncertainty: "",
};

function inputsFromArtifact(artifact: PromptBuilderArtifact): PromptBuilderInputs {
  const saved = artifact.inputs ?? {};
  return {
    projectGoal: saved.project_goal ?? "",
    phaseGoal: saved.phase_goal ?? "",
    aiTask: saved.ai_task ?? "",
    files: saved.files ?? "",
    constraints: saved.constraints ?? "",
    doNotChange: saved.do_not_change ?? "",
    planFirst: saved.plan_first !== "no",
    wantChecks: saved.want_checks !== "no",
    uncertainty: saved.uncertainty ?? "",
  };
}

function builtFromArtifact(artifact: PromptBuilderArtifact) {
  return {
    prompt: artifact.generated_prompt,
    whyStronger: artifact.why_stronger ?? "",
    badPrompt: artifact.bad_prompt_comparison ?? "",
  };
}

// Deterministic client-side Prompt Builder (v0.1) — no LLM call. Output is
// persisted as the phase's prompt_builder artifact (M13B). M13E.1 added the
// beginner layer: a plain-language phase explanation, starter asks (from the
// static phase guide + the phase's own roadmap tasks), and per-field help —
// the builder should produce a good prompt even when the student doesn't yet
// know what to ask.
export default function PromptBuilderPage() {
  const wf = useWorkflowSection("prompt_builder");
  const [inputs, setInputs] = useState<PromptBuilderInputs>(EMPTY);
  const [built, setBuilt] = useState<ReturnType<typeof buildPrompt> | null>(null);
  const [copied, setCopied] = useState(false);
  const [intakePurpose, setIntakePurpose] = useState<string | null>(null);
  const [intakeStack, setIntakeStack] = useState<string | null>(null);
  const [assignment, setAssignment] = useState<PhaseAssignmentState | null>(null);
  const [assignmentLoading, setAssignmentLoading] = useState(true);
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [assignmentBusy, setAssignmentBusy] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!wf.phase) return;
    let cancelled = false;
    setAssignmentLoading(true);
    getCurrentAssignment()
      .then((next) => {
        if (!cancelled) setAssignment(next);
      })
      .catch((caught) => {
        if (!cancelled) {
          setAssignmentError(
            caught instanceof ApiError ? caught.message : "Couldn't load the current assignment."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setAssignmentLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [wf.phase]);

  const activeAssignment =
    assignment?.state === "selected" && assignment.assignment?.owner === "ai"
      ? assignment.assignment
      : null;
  const draftSurface = wf.phase && activeAssignment
    ? promptAssignmentDraftSurface(wf.phase.phase, activeAssignment.task_id)
    : null;

  // Unsaved-draft persistence (M13E.2): the saved artifact prefills first,
  // then any local draft (typed but never saved) overlays it once.
  const draft = useDraft<PromptBuilderInputs>(draftSurface);
  const legacyDraft = useDraft<PromptBuilderInputs>(
    wf.phase ? legacyPromptDraftSurface(wf.phase.phase) : null
  );
  const initializedFor = useRef<string | null>(null);
  const pendingAssignmentFill = useRef<string | null>(null);
  useEffect(() => {
    if (wf.loading || assignmentLoading || !activeAssignment || !draft.ready || !draftSurface) return;
    if (draft.loadedSurface !== draftSurface || initializedFor.current === draftSurface) return;
    initializedFor.current = draftSurface;
    if (draft.restored) {
      setInputs({ ...EMPTY, ...draft.restored });
      setBuilt(null);
      setDirty(true);
      return;
    }
    if (wf.stored?.assignment_task_id === activeAssignment.task_id) {
      setInputs(inputsFromArtifact(wf.stored));
      setBuilt(builtFromArtifact(wf.stored));
      setDirty(false);
      return;
    }
    const useTask = pendingAssignmentFill.current === activeAssignment.task_id;
    pendingAssignmentFill.current = null;
    setInputs({ ...EMPTY, aiTask: activeAssignment.description });
    setBuilt(null);
    setDirty(useTask);
  }, [activeAssignment, assignmentLoading, draft.loadedSurface, draft.ready, draft.restored, draftSurface, wf.loading, wf.stored]);
  // A successful save re-prefills state from the stored artifact, which would
  // immediately re-write the just-cleared draft — skip that one echo.
  const saveDraft = draft.save;
  useEffect(() => {
    if (!dirty || !activeAssignment || draft.loadedSurface !== draftSurface) return;
    saveDraft(inputs);
  }, [activeAssignment, dirty, draft.loadedSurface, draftSurface, inputs, saveDraft]);

  // The student's own intake answers, offered as tap-to-use starters (never
  // auto-filled — the student stays the author of every field).
  useEffect(() => {
    let cancelled = false;
    getIntakeStatus()
      .then((s) => {
        if (cancelled) return;
        setIntakePurpose(s.answers?.purpose ?? null);
        setIntakeStack(s.answers?.stack ?? null);
      })
      .catch(() => {
        // Starters are optional sugar; the page works without them.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (wf.notReady) return <NotReady title="Prompt Builder" />;

  const set = (key: keyof PromptBuilderInputs, value: string | boolean) => {
    setInputs((prev) => ({ ...prev, [key]: value }));
    setBuilt(null);
    setDirty(true);
  };

  // Quick-add guardrail chips append (never overwrite) the constraints field.
  const addConstraint = (text: string) => {
    setInputs((prev) => ({
      ...prev,
      constraints: prev.constraints.trim()
        ? prev.constraints.includes(text)
          ? prev.constraints
          : `${prev.constraints}. ${text}`
        : text,
    }));
    setBuilt(null);
    setDirty(true);
  };

  async function applyAssignmentToTaskField() {
    const task = assignment?.assignment;
    if (!task || task.owner !== "ai") return;
    if (assignment.state === "recommended") {
      setAssignmentBusy(true);
      setAssignmentError(null);
      pendingAssignmentFill.current = task.task_id;
      try {
        const selected = await selectCurrentAssignment(task.task_id);
        initializedFor.current = null;
        setAssignment(selected);
      } catch (caught) {
        pendingAssignmentFill.current = null;
        setAssignmentError(
          caught instanceof ApiError ? caught.message : "Couldn't select that assignment."
        );
      } finally {
        setAssignmentBusy(false);
      }
      return;
    }
    set("aiTask", task.description);
  }

  function useLegacyDraft() {
    if (!legacyDraft.restored || !activeAssignment) return;
    setInputs({ ...EMPTY, ...legacyDraft.restored, aiTask: activeAssignment.description });
    setBuilt(null);
    setDirty(true);
  }

  function generate() {
    setBuilt(buildPrompt(inputs));
    setCopied(false);
  }

  async function save() {
    if (!activeAssignment) return;
    const result = built ?? buildPrompt(inputs);
    setBuilt(result);
    const ok = await wf.save({
      inputs: {
        project_goal: inputs.projectGoal.slice(0, 2000),
        phase_goal: inputs.phaseGoal.slice(0, 2000),
        ai_task: inputs.aiTask.slice(0, 2000),
        files: inputs.files.slice(0, 2000),
        constraints: inputs.constraints.slice(0, 2000),
        do_not_change: inputs.doNotChange.slice(0, 2000),
        plan_first: inputs.planFirst ? "yes" : "no",
        want_checks: inputs.wantChecks ? "yes" : "no",
        uncertainty: inputs.uncertainty.slice(0, 2000),
      },
      generated_prompt: result.prompt,
      why_stronger: result.whyStronger.slice(0, 2000),
      bad_prompt_comparison: result.badPrompt.slice(0, 8000),
      assignment_task_id: activeAssignment.task_id,
    });
    if (ok) {
      draft.clear();
      setDirty(false);
    }
  }

  async function copy() {
    if (!built) return;
    try {
      await navigator.clipboard.writeText(built.prompt);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  const guide = wf.phase ? phaseGuide(wf.phase.phase_title) : null;
  const roadmapStarters = wf.phase
    ? wf.phase.ai_appropriate_tasks.filter((t) => !t.completed).slice(0, 3)
    : [];
  const taskById = new Map(
    wf.phase
      ? [...wf.phase.ai_appropriate_tasks, ...wf.phase.human_required_tasks].map((task) => [task.task_id, task])
      : []
  );
  const savedMatchesAssignment = Boolean(
    activeAssignment && wf.stored?.assignment_task_id === activeAssignment.task_id
  );

  return (
    <>
      <h1 className="page-title">Prompt Builder</h1>
      <p className="page-sub">
        One clear ask beats a long conversation. Tap a starter if you&rsquo;re not sure — Codize
        turns it into a strong prompt.
      </p>
      <AdaptiveStepGuide stage="prompt" />

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
            <section className="card primary prompt-assignment" aria-labelledby="prompt-assignment-title">
              <p className="entry-kicker">Current prompt assignment</p>
              {assignmentLoading ? (
                <p className="muted" role="status">Loading assignment…</p>
              ) : assignmentError ? (
                <div className="notice error" role="alert">{assignmentError}</div>
              ) : assignment?.assignment ? (
                <>
                  <div className="phase-assignment-heading">
                    <h2 id="prompt-assignment-title">{assignment.assignment.description}</h2>
                    <span className={`tag assignment-owner ${assignment.assignment.owner}`}>
                      {assignment.assignment.owner_label}
                    </span>
                  </div>
                  <p className="muted">Phase {assignment.phase} · {assignment.phase_title}</p>
                  <p className="prompt-assignment-reason">{assignment.assignment.reason}</p>
                  <p className="one-task-rule">
                    Work on one focused task in this prompt. Do not combine it with another phase task unless Codize explicitly groups them.
                  </p>
                  {assignment.assignment.owner === "ai" ? (
                    <div className="row">
                      <button className="btn primary" type="button" disabled={assignmentBusy} onClick={() => void applyAssignmentToTaskField()}>
                        {assignmentBusy ? "Selecting…" : "Use this assignment"}
                      </button>
                      <Link className="btn" href="/app#current-work">Choose another task</Link>
                    </div>
                  ) : (
                    <div className="notice info">
                      You decide this task. Codize will not turn it into an AI prompt. Make or document the decision on Project Home first.
                      <div className="row"><Link className="btn" href="/app#current-work">Return to Project Home</Link></div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <h2 id="prompt-assignment-title">No AI assignment is selected</h2>
                  <p className="muted">
                    {assignment?.state === "phase_complete"
                      ? "All current-phase tasks are marked done. Revisit one deliberately from Project Home if you need another Prompt."
                      : "Choose a valid current-phase AI task before building a Prompt."}
                  </p>
                  <Link className="btn" href="/app#current-work">Return to Project Home</Link>
                </>
              )}
            </section>

            {wf.stored && !savedMatchesAssignment && (
              <SavedPromptRecord
                artifact={wf.stored}
                taskLabel={wf.stored.assignment_task_id && !assignment?.invalidated_selection
                  ? taskById.get(wf.stored.assignment_task_id)?.description
                  : undefined}
                heading={wf.stored.assignment_task_id ? "Saved Prompt for another assignment" : "Legacy saved Prompt"}
              />
            )}

            {activeAssignment && legacyDraft.ready && legacyDraft.restored && (
              <div className="notice info prompt-legacy-draft">
                <strong>Unassigned local draft preserved</strong>
                <p>This draft predates task binding. It has not been merged with “{activeAssignment.description}”.</p>
                <button className="btn small" type="button" onClick={useLegacyDraft}>
                  Use this draft with the current assignment
                </button>
              </div>
            )}

            {activeAssignment && (
              <>
            {/* Step 1 — the ask. The only required field, starters included. */}
            <div className="card primary" style={{ marginBottom: 16 }}>
              <label className="prompt-task-label" htmlFor="prompt-ai-task">Step 1 — What should the AI do?</label>
              <textarea
                id="prompt-ai-task"
                rows={3}
                maxLength={2000}
                value={inputs.aiTask}
                onChange={(e) => set("aiTask", e.target.value)}
                placeholder="One task, e.g. propose a schema for tasks and members, and explain each table"
              />
              {guide && (
                <details className="help prompt-generic-starters">
                  <summary>Generic starters</summary>
                  <div className="help-body">
                  <p className="muted">Use these only when the real assignment needs different wording.</p>
                  <div className="chips">
                    {guide.asks.map((a) => (
                      <button
                        key={a}
                        type="button"
                        className="chip"
                        onClick={() => set("aiTask", a)}
                      >
                        {a}
                      </button>
                    ))}
                    {roadmapStarters.map((t) => (
                      <button
                        key={t.task_id}
                        type="button"
                        className="chip"
                        onClick={() => set("aiTask", t.description)}
                      >
                        {t.description}
                      </button>
                    ))}
                  </div>
                  </div>
                </details>
              )}
              {wf.phase && guide && (
                <details className="help">
                  <summary>What does this phase mean?</summary>
                  <div className="help-body">
                    <p>{guide.meaning}</p>
                    <p className="muted">Your roadmap puts it this way: {wf.phase.core_concept}</p>
                  </div>
                </details>
              )}
            </div>

            <div className="card-grid">
              {/* Step 2 — context, all optional. */}
              <div className="card">
                <h3>Step 2 — Context (optional)</h3>
                <div className="field">
                  <label>Your project</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.projectGoal}
                    onChange={(e) => set("projectGoal", e.target.value)}
                    placeholder="one sentence, e.g. a task tracker for my study group"
                  />
                  {intakePurpose && !inputs.projectGoal && (
                    <div className="chips">
                      <button
                        type="button"
                        className="chip"
                        onClick={() => set("projectGoal", intakePurpose)}
                      >
                        Use my intake answer
                      </button>
                    </div>
                  )}
                </div>
                <div className="field">
                  <label>This phase</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.phaseGoal}
                    onChange={(e) => set("phaseGoal", e.target.value)}
                    placeholder="in your own words, e.g. designing the data model"
                  />
                  {guide && !inputs.phaseGoal && (
                    <div className="chips">
                      <button
                        type="button"
                        className="chip"
                        onClick={() => set("phaseGoal", guide.meaning)}
                      >
                        Use the phase explanation
                      </button>
                    </div>
                  )}
                </div>
                <div className="field">
                  <label>Files involved</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.files}
                    onChange={(e) => set("files", e.target.value)}
                    placeholder="only if you know them, e.g. app/models.py"
                  />
                </div>
              </div>

              {/* Step 3 — guardrails. Quick-add chips over typing. */}
              <div className="card">
                <h3>Step 3 — Guardrails</h3>
                <div className="chips" style={{ marginTop: 0 }}>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => set("planFirst", true)}
                  >
                    Plan first
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => addConstraint("Ask me clarifying questions before writing any code")}
                  >
                    Ask questions before coding
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() =>
                      set(
                        "doNotChange",
                        inputs.doNotChange.trim()
                          ? `${inputs.doNotChange}, the auth setup`
                          : "the auth setup"
                      )
                    }
                  >
                    Do not touch auth
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => addConstraint("Explain each table and decision in plain language")}
                  >
                    Explain each table
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => set("wantChecks", true)}
                  >
                    Give manual verification steps
                  </button>
                </div>
                <div className="field">
                  <label>Rules the AI must follow</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.constraints}
                    onChange={(e) => set("constraints", e.target.value)}
                    placeholder='e.g. "Python only — that&apos;s what I know"'
                  />
                  {intakeStack && !inputs.constraints && (
                    <div className="chips">
                      <button
                        type="button"
                        className="chip"
                        onClick={() => set("constraints", `Stick to what I know: ${intakeStack}`)}
                      >
                        Use my stack from intake
                      </button>
                    </div>
                  )}
                </div>
                <div className="field">
                  <label>Don&rsquo;t touch</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.doNotChange}
                    onChange={(e) => set("doNotChange", e.target.value)}
                    placeholder="anything that already works, e.g. main.py"
                  />
                </div>
                <div className="field">
                  <label>Least sure about</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.uncertainty}
                    onChange={(e) => set("uncertainty", e.target.value)}
                    placeholder="naming it is a strength, e.g. foreign keys"
                  />
                </div>
                <label className="checkline">
                  <input
                    type="checkbox"
                    checked={inputs.planFirst}
                    onChange={(e) => set("planFirst", e.target.checked)}
                  />
                  Ask for a plan before any code
                </label>
                <label className="checkline">
                  <input
                    type="checkbox"
                    checked={inputs.wantChecks}
                    onChange={(e) => set("wantChecks", e.target.checked)}
                  />
                  Ask for manual verification steps
                </label>
              </div>
            </div>

            <div className="row" style={{ margin: "16px 0" }}>
              <button className="btn primary" onClick={generate} disabled={!inputs.aiTask.trim()}>
                Build the prompt
              </button>
              {!inputs.aiTask.trim() && (
                <span className="muted">Step 1 first — a starter chip works.</span>
              )}
            </div>

            {built && (
              <>
                <div className="card">
                  <div className="spread">
                    <h3>Your prompt — paste into your AI tool</h3>
                    <button className="btn small" onClick={copy}>
                      {copied ? "Copied ✓" : "Copy"}
                    </button>
                  </div>
                  <pre className="output">{built.prompt}</pre>
                </div>
                <div className="card">
                  <h3>Why this is stronger</h3>
                  <p>{built.whyStronger}</p>
                  <hr className="rule" />
                  <p className="muted">
                    Compare with what usually goes wrong:{" "}
                    <span className="mono">&ldquo;{built.badPrompt}&rdquo;</span> — no scope, no
                    fences, no verification. That prompt is how projects end up 80% done and 100%
                    confusing.
                  </p>
                </div>
                <SaveBar
                  saving={wf.saving}
                  saveError={wf.saveError}
                  savedAt={wf.savedAt}
                  onSave={save}
                  label="Save to workflow"
                />
                {/* The loop's hand-off: prompt out → result back (M15B). */}
                {wf.savedAt && (
                  <p className="muted" style={{ marginTop: 12 }}>
                    Use your prompt in your AI coding tool. Then{" "}
                    <Link href="/app/phase/import">Bring Back What Changed →</Link>
                  </p>
                )}
              </>
            )}
              </>
            )}

            {wf.promptHistory.length > 0 && (
              <details className="card prompt-history">
                <summary>Prior saved Prompts ({wf.promptHistory.length})</summary>
                <div className="prompt-history-list">
                  {wf.promptHistory.map((artifact, index) => (
                    <SavedPromptRecord
                      key={`${artifact.saved_at ?? "legacy"}-${index}`}
                      artifact={artifact}
                      taskLabel={artifact.assignment_task_id && !assignment?.invalidated_selection
                        ? taskById.get(artifact.assignment_task_id)?.description
                        : undefined}
                      heading={artifact.assignment_task_id ? "Prior assignment Prompt" : "Prior legacy Prompt"}
                    />
                  ))}
                </div>
              </details>
            )}
          </div>

          <aside className="ws-rail" aria-label="Guidance">
            <GuideCard title="What is this page?">
              <p>
                Before you ask your AI tool for code, you plan the request here. Codize turns your
                answers into a scoped, fenced prompt — the difference between directing AI and
                gambling with it.
              </p>
            </GuideCard>
            <GuideCard title="A good ask is…">
              <ul>
                <li><strong>One task</strong>, not &ldquo;build my app&rdquo;.</li>
                <li><strong>Fenced</strong> — says what must not change.</li>
                <li><strong>Checkable</strong> — asks how you&rsquo;ll verify it.</li>
              </ul>
              <p>You don&rsquo;t have to write it from scratch — the starters exist to be edited.</p>
            </GuideCard>
            <GuideCard title="Confused by a field?">
              <p>
                Every field has a hint under it, and every field except the AI task is optional.
                A prompt from just one clear task already beats most prompts.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}

function SavedPromptRecord({
  artifact,
  taskLabel,
  heading,
}: {
  artifact: PromptBuilderArtifact;
  taskLabel?: string;
  heading: string;
}) {
  return (
    <section className="card saved-prompt-record" aria-label={heading}>
      <div className="spread">
        <h3>{heading}</h3>
        <span className="pill">
          {artifact.assignment_task_id ? "Assignment-bound" : "Legacy · unassigned"}
        </span>
      </div>
      <p className="muted">
        {artifact.assignment_task_id
          ? taskLabel ?? "The original task no longer resolves in the current roadmap. This Prompt keeps its historical binding."
          : "Saved before assignment binding existed. Codize does not fabricate a task association."}
      </p>
      <pre className="output">{artifact.generated_prompt}</pre>
      {artifact.saved_at && <p className="muted">Saved {new Date(artifact.saved_at).toLocaleString()}</p>}
    </section>
  );
}
