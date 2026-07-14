"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import LinkedReviewTargetRow from "@/components/LinkedReviewTarget";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { ApiError, initializeReviewFromChangeMap } from "@/lib/api";
import { containsSecretMarker, useDraft } from "@/lib/drafts";
import {
  REVIEW_HONESTY_LINE,
  REVIEW_PAGE_INTRO,
  REVIEW_PAGE_TITLE,
  canReplaceReviewFromMap,
  deriveReviewSavePayload,
  groupReviewTargets,
  isLinkedReviewArtifact,
  isLinkedReviewDirty,
  linkedReviewAllowsVerification,
  linkedReviewComplete,
  linkedReviewDraftSurface,
  linkedReviewDraftValue,
  linkedReviewProgress,
  linkedReviewServerRevision,
  restoreLinkedReviewDraft,
  reviewArtifactMode,
  reviewCategoryLabel,
  reviewFormBlocker,
  reviewPrerequisiteState,
  showFullReviewInitializationState,
  targetFormFromReview,
  type LinkedReviewDraft,
  type LinkedReviewFormState,
} from "@/lib/review";
import type {
  LinkedReviewBoardArtifact,
  PhaseView,
  ReviewBoardArtifact,
  ReviewBoardSaveRequest,
  StoredChangeMap,
  StoredReviewBoardArtifact,
} from "@/lib/types";
import { useWorkflowSection } from "@/lib/useWorkflowSection";

const MANUAL_FIELDS: { key: ManualFieldKey; label: string; placeholder: string }[] = [
  { key: "ai_generated", label: "What did the AI generate?", placeholder: "the POST /tasks route and the Task model" },
  { key: "accepted", label: "What did you accept?", placeholder: "the route handler, mostly as-is" },
  { key: "rejected", label: "What did you reject?", placeholder: "an unrequested rewrite of the auth middleware" },
  { key: "edited_manually", label: "What did you edit manually?", placeholder: "renamed fields, tightened the validation" },
  { key: "ai_assumptions", label: "What assumptions did the AI make?", placeholder: "it assumed every task has a due date" },
  { key: "least_confident", label: "What are you least confident about?", placeholder: "the query in list_tasks — I couldn't fully trace it" },
  { key: "out_of_scope_changes", label: "Did the AI change anything outside the requested scope?", placeholder: "it reformatted imports across three files" },
];

type ManualFieldKey =
  | "ai_generated"
  | "accepted"
  | "rejected"
  | "edited_manually"
  | "ai_assumptions"
  | "least_confident"
  | "out_of_scope_changes";

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
    <div className="replacement-warning" role="group" aria-labelledby="review-rebuild-title">
      <strong id="review-rebuild-title">Replace this Review?</strong>
      <p>
        Rebuilding replaces the current Review targets and decisions with a fresh draft from the
        latest confirmed Change Map.
      </p>
      {error && <div className="notice error" role="alert">{error}</div>}
      <div className="row">
        <button className="btn primary" type="button" disabled={busy} onClick={onConfirm}>
          {busy ? "Preparing…" : "Yes, rebuild Review"}
        </button>
        <button className="btn" type="button" disabled={busy} onClick={onCancel}>
          Keep current Review
        </button>
      </div>
    </div>
  );
}

function ReviewPrerequisite({
  map,
  phase,
  error,
  onStart,
}: {
  map: StoredChangeMap | null;
  phase: PhaseView | null;
  error: string | null;
  onStart: () => void;
}) {
  const state = reviewPrerequisiteState(map);
  const content = {
    missing_change_map: {
      title: "Create a Change Map first",
      body: "Review what appears to have changed before deciding what to keep, revise, remove, or test.",
      action: "Go to Change Map",
    },
    draft_change_map: {
      title: "Finish reviewing your Change Map first",
      body: "Confirm the Change Map before starting implementation Review.",
      action: "Continue Change Map review",
    },
    stale_change_map: {
      title: "Update your Change Map first",
      body: "Your implementation material changed after the Change Map was created.",
      action: "Regenerate Change Map",
    },
    ready: {
      title: "Start Review from your Change Map",
      body: "Codize will carry over the implementation-relevant items you reviewed. You make every decision about what happens next.",
      action: "Start Review",
    },
  }[state];

  return (
    <>
      <h1 className="page-title">{REVIEW_PAGE_TITLE}</h1>
      <p className="page-sub">Review implementation choices before continuing.</p>
      <div className="workspace">
        <div>
          {phase && (
            <p className="muted review-phase-line">
              Phase {phase.phase}: {phase.phase_title}
            </p>
          )}
          <div className="card primary review-empty">
            <h2>{content.title}</h2>
            <p>{content.body}</p>
            {error && <div className="notice error" role="alert">{error}</div>}
            {state === "ready" ? (
              <button className="btn primary" type="button" onClick={onStart}>
                {content.action}
              </button>
            ) : (
              <Link className="btn primary" href="/app/phase/change-map">
                {content.action}
              </Link>
            )}
            {state === "ready" && (
              <details className="help review-carry-over">
                <summary>What will carry over?</summary>
                <div className="help-body">
                  <p>
                    Implementation-relevant behavior changes, decisions, possible out-of-scope
                    changes, sensitive areas, unresolved risks, and behavior still needing testing.
                    Not every Change Map category becomes a Review target.
                  </p>
                </div>
              </details>
            )}
          </div>
        </div>
        <aside className="ws-rail" aria-label="Guidance">
          <GuideCard title="Change Map versus Review">
            <p>
              The Change Map records what appears to have changed. Review records what you decide
              should happen next. Confirming one never approves the implementation.
            </p>
          </GuideCard>
          <GuideCard title="Already in a patch loop?">
            <p>
              Use Review to decide what should stay, change, be removed, or be tested before adding
              another patch.
            </p>
          </GuideCard>
        </aside>
      </div>
    </>
  );
}

function LegacyReviewBoard({
  artifact,
  phase,
  map,
  saving,
  saveError,
  replacementError,
  savedAt,
  initializing,
  onSave,
  onReplace,
}: {
  artifact: ReviewBoardArtifact;
  phase: PhaseView;
  map: StoredChangeMap | null;
  saving: boolean;
  saveError: string | null;
  replacementError: string | null;
  savedAt: string | null;
  initializing: boolean;
  onSave: (payload: ReviewBoardSaveRequest) => Promise<StoredReviewBoardArtifact | null>;
  onReplace: () => Promise<boolean>;
}) {
  const [filesChanged, setFilesChanged] = useState("");
  const [values, setValues] = useState<Record<ManualFieldKey, string>>({
    ai_generated: "",
    accepted: "",
    rejected: "",
    edited_manually: "",
    ai_assumptions: "",
    least_confident: "",
    out_of_scope_changes: "",
  });
  const [replaceOpen, setReplaceOpen] = useState(false);

  useEffect(() => {
    setFilesChanged((artifact.files_changed ?? []).join("\n"));
    setValues((previous) => {
      const next = { ...previous };
      for (const field of MANUAL_FIELDS) next[field.key] = artifact[field.key] ?? "";
      return next;
    });
  }, [artifact]);

  type ManualReviewDraft = { filesChanged: string; values: Record<ManualFieldKey, string> };
  const draft = useDraft<ManualReviewDraft>(`review_board:${phase.phase}`);
  const draftApplied = useRef(false);
  useEffect(() => {
    if (!draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) {
      setFilesChanged(draft.restored.filesChanged ?? "");
      setValues((previous) => ({ ...previous, ...draft.restored?.values }));
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
    saveDraft({ filesChanged, values });
  }, [filesChanged, values, saveDraft]);

  async function save() {
    const files = filesChanged
      .split("\n")
      .map((file) => file.trim())
      .filter(Boolean)
      .slice(0, 50)
      .map((file) => file.slice(0, 300));
    const result = await onSave({
      files_changed: files,
      ...Object.fromEntries(
        MANUAL_FIELDS.map((field) => [
          field.key,
          values[field.key].trim() ? values[field.key].slice(0, 2000) : null,
        ])
      ),
    });
    if (result) {
      skipDraftEcho.current = true;
      draft.clear();
    }
  }

  async function replace() {
    if (await onReplace()) draft.clear();
  }

  return (
    <>
      <h1 className="page-title">Review Board</h1>
      <p className="page-sub">
        Back from your AI tool? Note what it actually did before you build on it. Every field is
        optional — skip what you don&rsquo;t know.
      </p>
      <div className="workspace">
        <div>
          <p className="muted review-phase-line">
            Reviewing work in <strong>Phase {phase.phase}: {phase.phase_title}</strong>
          </p>
          <div className="card">
            <h3>What changed</h3>
            <div className="field">
              <label htmlFor="manual-review-files">Files changed (one per line, up to 50)</label>
              <textarea
                id="manual-review-files"
                rows={4}
                value={filesChanged}
                onChange={(event) => setFilesChanged(event.target.value)}
                placeholder={"app/routes/tasks.py\napp/models.py"}
              />
              <p className="hint">
                If you can&rsquo;t list them, that itself is a finding — check your tool&rsquo;s diff
                before saving.
              </p>
            </div>
          </div>
          <div className="card">
            <h3>The review</h3>
            {MANUAL_FIELDS.map((field) => (
              <div className="field" key={field.key}>
                <label htmlFor={`manual-${field.key}`}>{field.label}</label>
                <textarea
                  id={`manual-${field.key}`}
                  rows={2}
                  maxLength={2000}
                  value={values[field.key]}
                  onChange={(event) => setValues((previous) => ({
                    ...previous,
                    [field.key]: event.target.value,
                  }))}
                  placeholder={field.placeholder}
                />
              </div>
            ))}
          </div>
          <SaveBar
            saving={saving}
            saveError={saveError}
            savedAt={savedAt}
            onSave={() => void save()}
            label="Save review"
          />

          {canReplaceReviewFromMap(map) && (
            <details className="help more-options">
              <summary>More options</summary>
              <div className="help-body">
                <p>Starting from the Change Map will replace the current Review for this phase.</p>
                {!replaceOpen ? (
                  <button className="btn" type="button" onClick={() => setReplaceOpen(true)}>
                    Start over from Change Map
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
          <GuideCard title="Existing Review preserved">
            <p>
              This phase uses the original manual Review format. Codize will not convert or replace
              it unless you deliberately start over from a confirmed Change Map.
            </p>
          </GuideCard>
          <GuideCard title="Honest answers win">
            <ul>
              <li>&ldquo;I don&rsquo;t know what it changed&rdquo; is a real finding.</li>
              <li>Rejected nothing? Say so — but check the diff first.</li>
              <li>The least-confident answer is useful defense preparation.</li>
            </ul>
          </GuideCard>
        </aside>
      </div>
    </>
  );
}

function LinkedReviewBoard({
  review,
  phase,
  map,
  saving,
  saveError,
  replacementError,
  initializing,
  onSave,
  onReplace,
}: {
  review: LinkedReviewBoardArtifact;
  phase: PhaseView;
  map: StoredChangeMap | null;
  saving: boolean;
  saveError: string | null;
  replacementError: string | null;
  initializing: boolean;
  onSave: (payload: ReviewBoardSaveRequest) => Promise<StoredReviewBoardArtifact | null>;
  onReplace: () => Promise<boolean>;
}) {
  const [form, setForm] = useState<LinkedReviewFormState>(() => targetFormFromReview(review));
  const [justSaved, setJustSaved] = useState(false);
  const [replaceOpen, setReplaceOpen] = useState(false);
  const reviewRef = useRef(review);
  reviewRef.current = review;
  const serverRevision = linkedReviewServerRevision(review);

  useEffect(() => {
    setForm(targetFormFromReview(reviewRef.current));
    setJustSaved(false);
    setReplaceOpen(false);
  }, [serverRevision]);

  const draftSurface = linkedReviewDraftSurface(phase.phase, review);
  const draft = useDraft<LinkedReviewDraft>(draftSurface);
  const draftAppliedFor = useRef<string | null>(null);
  useEffect(() => {
    if (!draft.ready || draft.loadedSurface !== draftSurface || draftAppliedFor.current === draftSurface) {
      return;
    }
    draftAppliedFor.current = draftSurface;
    const restored = restoreLinkedReviewDraft(review, draft.restored);
    if (restored && isLinkedReviewDirty(review, restored)) setForm(restored);
    else if (draft.restored) draft.clear();
  }, [draft, draftSurface, review]);

  const dirty = useMemo(() => isLinkedReviewDirty(review, form), [form, review]);
  const blocker = useMemo(() => reviewFormBlocker(review, form), [form, review]);
  const progress = useMemo(() => linkedReviewProgress(review, form), [form, review]);
  const complete = useMemo(() => linkedReviewComplete(review, form), [form, review]);
  const canContinue = useMemo(
    () => linkedReviewAllowsVerification(review, form),
    [form, review]
  );
  const draftBlocked = dirty && containsSecretMarker(JSON.stringify(form));
  const saveLocalDraft = draft.save;
  useEffect(() => {
    if (draftAppliedFor.current !== draftSurface || review.stale) return;
    if (dirty) saveLocalDraft(linkedReviewDraftValue(review, form));
  }, [dirty, draftSurface, form, review, saveLocalDraft]);

  async function save() {
    if (!dirty || blocker || review.stale || draftBlocked) return;
    const result = await onSave(deriveReviewSavePayload(review, form));
    if (result && isLinkedReviewArtifact(result)) {
      draft.clear();
      setForm(targetFormFromReview(result));
      setJustSaved(true);
    }
  }

  async function replace() {
    if (await onReplace()) draft.clear();
  }

  const groups = groupReviewTargets(review.review_targets);
  const replacementReady = canReplaceReviewFromMap(map);

  return (
    <>
      <h1 className="page-title">{REVIEW_PAGE_TITLE}</h1>
      <p className="page-sub">{REVIEW_PAGE_INTRO}</p>
      <p className="review-honesty">{REVIEW_HONESTY_LINE}</p>

      <div className="workspace">
        <div>
          <p className="muted review-phase-line">
            Phase {phase.phase}: {phase.phase_title}
          </p>

          {review.stale && (
            <div className="notice info stale-notice" role="status">
              <strong>Your Change Map changed after this Review was created.</strong>
              <p>Rebuild the Review to use the latest confirmed Change Map.</p>
              {replacementReady ? (
                !replaceOpen ? (
                  <button className="btn primary" type="button" onClick={() => setReplaceOpen(true)}>
                    Rebuild Review from current Change Map
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
                <Link className="btn primary" href="/app/phase/change-map">
                  Update Change Map first
                </Link>
              )}
            </div>
          )}

          <section className="card primary linked-review-surface" aria-labelledby="linked-review-heading">
            <div className="linked-review-summary">
              <div>
                <span className={`pill ${review.stale ? "warn" : "accent"}`}>
                  {review.stale ? "Needs rebuild" : "Current Review"}
                </span>
                <h2 id="linked-review-heading">Implementation Review</h2>
                <p>Started from your reviewed Change Map.</p>
              </div>
              {progress.total > 0 && (
                <strong>{progress.reviewed} of {progress.total} items reviewed</strong>
              )}
            </div>
            <p className="review-source-statement">
              The Change Map describes what appears to have changed. These decisions are yours.
            </p>

            {progress.total > 0 && (
              <div className="review-progress">
                <div
                  className="review-meter"
                  role="progressbar"
                  aria-label="Implementation Review progress"
                  aria-valuemin={0}
                  aria-valuemax={progress.total}
                  aria-valuenow={progress.reviewed}
                  aria-valuetext={`${progress.reviewed} of ${progress.total} items reviewed`}
                >
                  <span style={{ width: `${(progress.reviewed / progress.total) * 100}%` }} />
                </div>
              </div>
            )}

            {review.review_targets.length === 0 ? (
              <div className="notice info review-zero-targets">
                This Change Map did not contain implementation items that automatically become
                Review targets.
              </div>
            ) : (
              <div className="linked-review-groups">
                {groups.map((group) => (
                  <section className="linked-review-group" key={group.category}>
                    <div className="category-heading">
                      <h3>{reviewCategoryLabel(group.category)} <span>({group.targets.length})</span></h3>
                    </div>
                    {group.targets.map((target) => {
                      const targetIndex = review.review_targets.indexOf(target);
                      const targetForm = form[target.review_target_id];
                      if (!targetForm) return null;
                      return (
                        <LinkedReviewTargetRow
                          key={target.review_target_id}
                          target={target}
                          index={targetIndex}
                          form={targetForm}
                          disabled={review.stale || saving}
                          onChange={(patch) => {
                            setForm((current) => ({
                              ...current,
                              [target.review_target_id]: {
                                ...current[target.review_target_id],
                                ...patch,
                              },
                            }));
                            setJustSaved(false);
                          }}
                        />
                      );
                    })}
                  </section>
                ))}
              </div>
            )}

            {draftBlocked && (
              <div className="notice error" role="alert">
                This draft looks like it contains a secret. Remove the key-like text before saving;
                Codize is not keeping this draft on this device.
              </div>
            )}
            {blocker && dirty && <p className="field-error">{blocker}</p>}
            {dirty && !review.stale && (
              <SaveBar
                saving={saving}
                saveError={saveError}
                savedAt={null}
                onSave={() => void save()}
                label="Save Review"
                disabled={Boolean(blocker) || draftBlocked}
              />
            )}
            {!dirty && saveError && <div className="notice error" role="alert">{saveError}</div>}
            {justSaved && (
              <div className="notice ok" role="status"><strong>Review saved.</strong></div>
            )}

            {!review.stale && !dirty && canContinue && (
              <div className="review-complete" role="status">
                {complete ? (
                  <>
                    <strong>Review complete</strong>
                    <p>
                      You recorded a decision for every implementation item. Items marked for
                      testing or uncertainty remain visible.
                    </p>
                  </>
                ) : (
                  <p>No automatic targets need a decision in this Review.</p>
                )}
                <Link className="btn primary" href="/app/phase/verify">
                  Continue to Verification
                </Link>
              </div>
            )}
          </section>

          {!review.stale && (
            <details className="help more-options">
              <summary>More options</summary>
              <div className="help-body">
                <p>Rebuild this Review only when you deliberately want fresh pending targets.</p>
                {!replacementReady ? (
                  <Link href="/app/phase/change-map">Review the current Change Map first</Link>
                ) : !replaceOpen ? (
                  <button className="btn" type="button" onClick={() => setReplaceOpen(true)}>
                    Rebuild Review from Change Map
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
          <GuideCard title="What each choice means">
            <p><strong>Keep</strong> means you intend to keep the choice for now.</p>
            <p><strong>Needs testing</strong> means you want to check the behavior before deciding.</p>
            <p><strong>I&rsquo;m not sure</strong> keeps uncertainty honest and still records your review.</p>
          </GuideCard>
          <GuideCard title="Change Map versus Review">
            <p>
              The Change Map records what appears to have changed. Review records what you decide
              to do about it. Neither one claims the implementation is correct or verified.
            </p>
          </GuideCard>
          <GuideCard title="Your draft is scoped">
            <p>
              Unsaved decisions stay on this device for your account, active project, phase, and
              exact linked Review. Saving reconciles them with the server record.
            </p>
          </GuideCard>
        </aside>
      </div>
      <p className="sr-only" role="status" aria-live="polite">
        {saving ? "Saving Review." : complete && !dirty ? "Review complete." : ""}
      </p>
    </>
  );
}

export default function ReviewBoardPage() {
  const wf = useWorkflowSection("review_board");
  const [initializing, setInitializing] = useState(false);
  const [initializationError, setInitializationError] = useState<string | null>(null);

  if (wf.notReady) return <NotReady title="Review What Changed" />;

  async function initialize(replaceExisting: boolean): Promise<boolean> {
    if (!wf.phase || initializing) return false;
    setInitializing(true);
    setInitializationError(null);
    try {
      const result = await initializeReviewFromChangeMap(wf.phase.phase, replaceExisting);
      wf.applyArtifact(result.artifact);
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409 && !replaceExisting) {
        // A concurrent click/tab may have initialized Review first. Refetch the
        // single source of truth and display that existing artifact.
        await wf.reload();
      } else {
        setInitializationError(
          error instanceof ApiError ? error.message : "Couldn’t prepare this Review. Try again."
        );
      }
      return false;
    } finally {
      setInitializing(false);
    }
  }

  if (showFullReviewInitializationState(initializing, Boolean(wf.stored))) {
    return (
      <>
        <h1 className="page-title">{REVIEW_PAGE_TITLE}</h1>
        <p className="page-sub">Review implementation choices before continuing.</p>
        <div className="card primary review-initializing" role="status" aria-live="polite">
          <h2>Preparing your Review…</h2>
          <p>Codize is carrying over the implementation-relevant items from your reviewed Change Map.</p>
        </div>
      </>
    );
  }

  return (
    <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
      {wf.phase && (() => {
        const mode = reviewArtifactMode(wf.stored);
        if (mode === "linked" && isLinkedReviewArtifact(wf.stored)) {
          return (
            <LinkedReviewBoard
              review={wf.stored}
              phase={wf.phase}
              map={wf.changeMap}
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
            <LegacyReviewBoard
              artifact={wf.stored}
              phase={wf.phase}
              map={wf.changeMap}
              saving={wf.saving}
              saveError={wf.saveError}
              replacementError={initializationError}
              savedAt={wf.savedAt}
              initializing={initializing}
              onSave={wf.save}
              onReplace={() => initialize(true)}
            />
          );
        }
        return (
          <ReviewPrerequisite
            map={wf.changeMap}
            phase={wf.phase}
            error={initializationError}
            onStart={() => void initialize(false)}
          />
        );
      })()}
    </Async>
  );
}
