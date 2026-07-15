"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import Async from "@/components/Async";
import AdaptiveStepGuide from "@/components/AdaptiveStepGuide";
import { GuidedContinueAction } from "@/components/GuidedProjectNav";
import GuideCard from "@/components/GuideCard";
import LinkedVerificationTargetRow from "@/components/LinkedVerificationTarget";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { ApiError, initializeVerificationFromReview } from "@/lib/api";
import { containsSecretMarker, useDraft } from "@/lib/drafts";
import { useWorkflowSection } from "@/lib/useWorkflowSection";
import {
  VERIFICATION_HONESTY_LINE,
  VERIFICATION_PAGE_INTRO,
  VERIFICATION_PAGE_TITLE,
  canReplaceVerificationFromReview,
  deriveVerificationSavePayload,
  groupVerificationTargets,
  isLinkedVerificationArtifact,
  isLinkedVerificationDirty,
  isZeroTargetVerification,
  linkedVerificationDraftSurface,
  linkedVerificationDraftValue,
  linkedVerificationProgress,
  linkedVerificationRecorded,
  linkedVerificationResultSummary,
  linkedVerificationServerRevision,
  restoreLinkedVerificationDraft,
  shouldKeepVerificationSaveNotice,
  showFullVerificationInitializationState,
  targetFormFromVerification,
  verificationArtifactMode,
  verificationCategoryLabel,
  verificationFormBlocker,
  verificationPrerequisiteState,
  verificationResultLabel,
  type LinkedVerificationDraft,
  type LinkedVerificationFormState,
} from "@/lib/verification";
import type {
  LinkedVerificationArtifact,
  PhaseView,
  StoredReviewBoardArtifact,
  StoredVerificationArtifact,
  VerificationArtifact,
  VerificationCheckId,
  VerificationResult,
  VerificationSaveRequest,
} from "@/lib/types";

const MANUAL_CHECKS: {
  id: VerificationCheckId;
  label: string;
  whenRelevant?: boolean;
}[] = [
  { id: "app_runs_locally", label: "The app runs locally" },
  { id: "smoke_test", label: "Ran at least one smoke test" },
  { id: "api_route_checked", label: "The relevant API route responds correctly" },
  { id: "ui_flow_checked", label: "The relevant UI flow works" },
  { id: "failure_case_tested", label: "Tested at least one failure case" },
  { id: "auth_boundary_checked", label: "Auth boundary checked", whenRelevant: true },
  { id: "secret_exposure_checked", label: "No secrets exposed in frontend/repo" },
  { id: "rls_wrong_user_checked", label: "Wrong-user access blocked (RLS)", whenRelevant: true },
];

const MANUAL_RESULTS: { value: VerificationResult; label: string }[] = [
  { value: "pass", label: "pass" },
  { value: "fail", label: "fail" },
  { value: "skipped", label: "skipped" },
  { value: "not_applicable", label: "n/a" },
];

const MANUAL_NOTE_PROMPTS: Record<
  VerificationResult,
  { label: string; placeholder: string }
> = {
  pass: {
    label: "How did you check it?",
    placeholder: "e.g. curl POST /tasks with a missing title → 422",
  },
  fail: {
    label: "What failed, or what needs fixing?",
    placeholder: "e.g. the route 500s when title is missing — needs validation",
  },
  skipped: {
    label: "Why are you skipping it for now? (optional)",
    placeholder: "e.g. will check this after the next feature lands",
  },
  not_applicable: {
    label: "Why doesn't this apply? (optional)",
    placeholder: "e.g. this phase has no UI yet",
  },
};

type ManualCheckState = { result: VerificationResult | ""; note: string };

function ReplacementWarning({
  busy,
  error,
  onConfirm,
  onCancel,
}: {
  busy: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      className="replacement-warning"
      role="group"
      aria-labelledby="verification-rebuild-title"
    >
      <strong id="verification-rebuild-title">Replace this Verification?</strong>
      <p>
        Rebuilding replaces the current Verification targets, edited checks, results, and notes
        with a fresh draft from the latest Review.
      </p>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      <div className="row">
        <button className="btn primary" type="button" disabled={busy} onClick={onConfirm}>
          {busy ? "Preparing…" : "Yes, rebuild Verification"}
        </button>
        <button className="btn" type="button" disabled={busy} onClick={onCancel}>
          Keep current Verification
        </button>
      </div>
    </div>
  );
}

function VerificationPrerequisite({
  review,
  phase,
  error,
  initializing,
  onStart,
}: {
  review: StoredReviewBoardArtifact | null;
  phase: PhaseView | null;
  error: string | null;
  initializing: boolean;
  onStart: () => void;
}) {
  const state = verificationPrerequisiteState(review);
  const content = {
    no_review: {
      title: "Complete Review first",
      body: "Decide what to keep, revise, remove, or test before starting Verification.",
      action: "Go to Review",
    },
    incomplete_review: {
      title: "Finish reviewing every implementation item",
      body: "Save a decision for each Review item before creating Verification checks.",
      action: "Continue Review",
    },
    stale_review: {
      title: "Update Review first",
      body: "The Change Map changed after this Review was created.",
      action: "Rebuild Review",
    },
    ready: {
      title: "Create Verification checks from Review",
      body: "Codize will carry over only the Review items you marked as needing testing. You will perform each check and record the result.",
      action: "Start Verification",
    },
  }[state];

  return (
    <>
      <h1 className="page-title">{VERIFICATION_PAGE_TITLE}</h1>
      <p className="page-sub">Test implementation choices before continuing.</p>
      <AdaptiveStepGuide stage="verification" />
      <div className="workspace">
        <div>
          {phase && (
            <p className="muted verification-phase-line">
              Phase {phase.phase}: {phase.phase_title}
            </p>
          )}
          <div className="card primary verification-empty">
            <h2>{content.title}</h2>
            <p>{content.body}</p>
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            {state === "ready" ? (
              <button
                className="btn primary"
                type="button"
                disabled={initializing}
                onClick={onStart}
              >
                {initializing ? "Preparing…" : content.action}
              </button>
            ) : (
              <Link className="btn primary" href="/app/phase/review">
                {content.action}
              </Link>
            )}
            {state === "ready" && (
              <details className="help verification-carry-over">
                <summary>What will carry over?</summary>
                <div className="help-body">
                  <p>
                    The reviewed implementation item, the reason you marked it for testing when
                    recorded, and one grounded suggested check. No result is selected for you.
                  </p>
                </div>
              </details>
            )}
          </div>
        </div>
        <aside className="ws-rail" aria-label="Guidance">
          <GuideCard title="Review versus Verification">
            <p>
              Review records “I need to test this.” Verification records the check you perform and
              what actually happens.
            </p>
          </GuideCard>
          <GuideCard title="Already in a patch loop?">
            <p>Record what actually happens before asking AI for another patch.</p>
          </GuideCard>
        </aside>
      </div>
    </>
  );
}

function LegacyVerificationLab({
  artifact,
  phase,
  saving,
  saveError,
  savedAt,
  replacementError,
  initializing,
  replacementReady,
  onSave,
  onReplace,
}: {
  artifact: VerificationArtifact;
  phase: PhaseView;
  saving: boolean;
  saveError: string | null;
  savedAt: string | null;
  replacementError: string | null;
  initializing: boolean;
  replacementReady: boolean;
  onSave: (payload: VerificationSaveRequest) => Promise<StoredVerificationArtifact | null>;
  onReplace: () => Promise<boolean>;
}) {
  const [state, setState] = useState<Record<VerificationCheckId, ManualCheckState>>(
    Object.fromEntries(
      MANUAL_CHECKS.map((check) => [check.id, { result: "", note: "" }])
    ) as Record<VerificationCheckId, ManualCheckState>
  );
  const [explanation, setExplanation] = useState("");
  const [replaceOpen, setReplaceOpen] = useState(false);

  useEffect(() => {
    setState((previous) => {
      const next = { ...previous };
      for (const check of artifact.checks ?? []) {
        next[check.check] = { result: check.result, note: check.note ?? "" };
      }
      return next;
    });
    setExplanation(artifact.explanation ?? "");
  }, [artifact]);

  type ManualVerificationDraft = {
    state: Record<VerificationCheckId, ManualCheckState>;
    explanation: string;
  };
  const draft = useDraft<ManualVerificationDraft>(`verification:${phase.phase}`);
  const draftApplied = useRef(false);
  useEffect(() => {
    if (!draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) {
      setState((previous) => ({ ...previous, ...draft.restored?.state }));
      setExplanation(draft.restored.explanation ?? "");
    }
  }, [draft.ready, draft.restored]);
  const skipDraftEcho = useRef(false);
  const saveDraft = draft.save;
  useEffect(() => {
    if (!draftApplied.current) return;
    if (skipDraftEcho.current) {
      skipDraftEcho.current = false;
      return;
    }
    saveDraft({ state, explanation });
  }, [state, explanation, saveDraft]);

  async function save() {
    const checks = MANUAL_CHECKS.filter((check) => state[check.id].result !== "").map(
      (check) => ({
        check: check.id,
        result: state[check.id].result as VerificationResult,
        note: state[check.id].note.trim() ? state[check.id].note.slice(0, 2000) : null,
      })
    );
    const result = await onSave({
      checks,
      explanation: explanation.trim() ? explanation.slice(0, 2000) : null,
    });
    if (result) {
      skipDraftEcho.current = true;
      draft.clear();
    }
  }

  async function replace() {
    if (await onReplace()) draft.clear();
  }

  const recorded = MANUAL_CHECKS.filter((check) => state[check.id].result !== "").length;

  return (
    <>
      <h1 className="page-title">Verification</h1>
      <p className="page-sub">
        A quick honesty check, not homework — mark what you actually tried. It lands in your
        Defense Report.
      </p>
      <AdaptiveStepGuide stage="verification" />
      <div className="workspace">
        <div>
          <p className="muted" style={{ marginBottom: 14 }}>
            Phase {phase.phase}: {phase.phase_title} · {recorded}/{MANUAL_CHECKS.length} recorded ·
            you can save any time and come back later
          </p>
          <div className="card primary">
            <h3>Checks</h3>
            {MANUAL_CHECKS.map((check) => (
              <div
                key={check.id}
                style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}
              >
                <div className="spread">
                  <span>
                    {check.label}
                    {check.whenRelevant && <span className="muted"> (when relevant)</span>}
                  </span>
                  <div className="row">
                    {MANUAL_RESULTS.map((result) => (
                      <button
                        key={result.value}
                        className={`btn small${state[check.id].result === result.value ? " primary" : ""}`}
                        onClick={() =>
                          setState((previous) => ({
                            ...previous,
                            [check.id]: {
                              ...previous[check.id],
                              result:
                                previous[check.id].result === result.value ? "" : result.value,
                            },
                          }))
                        }
                      >
                        {result.label}
                      </button>
                    ))}
                  </div>
                </div>
                {state[check.id].result !== "" && (
                  <div style={{ marginTop: 8 }}>
                    <p className="hint" style={{ margin: "0 0 4px" }}>
                      {MANUAL_NOTE_PROMPTS[state[check.id].result as VerificationResult].label}
                    </p>
                    <input
                      type="text"
                      maxLength={2000}
                      value={state[check.id].note}
                      onChange={(event) =>
                        setState((previous) => ({
                          ...previous,
                          [check.id]: { ...previous[check.id], note: event.target.value },
                        }))
                      }
                      placeholder={
                        MANUAL_NOTE_PROMPTS[state[check.id].result as VerificationResult]
                          .placeholder
                      }
                    />
                    {(state[check.id].result === "skipped" ||
                      state[check.id].result === "not_applicable") && (
                      <p className="hint" style={{ margin: "4px 0 0" }}>
                        {state[check.id].result === "skipped"
                          ? "Recorded as “skipped for now” — no evidence needed."
                          : "Recorded as “doesn't apply” — no evidence needed."}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="card">
            <h3>What does this verification prove?</h3>
            <textarea
              rows={3}
              maxLength={2000}
              value={explanation}
              onChange={(event) => setExplanation(event.target.value)}
              placeholder="In your own words: what do these checks demonstrate, and what's still unproven?"
            />
          </div>
          <SaveBar
            saving={saving}
            saveError={saveError}
            savedAt={savedAt}
            onSave={() => void save()}
            label="Save verification"
          />

          {replacementReady && (
            <details className="help more-options">
              <summary>More options</summary>
              <div className="help-body">
                <p>Starting from Review will replace the current Verification work for this phase.</p>
                {!replaceOpen ? (
                  <button className="btn" type="button" onClick={() => setReplaceOpen(true)}>
                    Start over from Review
                  </button>
                ) : (
                  <ReplacementWarning
                    busy={initializing}
                    error={replacementError}
                    onConfirm={() => void replace()}
                    onCancel={() => setReplaceOpen(false)}
                  />
                )}
              </div>
            </details>
          )}
        </div>
        <aside className="ws-rail" aria-label="Guidance">
          <GuideCard title="Existing Verification preserved">
            <p>
              This phase uses the original manual Verification format. Codize will not convert or
              replace it unless you deliberately start over from Review.
            </p>
          </GuideCard>
          <GuideCard title="What the four results mean">
            <ul>
              <li><strong>pass</strong> — you checked it and it worked. Say how.</li>
              <li><strong>fail</strong> — you checked it and it didn’t. Say what broke.</li>
              <li><strong>skipped</strong> — not checked yet. That’s allowed.</li>
              <li><strong>n/a</strong> — doesn’t apply to this phase.</li>
            </ul>
          </GuideCard>
          <GuideCard title="Your text is kept">
            <p>
              Results and notes survive switching tabs as a local draft. Save verification to
              store them to your project.
            </p>
          </GuideCard>
        </aside>
      </div>
    </>
  );
}

function LinkedVerificationBoard({
  verification,
  phase,
  review,
  saving,
  saveError,
  replacementError,
  initializing,
  onSave,
  onReplace,
}: {
  verification: LinkedVerificationArtifact;
  phase: PhaseView;
  review: StoredReviewBoardArtifact | null;
  saving: boolean;
  saveError: string | null;
  replacementError: string | null;
  initializing: boolean;
  onSave: (payload: VerificationSaveRequest) => Promise<StoredVerificationArtifact | null>;
  onReplace: () => Promise<boolean>;
}) {
  const [form, setForm] = useState<LinkedVerificationFormState>(() =>
    targetFormFromVerification(verification)
  );
  const [justSaved, setJustSaved] = useState(false);
  const [replaceOpen, setReplaceOpen] = useState(false);
  const [resultAnnouncement, setResultAnnouncement] = useState("");
  const acknowledgedSaveRevision = useRef<string | null>(null);
  const verificationRef = useRef(verification);
  verificationRef.current = verification;
  const serverRevision = linkedVerificationServerRevision(verification);

  useEffect(() => {
    setForm(targetFormFromVerification(verificationRef.current));
    if (shouldKeepVerificationSaveNotice(acknowledgedSaveRevision.current, serverRevision)) {
      acknowledgedSaveRevision.current = null;
    } else {
      setJustSaved(false);
    }
    setReplaceOpen(false);
  }, [serverRevision]);

  const draftSurface = linkedVerificationDraftSurface(phase.phase, verification);
  const draft = useDraft<LinkedVerificationDraft>(draftSurface);
  const draftAppliedFor = useRef<string | null>(null);
  useEffect(() => {
    if (
      !draft.ready ||
      draft.loadedSurface !== draftSurface ||
      draftAppliedFor.current === draftSurface
    ) {
      return;
    }
    draftAppliedFor.current = draftSurface;
    const restored = restoreLinkedVerificationDraft(verification, draft.restored);
    if (restored && isLinkedVerificationDirty(verification, restored)) setForm(restored);
    else if (draft.restored) draft.clear();
  }, [draft, draftSurface, verification]);

  const dirty = useMemo(
    () => isLinkedVerificationDirty(verification, form),
    [form, verification]
  );
  const blocker = useMemo(
    () => verificationFormBlocker(verification, form),
    [form, verification]
  );
  const progress = useMemo(
    () => linkedVerificationProgress(verification, form),
    [form, verification]
  );
  const summary = useMemo(
    () => linkedVerificationResultSummary(verification, form),
    [form, verification]
  );
  const recorded = useMemo(
    () => linkedVerificationRecorded(verification, form),
    [form, verification]
  );
  const draftBlocked = dirty && containsSecretMarker(JSON.stringify(form));
  const saveLocalDraft = draft.save;
  useEffect(() => {
    if (draftAppliedFor.current !== draftSurface || verification.stale) return;
    if (dirty) saveLocalDraft(linkedVerificationDraftValue(verification, form));
  }, [dirty, draftSurface, form, saveLocalDraft, verification]);

  async function save() {
    if (!dirty || blocker || verification.stale || draftBlocked) return;
    const result = await onSave(deriveVerificationSavePayload(verification, form));
    if (result && isLinkedVerificationArtifact(result)) {
      acknowledgedSaveRevision.current = linkedVerificationServerRevision(result);
      draft.clear();
      setForm(targetFormFromVerification(result));
      setJustSaved(true);
    }
  }

  async function replace() {
    if (await onReplace()) draft.clear();
  }

  const groups = groupVerificationTargets(verification.verification_targets);
  const replacementReady = canReplaceVerificationFromReview(review);
  const zeroTargets = isZeroTargetVerification(verification);

  return (
    <>
      <h1 className="page-title">{VERIFICATION_PAGE_TITLE}</h1>
      <p className="page-sub">{VERIFICATION_PAGE_INTRO}</p>
      <p className="verification-honesty">{VERIFICATION_HONESTY_LINE}</p>
      <AdaptiveStepGuide stage="verification" />

      <div className="workspace">
        <div>
          <p className="muted verification-phase-line">
            Phase {phase.phase}: {phase.phase_title}
          </p>

          {verification.stale && (
            <div className="notice info stale-notice" role="status">
              <strong>Review changed after these Verification checks were created.</strong>
              <p>Rebuild Verification to use the latest saved Review decisions.</p>
              {replacementReady ? (
                !replaceOpen ? (
                  <button
                    className="btn primary"
                    type="button"
                    onClick={() => setReplaceOpen(true)}
                  >
                    Rebuild Verification from current Review
                  </button>
                ) : (
                  <ReplacementWarning
                    busy={initializing}
                    error={replacementError}
                    onConfirm={() => void replace()}
                    onCancel={() => setReplaceOpen(false)}
                  />
                )
              ) : (
                <Link className="btn primary" href="/app/phase/review">
                  Update Review first
                </Link>
              )}
            </div>
          )}

          <section
            className="card primary linked-verification-surface"
            aria-labelledby="linked-verification-heading"
          >
            <div className="linked-verification-summary">
              <div>
                <span className={`pill ${verification.stale ? "warn" : "accent"}`}>
                  {verification.stale ? "Needs rebuild" : "Current Verification"}
                </span>
                <h2 id="linked-verification-heading">Verification</h2>
                <p>Created from the Review items you marked as needing testing.</p>
              </div>
              {!zeroTargets && (
                <strong>
                  {progress.recorded} of {progress.total} checks recorded
                </strong>
              )}
            </div>
            <p className="verification-source-statement">
              Codize suggested the checks. You perform them and record what happened.
            </p>

            {!zeroTargets && (
              <div
                className="review-meter verification-meter"
                role="progressbar"
                aria-label="Verification checks recorded"
                aria-valuemin={0}
                aria-valuemax={progress.total}
                aria-valuenow={progress.recorded}
                aria-valuetext={`${progress.recorded} of ${progress.total} checks recorded`}
              >
                <span style={{ width: `${(progress.recorded / progress.total) * 100}%` }} />
              </div>
            )}

            {zeroTargets ? (
              <div className="verification-zero-targets">
                <h3>No Review items are currently marked as needing testing.</h3>
                <p>
                  Verification suggestions are created only from Review items you marked “Needs
                  testing.”
                </p>
                <div className="row">
                  <Link className="btn" href="/app/phase/review">
                    Review your decisions
                  </Link>
                  <GuidedContinueAction className="btn primary" />
                </div>
              </div>
            ) : (
              <>
                {summary.recorded > 0 && (
                  <dl className="verification-result-summary" aria-label="Recorded result summary">
                    <div><dt>Recorded</dt><dd>{summary.recorded}</dd></div>
                    <div><dt>Passed</dt><dd>{summary.passed}</dd></div>
                    <div><dt>Failed</dt><dd>{summary.failed}</dd></div>
                    <div><dt>Skipped</dt><dd>{summary.skipped}</dd></div>
                    <div><dt>Not applicable</dt><dd>{summary.notApplicable}</dd></div>
                    <div><dt>Unperformed</dt><dd>{summary.unperformed}</dd></div>
                  </dl>
                )}

                <div className="linked-verification-groups">
                  {groups.map((group) => (
                    <section className="linked-verification-group" key={group.category}>
                      <div className="category-heading">
                        <h3>
                          {verificationCategoryLabel(group.category)} <span>({group.targets.length})</span>
                        </h3>
                      </div>
                      {group.targets.map((target) => {
                        const targetIndex = verification.verification_targets.indexOf(target);
                        const targetForm = form[target.verification_target_id];
                        if (!targetForm) return null;
                        return (
                          <LinkedVerificationTargetRow
                            key={target.verification_target_id}
                            target={target}
                            index={targetIndex}
                            form={targetForm}
                            disabled={verification.stale || saving}
                            onChange={(patch) => {
                              setForm((current) => ({
                                ...current,
                                [target.verification_target_id]: {
                                  ...current[target.verification_target_id],
                                  ...patch,
                                },
                              }));
                              if (Object.prototype.hasOwnProperty.call(patch, "result")) {
                                setResultAnnouncement(
                                  patch.result == null
                                    ? "Result returned to not recorded yet."
                                    : `${verificationResultLabel(patch.result)} recorded for this check.`
                                );
                              }
                              setJustSaved(false);
                            }}
                          />
                        );
                      })}
                    </section>
                  ))}
                </div>
              </>
            )}

            {draftBlocked && (
              <div className="notice error" role="alert">
                This draft looks like it contains a secret. Remove the key-like text before saving;
                Codize is not keeping this draft on this device.
              </div>
            )}
            {blocker && dirty && <p className="field-error">{blocker}</p>}
            {dirty && !verification.stale && (
              <SaveBar
                saving={saving}
                saveError={saveError}
                savedAt={null}
                onSave={() => void save()}
                label="Save Verification"
                disabled={Boolean(blocker) || draftBlocked}
              />
            )}
            {!dirty && saveError && (
              <div className="notice error" role="alert">
                {saveError}
              </div>
            )}
            {justSaved && (
              <div className="notice ok" role="status">
                <strong>Verification saved.</strong>
              </div>
            )}

            {!zeroTargets && !verification.stale && !dirty && recorded && (
              <div className="verification-complete" role="status">
                <strong>Verification results recorded</strong>
                <p>
                  You recorded an outcome for every suggested check. Failures, skipped checks, and
                  not-applicable items remain part of the project record.
                </p>
                <GuidedContinueAction className="btn primary" />
              </div>
            )}
          </section>

          {!verification.stale && (
            <details className="help more-options">
              <summary>More options</summary>
              <div className="help-body">
                <p>Rebuild only when you deliberately want fresh checks from the current Review.</p>
                {!replacementReady ? (
                  <Link href="/app/phase/review">Finish the current Review first</Link>
                ) : !replaceOpen ? (
                  <button className="btn" type="button" onClick={() => setReplaceOpen(true)}>
                    Rebuild from Review
                  </button>
                ) : (
                  <ReplacementWarning
                    busy={initializing}
                    error={replacementError}
                    onConfirm={() => void replace()}
                    onCancel={() => setReplaceOpen(false)}
                  />
                )}
              </div>
            </details>
          )}
        </div>

        <aside className="ws-rail" aria-label="Guidance">
          <GuideCard title="Suggestion versus result">
            <p>
              A suggestion is a grounded starting point. Your result is the outcome you record only
              after performing the check outside Codize.
            </p>
          </GuideCard>
          <GuideCard title="Honest outcomes stay visible">
            <p>
              Failed, skipped, and not-applicable checks all count as recorded outcomes, but none is
              relabeled as passed. A pass applies only to that check.
            </p>
          </GuideCard>
          <GuideCard title="Your draft is scoped">
            <p>
              Unsaved check wording and results stay on this device for your account, active
              project, phase, and exact linked Verification. Saving reconciles the draft with the
              server record.
            </p>
          </GuideCard>
          <GuideCard title="Already in a patch loop?">
            <p>Record what actually happens before asking AI for another patch.</p>
          </GuideCard>
        </aside>
      </div>

      <p className="sr-only" role="status" aria-live="polite">
        {saving
          ? "Saving Verification."
          : resultAnnouncement || (recorded && !dirty ? "Verification results recorded." : "")}
      </p>
    </>
  );
}

export default function VerificationLabPage() {
  const wf = useWorkflowSection("verification");
  const [initializing, setInitializing] = useState(false);
  const [initializationError, setInitializationError] = useState<string | null>(null);
  const review = wf.sections?.review_board ?? null;

  if (wf.notReady) return <NotReady title="Test What You Changed" />;

  async function initialize(replaceExisting: boolean): Promise<boolean> {
    if (!wf.phase || initializing) return false;
    setInitializing(true);
    setInitializationError(null);
    try {
      const result = await initializeVerificationFromReview(wf.phase.phase, replaceExisting);
      wf.applyArtifact(result.artifact);
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409 && !replaceExisting) {
        await wf.reload();
      } else {
        setInitializationError(
          error instanceof ApiError
            ? error.message
            : "Couldn’t prepare these Verification checks. Try again."
        );
      }
      return false;
    } finally {
      setInitializing(false);
    }
  }

  if (showFullVerificationInitializationState(initializing, Boolean(wf.stored))) {
    return (
      <>
        <h1 className="page-title">{VERIFICATION_PAGE_TITLE}</h1>
        <p className="page-sub">Test implementation choices before continuing.</p>
        <div
          className="card primary verification-initializing"
          role="status"
          aria-live="polite"
        >
          <h2>Preparing your Verification checks…</h2>
          <p>Codize is carrying over the Review items you marked as needing testing.</p>
        </div>
      </>
    );
  }

  return (
    <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
      {wf.phase && (() => {
        const mode = verificationArtifactMode(wf.stored);
        if (mode === "linked" && isLinkedVerificationArtifact(wf.stored)) {
          return (
            <LinkedVerificationBoard
              verification={wf.stored}
              phase={wf.phase}
              review={review}
              saving={wf.saving}
              saveError={wf.saveError}
              replacementError={initializationError}
              initializing={initializing}
              onSave={wf.save}
              onReplace={() => initialize(true)}
            />
          );
        }
        if (mode === "legacy" && wf.stored) {
          return (
            <LegacyVerificationLab
              artifact={wf.stored}
              phase={wf.phase}
              saving={wf.saving}
              saveError={wf.saveError}
              savedAt={wf.savedAt}
              replacementError={initializationError}
              initializing={initializing}
              replacementReady={canReplaceVerificationFromReview(review)}
              onSave={wf.save}
              onReplace={() => initialize(true)}
            />
          );
        }
        return (
          <VerificationPrerequisite
            review={review}
            phase={wf.phase}
            error={initializationError}
            initializing={initializing}
            onStart={() => void initialize(false)}
          />
        );
      })()}
    </Async>
  );
}
