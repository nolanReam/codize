"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import Async from "@/components/Async";
import { useGuidedProjectNavigation } from "@/components/GuidedProjectNavigationProvider";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { ApiError, getCurrentAssignment, getIntakeStatus, selectCurrentAssignment } from "@/lib/api";
import {
  legacyPromptDraftSurface,
  promptAssignmentDraftSurface,
  promptScopeDraftSurface,
  useDraft,
} from "@/lib/drafts";
import {
  BOUNDED_ASSIGNMENT_OBJECTIVE_NAME,
  EMPTY_SCOPE_PRACTICE,
  SCOPE_PRACTICE_MAX_CODE_POINTS,
  codePointLength,
  normalizeScopePracticeDraft,
  normalizeStoredScopePractice,
  promptArtifactMatchesAssignment,
  scopeApplication,
  scopeApplicationConflicts,
  scopeApplicationIsCurrent,
  scopeFromStored,
  scopeSubmission,
  validateScopePractice,
  type ScopeFieldName,
  type ScopePracticeDraft,
} from "@/lib/boundedAssignment";
import { phaseGuide } from "@/lib/phaseGuide";
import {
  buildPrompt,
  normalizePromptBuilderInputs,
  type PromptBuilderInputs,
} from "@/lib/promptBuilder";
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
  const { entryProfile } = useGuidedProjectNavigation();
  const [inputs, setInputs] = useState<PromptBuilderInputs>(EMPTY);
  const [scope, setScope] = useState<ScopePracticeDraft>(EMPTY_SCOPE_PRACTICE);
  const [built, setBuilt] = useState<ReturnType<typeof buildPrompt> | null>(null);
  const [copied, setCopied] = useState(false);
  const [intakePurpose, setIntakePurpose] = useState<string | null>(null);
  const [intakeStack, setIntakeStack] = useState<string | null>(null);
  const [assignment, setAssignment] = useState<PhaseAssignmentState | null>(null);
  const [assignmentLoading, setAssignmentLoading] = useState(true);
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [assignmentBusy, setAssignmentBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [scopeDirty, setScopeDirty] = useState(false);
  const [scopeAttempted, setScopeAttempted] = useState(false);
  const [applyConflict, setApplyConflict] = useState<{
    task: boolean;
    guardrail: boolean;
  } | null>(null);
  const scopeFieldRefs = useRef<Record<ScopeFieldName, HTMLTextAreaElement | null>>({
    finishCondition: null,
    excludedWork: null,
    inspectionCondition: null,
  });
  const taskFieldRef = useRef<HTMLTextAreaElement | null>(null);
  const conflictRef = useRef<HTMLDivElement | null>(null);
  const applyTriggerRef = useRef<HTMLButtonElement | null>(null);

  const loadAssignment = useCallback(async () => {
    if (!wf.phase) return;
    setAssignmentLoading(true);
    setAssignmentError(null);
    try {
      setAssignment(await getCurrentAssignment());
    } catch (caught) {
      setAssignment(null);
      setAssignmentError(
        caught instanceof ApiError ? caught.message : "Couldn't load the current assignment."
      );
    } finally {
      setAssignmentLoading(false);
    }
  }, [wf.phase]);

  useEffect(() => {
    void loadAssignment();
    const refreshOnFocus = () => void loadAssignment();
    window.addEventListener("focus", refreshOnFocus);
    return () => {
      window.removeEventListener("focus", refreshOnFocus);
    };
  }, [loadAssignment]);

  const activeAssignment =
    assignment?.state === "selected" && assignment.assignment?.owner === "ai"
      ? assignment.assignment
      : null;
  const activeAssignmentRevision = activeAssignment
    ? assignment?.assignment_revision ?? null
    : null;
  const draftSurface = wf.phase && activeAssignment && activeAssignmentRevision
    ? promptAssignmentDraftSurface(
        wf.phase.phase,
        activeAssignment.task_id,
        activeAssignmentRevision
      )
    : null;
  const scopeDraftSurface = wf.phase && activeAssignment && activeAssignmentRevision
    ? promptScopeDraftSurface(
        wf.phase.phase,
        activeAssignment.task_id,
        activeAssignmentRevision
      )
    : null;

  // Unsaved-draft persistence (M13E.2): the saved artifact prefills first,
  // then any local draft (typed but never saved) overlays it once.
  const draft = useDraft<unknown>(draftSurface);
  const scopeDraft = useDraft<unknown>(scopeDraftSurface);
  const legacyDraft = useDraft<PromptBuilderInputs>(
    wf.phase ? legacyPromptDraftSurface(wf.phase.phase) : null
  );
  const initializedFor = useRef<string | null>(null);
  const scopeInitializedFor = useRef<string | null>(null);
  useEffect(() => {
    if (wf.loading || assignmentLoading || !activeAssignment || !draft.ready || !draftSurface) return;
    if (draft.loadedSurface !== draftSurface || initializedFor.current === draftSurface) return;
    initializedFor.current = draftSurface;
    if (draft.restored) {
      const restored = normalizePromptBuilderInputs(draft.restored);
      if (restored) {
        setInputs(restored);
        setBuilt(null);
        setDirty(true);
        return;
      }
    }
    if (
      wf.stored &&
      activeAssignmentRevision &&
      promptArtifactMatchesAssignment(
        wf.stored,
        activeAssignment,
        activeAssignmentRevision
      )
    ) {
      setInputs(inputsFromArtifact(wf.stored));
      setBuilt(builtFromArtifact(wf.stored));
      setDirty(false);
      return;
    }
    setInputs(EMPTY);
    setBuilt(null);
    setDirty(false);
  }, [activeAssignment, activeAssignmentRevision, assignmentLoading, draft.loadedSurface, draft.ready, draft.restored, draftSurface, wf.loading, wf.stored]);

  useEffect(() => {
    if (
      wf.loading ||
      assignmentLoading ||
      !activeAssignment ||
      !activeAssignmentRevision ||
      !scopeDraft.ready ||
      !scopeDraftSurface
    ) return;
    if (
      scopeDraft.loadedSurface !== scopeDraftSurface ||
      scopeInitializedFor.current === scopeDraftSurface
    ) return;
    scopeInitializedFor.current = scopeDraftSurface;
    setScopeAttempted(false);
    setApplyConflict(null);

    const restored = normalizeScopePracticeDraft(scopeDraft.restored);
    if (restored) {
      setScope(restored);
      setScopeDirty(
        Boolean(
          restored.finishCondition.trim() ||
            restored.excludedWork.trim() ||
            restored.inspectionCondition.trim() ||
            restored.applied
        )
      );
      return;
    }

    const storedScope = normalizeStoredScopePractice(wf.stored?.scope_practice);
    if (
      wf.stored?.assignment_task_id === activeAssignment.task_id &&
      storedScope?.assignment_task_id === activeAssignment.task_id &&
      storedScope.assignment_revision === activeAssignmentRevision
    ) {
      const fromStored = scopeFromStored(storedScope);
      setScope({
        ...fromStored,
        applied: scopeApplication(fromStored, activeAssignment.description),
      });
      setScopeDirty(false);
      return;
    }

    setScope(EMPTY_SCOPE_PRACTICE);
    setScopeDirty(false);
  }, [
    activeAssignment,
    activeAssignmentRevision,
    assignmentLoading,
    scopeDraft.loadedSurface,
    scopeDraft.ready,
    scopeDraft.restored,
    scopeDraftSurface,
    wf.loading,
    wf.stored,
  ]);

  // A successful save re-prefills state from the stored artifact, which would
  // immediately re-write the just-cleared draft — skip that one echo.
  const saveDraft = draft.save;
  useEffect(() => {
    if (!dirty || !activeAssignment || draft.loadedSurface !== draftSurface) return;
    saveDraft(inputs);
  }, [activeAssignment, dirty, draft.loadedSurface, draftSurface, inputs, saveDraft]);
  const saveScopeDraft = scopeDraft.save;
  useEffect(() => {
    if (
      !scopeDirty ||
      !activeAssignment ||
      scopeDraft.loadedSurface !== scopeDraftSurface
    ) return;
    saveScopeDraft(scope);
  }, [
    activeAssignment,
    saveScopeDraft,
    scope,
    scopeDirty,
    scopeDraft.loadedSurface,
    scopeDraftSurface,
  ]);

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

  useEffect(() => {
    if (applyConflict) conflictRef.current?.focus();
  }, [applyConflict]);

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

  const setScopeField = (field: ScopeFieldName, value: string) => {
    setScope((current) => ({ ...current, [field]: value }));
    setScopeDirty(true);
    setBuilt(null);
    setApplyConflict(null);
  };

  function focusFirstScopeError() {
    const order: ScopeFieldName[] = [
      "finishCondition",
      "excludedWork",
      "inspectionCondition",
    ];
    const first = order.find((field) => scopeValidation.errors[field]);
    if (first) {
      window.setTimeout(() => scopeFieldRefs.current[first]?.focus(), 0);
    }
  }

  function applyScopeToPrompt(replaceConflicts = false) {
    setScopeAttempted(true);
    if (!scopeValidation.complete) {
      focusFirstScopeError();
      return;
    }
    const proposed = scopeApplication(scope, activeAssignment?.description ?? "");
    const conflicts = scopeApplicationConflicts(inputs, scope.applied, proposed);
    if (!replaceConflicts && (conflicts.task || conflicts.guardrail)) {
      setApplyConflict(conflicts);
      return;
    }
    setInputs((current) => ({
      ...current,
      aiTask: proposed.taskText,
      doNotChange: proposed.guardrailText,
    }));
    setScope((current) => ({ ...current, applied: proposed }));
    setScopeDirty(true);
    setDirty(true);
    setBuilt(null);
    setApplyConflict(null);
    window.setTimeout(() => taskFieldRef.current?.focus(), 0);
  }

  function scopeReadyForFinalAction(): boolean {
    if (!scopeValidation.complete) {
      setScopeAttempted(true);
      focusFirstScopeError();
      return false;
    }
    if (
      !activeAssignment ||
      !scopeApplicationIsCurrent(
        scope,
        scope.applied,
        activeAssignment.description
      )
    ) {
      setScopeAttempted(true);
      window.setTimeout(
        () => document.getElementById("apply-scope-to-prompt")?.focus(),
        0
      );
      return false;
    }
    return true;
  }

  function cancelApplyConflict() {
    setApplyConflict(null);
    window.setTimeout(() => applyTriggerRef.current?.focus(), 0);
  }

  async function selectPromptAssignment() {
    const task = assignment?.assignment;
    if (!task || task.owner !== "ai" || assignment.state !== "recommended") return;
    setAssignmentBusy(true);
    setAssignmentError(null);
    try {
      const selected = await selectCurrentAssignment(task.task_id);
      initializedFor.current = null;
      scopeInitializedFor.current = null;
      setAssignment(selected);
    } catch (caught) {
      setAssignmentError(
        caught instanceof ApiError ? caught.message : "Couldn't select that assignment."
      );
    } finally {
      setAssignmentBusy(false);
    }
  }

  function useLegacyDraft() {
    if (!legacyDraft.restored || !activeAssignment) return;
    const restored = normalizePromptBuilderInputs(legacyDraft.restored);
    if (!restored) return;
    setInputs({ ...restored, aiTask: activeAssignment.description });
    setBuilt(null);
    setDirty(true);
  }

  function generate() {
    if (finalScopeMustBeReady && !scopeReadyForFinalAction()) return;
    if (!inputs.aiTask.trim()) {
      window.setTimeout(() => taskFieldRef.current?.focus(), 0);
      return;
    }
    setBuilt(buildPrompt(inputs, { assignment: activeAssignment?.description }));
    setCopied(false);
  }

  async function save() {
    if (!activeAssignment) return;
    if (finalScopeMustBeReady && !scopeReadyForFinalAction()) return;
    const result =
      built ?? buildPrompt(inputs, { assignment: activeAssignment.description });
    setBuilt(result);
    const persistScope =
      scopeValidation.complete &&
      scopeApplicationIsCurrent(
        scope,
        scope.applied,
        activeAssignment.description
      );
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
      ...(persistScope ? { scope_practice: scopeSubmission(scope) } : {}),
    });
    if (ok) {
      draft.clear();
      setDirty(false);
      if (persistScope) {
        scopeDraft.clear();
        setScopeDirty(false);
      }
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
    activeAssignment &&
      assignment &&
      promptArtifactMatchesAssignment(
        wf.stored,
        activeAssignment,
        assignment.assignment_revision
      )
  );
  const scopeValidation = validateScopePractice(scope);
  const legacyBoundPrompt = Boolean(
    savedMatchesAssignment &&
      !normalizeStoredScopePractice(wf.stored?.scope_practice)
  );
  const finalScopeMustBeReady =
    Boolean(activeAssignment && !legacyBoundPrompt) || scopeValidation.complete;
  const scopeAppliedCurrent =
    Boolean(activeAssignment) &&
    scopeValidation.complete &&
    scopeApplicationIsCurrent(
      scope,
      scope.applied,
      activeAssignment?.description ?? ""
    );
  const promptChangedAfterApply = Boolean(
    scopeAppliedCurrent &&
      scope.applied &&
      (inputs.aiTask !== scope.applied.taskText ||
        inputs.doNotChange !== scope.applied.guardrailText)
  );
  const guidanceDepth = entryProfile?.guidance_depth ?? "standard";

  return (
    <>
      <h1 className="page-title">Prompt Builder</h1>
      <p className="page-sub">
        Turn the selected phase assignment into one request you can inspect before using it with your AI tool.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
            <section
              className={`card prompt-assignment${activeAssignment ? "" : " primary"}`}
              aria-labelledby="prompt-assignment-title"
            >
              <h2 id="prompt-assignment-title" className="entry-kicker">Current prompt assignment</h2>
              {assignmentLoading ? (
                <p className="muted" role="status">Loading assignment…</p>
              ) : assignmentError ? (
                <div className="notice error" role="alert">
                  {assignmentError}
                  <button className="btn small" type="button" onClick={() => void loadAssignment()}>
                    Retry assignment
                  </button>
                </div>
              ) : assignment?.assignment ? (
                <>
                  <div className="phase-assignment-heading">
                    <h3>{assignment.assignment.description}</h3>
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
                      {assignment.state === "recommended" ? (
                        <button className="btn primary" type="button" disabled={assignmentBusy} onClick={() => void selectPromptAssignment()}>
                          {assignmentBusy ? "Selecting…" : "Use this assignment"}
                        </button>
                      ) : (
                        <span className="pill ok">Selected for this Prompt</span>
                      )}
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
                  <h3>No AI assignment is selected</h3>
                  <p className="muted">
                    {assignment?.state === "phase_complete"
                      ? "All current-phase tasks are marked done. Revisit one deliberately from Project Home if you need another Prompt."
                      : "Choose a valid current-phase AI task before building a Prompt."}
                  </p>
                  <Link className="btn" href="/app#current-work">Return to Project Home</Link>
                </>
              )}
            </section>

            {activeAssignment && (
              <section
                className="card primary bounded-assignment-practice"
                aria-labelledby="bounded-assignment-title"
              >
                <div className="bounded-practice-heading">
                  <div>
                    <p className="entry-kicker">Learning focus</p>
                    <h2 id="bounded-assignment-title">
                      {BOUNDED_ASSIGNMENT_OBJECTIVE_NAME}
                    </h2>
                  </div>
                  <span className="pill">Required for new assigned Prompts</span>
                </div>
                <p className="bounded-practice-purpose">
                  A focused request is easier to inspect, test, and understand than several features bundled into one AI change.
                </p>

                {guidanceDepth === "minimal" ? (
                  <details className="help bounded-practice-why">
                    <summary>Why this matters</summary>
                    <div className="help-body">
                      <p>
                        One AI request should produce one result that you can inspect. Bundling several features makes it harder to understand what changed, identify the cause of a problem, or test the result.
                      </p>
                    </div>
                  </details>
                ) : (
                  <div className="bounded-practice-why">
                    <h3>Why this matters</h3>
                    <p>
                      One AI request should produce one result that you can inspect. Bundling several features makes it harder to understand what changed, identify the cause of a problem, or test the result.
                    </p>
                  </div>
                )}

                {legacyBoundPrompt && (
                  <div className="notice info bounded-practice-legacy" role="status">
                    <strong>Existing Prompt preserved</strong>
                    <p>
                      This saved Prompt predates scope practice. You can keep editing or saving it without retroactive blocking. Complete this organizer when you want to add the new scope record.
                    </p>
                  </div>
                )}

                <div className="bounded-practice-fields">
                  <div className="field">
                    <label htmlFor="scope-finish-condition">
                      What will exist when this task is done?
                    </label>
                    <p id="scope-finish-hint" className="field-hint">
                      Describe the specific result this AI request should produce.
                    </p>
                    <textarea
                      ref={(node) => {
                        scopeFieldRefs.current.finishCondition = node;
                      }}
                      id="scope-finish-condition"
                      rows={3}
                      value={scope.finishCondition}
                      aria-invalid={Boolean(
                        scopeAttempted && scopeValidation.errors.finishCondition
                      )}
                      aria-describedby={`scope-finish-hint scope-finish-count${
                        scopeAttempted && scopeValidation.errors.finishCondition
                          ? " scope-finish-error"
                          : ""
                      }`}
                      onChange={(event) =>
                        setScopeField("finishCondition", event.target.value)
                      }
                    />
                    {guidanceDepth === "more" && (
                      <p className="muted scope-direction">
                        Keep this to the selected assignment, not the whole project.
                      </p>
                    )}
                    <div className="field-meta">
                      {scopeAttempted && scopeValidation.errors.finishCondition ? (
                        <span id="scope-finish-error" className="field-error" role="alert">
                          {scopeValidation.errors.finishCondition}
                        </span>
                      ) : (
                        <span />
                      )}
                      <span
                        id="scope-finish-count"
                        className={
                          codePointLength(scope.finishCondition.trim()) >
                          SCOPE_PRACTICE_MAX_CODE_POINTS
                            ? "field-count over"
                            : "field-count"
                        }
                      >
                        {codePointLength(scope.finishCondition.trim())}/{SCOPE_PRACTICE_MAX_CODE_POINTS}
                      </span>
                    </div>
                  </div>

                  <div className="field">
                    <label htmlFor="scope-excluded-work">
                      What related work are you leaving out of this request?
                    </label>
                    <p id="scope-excluded-hint" className="field-hint">
                      Name at least one nearby feature, decision, or task that should remain for later.
                    </p>
                    <textarea
                      ref={(node) => {
                        scopeFieldRefs.current.excludedWork = node;
                      }}
                      id="scope-excluded-work"
                      rows={3}
                      value={scope.excludedWork}
                      aria-invalid={Boolean(
                        scopeAttempted && scopeValidation.errors.excludedWork
                      )}
                      aria-describedby={`scope-excluded-hint scope-excluded-count${
                        scopeAttempted && scopeValidation.errors.excludedWork
                          ? " scope-excluded-error"
                          : ""
                      }`}
                      onChange={(event) =>
                        setScopeField("excludedWork", event.target.value)
                      }
                    />
                    {guidanceDepth === "more" && (
                      <p className="muted scope-direction">
                        Pick a real boundary yourself; Codize will not select one for you.
                      </p>
                    )}
                    <div className="field-meta">
                      {scopeAttempted && scopeValidation.errors.excludedWork ? (
                        <span id="scope-excluded-error" className="field-error" role="alert">
                          {scopeValidation.errors.excludedWork}
                        </span>
                      ) : (
                        <span />
                      )}
                      <span
                        id="scope-excluded-count"
                        className={
                          codePointLength(scope.excludedWork.trim()) >
                          SCOPE_PRACTICE_MAX_CODE_POINTS
                            ? "field-count over"
                            : "field-count"
                        }
                      >
                        {codePointLength(scope.excludedWork.trim())}/{SCOPE_PRACTICE_MAX_CODE_POINTS}
                      </span>
                    </div>
                  </div>

                  <div className="field">
                    <label htmlFor="scope-inspection-condition">
                      What observable result will tell you the response is ready to inspect?
                    </label>
                    <p id="scope-inspection-hint" className="field-hint">
                      Describe something you can look for after the AI finishes. This is not the same as proving the entire feature works.
                    </p>
                    <textarea
                      ref={(node) => {
                        scopeFieldRefs.current.inspectionCondition = node;
                      }}
                      id="scope-inspection-condition"
                      rows={3}
                      value={scope.inspectionCondition}
                      aria-invalid={Boolean(
                        scopeAttempted && scopeValidation.errors.inspectionCondition
                      )}
                      aria-describedby={`scope-inspection-hint scope-inspection-count${
                        scopeAttempted && scopeValidation.errors.inspectionCondition
                          ? " scope-inspection-error"
                          : ""
                      }`}
                      onChange={(event) =>
                        setScopeField("inspectionCondition", event.target.value)
                      }
                    />
                    {guidanceDepth === "more" && (
                      <p className="muted scope-direction">
                        Think about a visible structure, route, file, or targeted command result.
                      </p>
                    )}
                    <div className="field-meta">
                      {scopeAttempted && scopeValidation.errors.inspectionCondition ? (
                        <span id="scope-inspection-error" className="field-error" role="alert">
                          {scopeValidation.errors.inspectionCondition}
                        </span>
                      ) : (
                        <span />
                      )}
                      <span
                        id="scope-inspection-count"
                        className={
                          codePointLength(scope.inspectionCondition.trim()) >
                          SCOPE_PRACTICE_MAX_CODE_POINTS
                            ? "field-count over"
                            : "field-count"
                        }
                      >
                        {codePointLength(scope.inspectionCondition.trim())}/{SCOPE_PRACTICE_MAX_CODE_POINTS}
                      </span>
                    </div>
                  </div>
                </div>

                <section
                  className="scope-checklist"
                  aria-labelledby="scope-checklist-title"
                >
                  <div className="spread">
                    <h3 id="scope-checklist-title">Scope checklist</h3>
                    <p className="scope-checklist-status" role="status" aria-live="polite">
                      {scopeValidation.complete
                        ? "Scope checklist complete"
                        : `${Object.keys(scopeValidation.errors).length} planning ${
                            Object.keys(scopeValidation.errors).length === 1
                              ? "piece is"
                              : "pieces are"
                          } still missing`}
                    </p>
                  </div>
                  <ul>
                    <ScopeChecklistItem complete>
                      This Prompt is connected to the selected assignment
                    </ScopeChecklistItem>
                    <ScopeChecklistItem
                      complete={!scopeValidation.errors.finishCondition}
                    >
                      You described what should exist afterward
                    </ScopeChecklistItem>
                    <ScopeChecklistItem
                      complete={!scopeValidation.errors.excludedWork}
                    >
                      You named related work that remains outside this request
                    </ScopeChecklistItem>
                    <ScopeChecklistItem
                      complete={!scopeValidation.errors.inspectionCondition}
                    >
                      You described what you will inspect afterward
                    </ScopeChecklistItem>
                  </ul>
                  <p className="muted scope-checklist-boundary">
                    This checks only that the required planning pieces are present. It does not score correctness or prove the request is well scoped.
                  </p>
                </section>

                <div className="scope-apply">
                  <div>
                    <h3>Use these decisions in the editable Prompt</h3>
                    <p className="muted">
                      This adds the selected assignment plus your finish and inspection conditions to Task, and excluded work to Don&rsquo;t touch. Context stays exactly as written. Nothing is saved automatically.
                    </p>
                  </div>
                  <button
                    id="apply-scope-to-prompt"
                    ref={applyTriggerRef}
                    className="btn primary"
                    type="button"
                    onClick={() => applyScopeToPrompt(false)}
                  >
                    {scopeAppliedCurrent
                      ? "Reapply this scope"
                      : "Apply this scope to my Prompt"}
                  </button>
                </div>

                {applyConflict && (
                  <div
                    ref={conflictRef}
                    className="notice warn scope-apply-conflict"
                    role="alertdialog"
                    aria-labelledby="scope-conflict-title"
                    aria-describedby="scope-conflict-description"
                    tabIndex={-1}
                  >
                    <strong id="scope-conflict-title">Replace existing Prompt text?</strong>
                    <p id="scope-conflict-description">
                      {applyConflict.task && applyConflict.guardrail
                        ? "Task and Don’t touch already contain text."
                        : applyConflict.task
                          ? "Task already contains text."
                          : "Don’t touch already contains text."}{" "}
                      Applying replaces only those fields with your current scope decisions. Context and other Guardrails stay unchanged.
                    </p>
                    <div className="row">
                      <button className="btn" type="button" onClick={cancelApplyConflict}>
                        Keep existing text
                      </button>
                      <button className="btn primary" type="button" onClick={() => applyScopeToPrompt(true)}>
                        Replace and apply scope
                      </button>
                    </div>
                  </div>
                )}

                {scopeAppliedCurrent && (
                  <p className="notice ok scope-applied-status" role="status">
                    Scope applied to the editable Prompt fields. Review the final Prompt before using it with your AI tool; nothing has been saved or marked complete.
                  </p>
                )}
                {scopeValidation.complete && !scopeAppliedCurrent && !applyConflict && (
                  <p className="notice info" role="status">
                    Your scope checklist includes the required planning pieces. Apply them to the Prompt fields before building the final preview.
                  </p>
                )}
              </section>
            )}

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
            {promptChangedAfterApply && (
              <div className="notice info prompt-scope-mismatch" role="status">
                You edited Task or Don&rsquo;t touch after applying scope. Your edits are preserved. Reapply only if you want those fields replaced with the current scope decisions.
              </div>
            )}
            <div className="card prompt-fields-card">
              <label className="prompt-task-label" htmlFor="prompt-ai-task">Step 1 — Task (editable)</label>
              <textarea
                ref={taskFieldRef}
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
              <button className="btn primary" type="button" onClick={generate}>
                Build the prompt
              </button>
              {finalScopeMustBeReady && !scopeAppliedCurrent ? (
                <span className="muted">Complete and apply the scope organizer first.</span>
              ) : !inputs.aiTask.trim() ? (
                <span className="muted">Add one Task before building the preview.</span>
              ) : (
                <span className="muted">Review remains yours before save or handoff.</span>
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
                  <h3>What this structure includes</h3>
                  <p>{built.whyStronger}</p>
                  <hr className="rule" />
                  <p className="muted">
                    Compare with what usually goes wrong:{" "}
                    <span className="mono">&ldquo;{built.badPrompt}&rdquo;</span> — it does not state
                    the same boundary or inspection plan. Review your final wording before using it.
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
                Before you ask your AI tool for code, record one assignment boundary and review
                the editable request Codize assembles from your own decisions.
              </p>
            </GuideCard>
            <GuideCard title="What the organizer checks">
              <ul>
                <li>A finish condition is present.</li>
                <li>Excluded work is present.</li>
                <li>An inspection condition is present.</li>
              </ul>
              <p>It does not judge whether the wording is correct.</p>
            </GuideCard>
            <GuideCard
              title="Broad versus bounded example"
              defaultOpen={guidanceDepth === "more"}
            >
              <p className="muted">Another project: a habit tracker</p>
              <dl className="contrast-example">
                <div>
                  <dt>Broad</dt>
                  <dd>Build the tracker, add accounts, reminders, analytics, and deploy it.</dd>
                </div>
                <div>
                  <dt>Bounded</dt>
                  <dd>Create the basic habit-entry form without accounts, reminders, analytics, or deployment.</dd>
                </div>
              </dl>
            </GuideCard>
            <GuideCard title="Prompt fields remain yours">
              <p>
                Applying scope changes only Task and Don&rsquo;t touch. Context, other Guardrails,
                final edits, and the decision to save remain yours.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}

function ScopeChecklistItem({
  complete,
  children,
}: {
  complete: boolean;
  children: ReactNode;
}) {
  return (
    <li className={complete ? "complete" : "incomplete"}>
      <span aria-hidden="true">{complete ? "✓" : "○"}</span>
      <span>{complete ? "Present: " : "Missing: "}{children}</span>
    </li>
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
