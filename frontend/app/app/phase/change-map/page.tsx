"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import Async from "@/components/Async";
import AdaptiveStepGuide from "@/components/AdaptiveStepGuide";
import { ChangeMapErrorNotice, SourceReferences } from "@/components/ChangeMapSafety";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import {
  ApiError,
  confirmChangeMap,
  createManualChangeMap,
  generateChangeMap,
  updateChangeMap,
} from "@/lib/api";
import {
  aiUncertaintyLabel,
  categoryExplanation,
  categoryLabel,
  CHANGE_MAP_CATEGORY_ORDER,
  type ChangeMapGenerationFailureKind,
  CHANGE_MAP_HONESTY_LINE,
  CHANGE_MAP_NOTE_MAX,
  CHANGE_MAP_PAGE_INTRO,
  CHANGE_MAP_PAGE_TITLE,
  CHANGE_MAP_STUDENT_ITEMS_MAX,
  CHANGE_MAP_TEXT_MAX,
  changeMapCharacterCount,
  changeMapDraftSurface,
  confirmationReadiness,
  decisionLabel,
  deriveReviewProgress,
  deriveSavePayload,
  deriveChangeMapPageModel,
  groupItemsByCategory,
  generationFailureCopy,
  hasOnlyQuestionItems,
  humanSafeStatusCopy,
  isReviewDirty,
  restoreReviewDraft,
  REVIEWABLE_DECISIONS,
  reviewBlocker,
  reviewStateFromMap,
  STUDENT_ADDED_DECISIONS,
  type AiItemReviewDraft,
  type ChangeMapReviewState,
  type StudentAddedReviewDraft,
} from "@/lib/changeMap";
import { containsSecretMarker, useDraft } from "@/lib/drafts";
import type {
  ChangeMapCategory,
  ChangeMapItem,
  ChangeMapStudentDecision,
  StoredChangeMap,
  StudentAddedChangeMapDecision,
} from "@/lib/types";
import { useWorkflowSection } from "@/lib/useWorkflowSection";

function decisionTone(decision: ChangeMapStudentDecision): string {
  if (decision === "rejected") return "danger";
  if (decision === "uncertain" || decision === "needs_inspection") return "warn";
  if (decision === "edited" || decision === "confirmed") return "accent";
  return "";
}

function AiReviewItem({
  item,
  draft,
  editable,
  onDecision,
  onText,
  onNote,
}: {
  item: ChangeMapItem;
  draft: AiItemReviewDraft;
  editable: boolean;
  onDecision: (decision: ChangeMapStudentDecision) => void;
  onText: (text: string) => void;
  onNote: (note: string) => void;
}) {
  const correctionMissing = draft.studentDecision === "edited" && !draft.studentText.trim();
  const correctionCount = changeMapCharacterCount(draft.studentText);
  const correctionTooLong = correctionCount > CHANGE_MAP_TEXT_MAX;
  const correctionError = correctionMissing
    ? "Add your corrected wording before saving."
    : correctionTooLong
      ? `Shorten this correction to ${CHANGE_MAP_TEXT_MAX} characters or fewer.`
      : null;
  const correctionErrorId = `${item.item_id}-correction-error`;
  const noteCount = changeMapCharacterCount(draft.studentNote);
  const noteTooLong = noteCount > CHANGE_MAP_NOTE_MAX;
  const noteErrorId = `${item.item_id}-note-error`;
  return (
    <article
      className={`change-map-item${draft.studentDecision === "rejected" ? " rejected" : ""}`}
    >
      <div className="change-map-item-head">
        <span className="authorship">Codize draft</span>
        <span className={`pill ${decisionTone(draft.studentDecision)}`}>
          {decisionLabel(draft.studentDecision)}
        </span>
      </div>

      <p className="change-map-draft">{item.draft_text}</p>
      <div className="row item-context">
        {item.ai_uncertainty && (
          <span className={`pill ${item.ai_uncertainty === "supported" ? "" : "warn"}`}>
            {aiUncertaintyLabel(item.ai_uncertainty)}
          </span>
        )}
      </div>
      {item.ai_uncertainty !== "supported" && item.uncertainty_reason && (
        <p className="muted uncertainty-reason">{item.uncertainty_reason}</p>
      )}

      {editable ? (
        <fieldset className="decision-picker">
          <legend>Your decision</legend>
          <div className="chips">
            {REVIEWABLE_DECISIONS.map((decision) => (
              <label
                className={`chip${draft.studentDecision === decision ? " active" : ""}`}
                key={decision}
              >
                <input
                  type="radio"
                  name={`decision-${item.item_id}`}
                  value={decision}
                  checked={draft.studentDecision === decision}
                  onChange={() => onDecision(decision)}
                />
                {decisionLabel(decision)}
              </label>
            ))}
          </div>
        </fieldset>
      ) : null}

      {draft.studentDecision === "edited" && (
        <div className="student-correction">
          <div className="field">
            <label htmlFor={`${item.item_id}-correction`}>Your correction</label>
            {editable ? (
              <>
                <textarea
                  id={`${item.item_id}-correction`}
                  rows={3}
                  value={draft.studentText}
                  onChange={(event) => onText(event.target.value)}
                  aria-invalid={correctionError != null}
                  aria-describedby={correctionError ? correctionErrorId : undefined}
                />
                <p className="hint">
                  {correctionCount.toLocaleString()} / {CHANGE_MAP_TEXT_MAX}
                </p>
                {correctionError && (
                  <p className="field-error" id={correctionErrorId}>
                    {correctionError}
                  </p>
                )}
              </>
            ) : (
              <p>{draft.studentText}</p>
            )}
          </div>
        </div>
      )}

      {draft.studentDecision === "rejected" && (
        <p className="decision-explanation">
          Rejected items stay in the review record but will not be treated as confirmed project
          information.
        </p>
      )}
      {(draft.studentDecision === "uncertain" ||
        draft.studentDecision === "needs_inspection") && (
        <p className="decision-explanation">
          This remains unresolved. You can still confirm that you reviewed the map.
        </p>
      )}

      {editable ? (
        <details className="help item-note" open={draft.studentNote.length > 0 || undefined}>
          <summary>
            {draft.studentDecision === "rejected"
              ? "Why are you rejecting this? (optional)"
              : "Add a note (optional)"}
          </summary>
          <div className="help-body">
            <textarea
              aria-label={`Review note for: ${item.draft_text}`}
              rows={2}
              value={draft.studentNote}
              onChange={(event) => onNote(event.target.value)}
              placeholder="Record what you still need to check or remember."
              aria-invalid={noteTooLong}
              aria-describedby={noteTooLong ? noteErrorId : undefined}
            />
            <p className="hint">
              {noteCount.toLocaleString()} / {CHANGE_MAP_NOTE_MAX.toLocaleString()}
            </p>
            {noteTooLong && (
              <p className="field-error" id={noteErrorId}>
                Shorten this note to {CHANGE_MAP_NOTE_MAX.toLocaleString()} characters or fewer.
              </p>
            )}
          </div>
        </details>
      ) : (
        draft.studentNote && (
          <div className="student-note">
            <span>Your note</span>
            <p>{draft.studentNote}</p>
          </div>
        )
      )}

      <SourceReferences item={item} />
    </article>
  );
}

function StudentAddedItem({
  item,
  editable,
  onChange,
  onRemove,
}: {
  item: StudentAddedReviewDraft;
  editable: boolean;
  onChange: (patch: Partial<StudentAddedReviewDraft>) => void;
  onRemove: () => void;
}) {
  const textMissing = !item.studentText.trim();
  const textCount = changeMapCharacterCount(item.studentText);
  const textTooLong = textCount > CHANGE_MAP_TEXT_MAX;
  const textError = textMissing
    ? "Describe the item before saving."
    : textTooLong
      ? `Shorten this item to ${CHANGE_MAP_TEXT_MAX} characters or fewer.`
      : null;
  const textErrorId = `${item.localId}-text-error`;
  const noteCount = changeMapCharacterCount(item.studentNote);
  const noteTooLong = noteCount > CHANGE_MAP_NOTE_MAX;
  const noteErrorId = `${item.localId}-note-error`;
  return (
    <article className="change-map-item student-added">
      <div className="change-map-item-head">
        <span className="authorship student">Added by you</span>
        <span className={`pill ${decisionTone(item.studentDecision)}`}>
          {decisionLabel(item.studentDecision)}
        </span>
      </div>

      {editable ? (
        <>
          <div className="field">
            <label htmlFor={`${item.localId}-category`}>Category</label>
            <select
              id={`${item.localId}-category`}
              value={item.category}
              onChange={(event) =>
                onChange({ category: event.target.value as ChangeMapCategory })
              }
            >
              {CHANGE_MAP_CATEGORY_ORDER.map((category) => (
                <option key={category} value={category}>
                  {categoryLabel(category)}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor={`${item.localId}-text`}>What should the map include?</label>
            <textarea
              id={`${item.localId}-text`}
              rows={3}
              value={item.studentText}
              onChange={(event) => onChange({ studentText: event.target.value })}
              aria-invalid={textError != null}
              aria-describedby={textError ? textErrorId : undefined}
              placeholder="Describe the change, decision, risk, or question Codize missed."
            />
            <p className="hint">
              {textCount.toLocaleString()} / {CHANGE_MAP_TEXT_MAX}
            </p>
            {textError && (
              <p className="field-error" id={textErrorId}>
                {textError}
              </p>
            )}
          </div>
          <div className="field">
            <label htmlFor={`${item.localId}-note`}>Optional note</label>
            <textarea
              id={`${item.localId}-note`}
              rows={2}
              value={item.studentNote}
              onChange={(event) => onChange({ studentNote: event.target.value })}
              aria-invalid={noteTooLong}
              aria-describedby={noteTooLong ? noteErrorId : undefined}
            />
            <p className="hint">
              {noteCount.toLocaleString()} / {CHANGE_MAP_NOTE_MAX.toLocaleString()}
            </p>
            {noteTooLong && (
              <p className="field-error" id={noteErrorId}>
                Shorten this note to {CHANGE_MAP_NOTE_MAX.toLocaleString()} characters or fewer.
              </p>
            )}
          </div>
          <fieldset className="decision-picker">
            <legend>Current status</legend>
            <div className="chips">
              {STUDENT_ADDED_DECISIONS.map((decision) => (
                <label
                  className={`chip${item.studentDecision === decision ? " active" : ""}`}
                  key={decision}
                >
                  <input
                    type="radio"
                    name={`student-decision-${item.localId}`}
                    value={decision}
                    checked={item.studentDecision === decision}
                    onChange={() => onChange({ studentDecision: decision })}
                  />
                  {decisionLabel(decision)}
                </label>
              ))}
            </div>
          </fieldset>
          <button
            className="btn small"
            type="button"
            onClick={onRemove}
            aria-label={`Remove student-added item: ${item.studentText || "untitled item"}`}
          >
            Remove this item
          </button>
        </>
      ) : (
        <>
          <p className="change-map-draft">{item.studentText}</p>
          {item.studentNote && (
            <div className="student-note">
              <span>Your note</span>
              <p>{item.studentNote}</p>
            </div>
          )}
        </>
      )}
    </article>
  );
}

function GenerationFailure({
  kind,
  replacing,
  onRetry,
  onManual,
  manualBusy,
}: {
  kind: ChangeMapGenerationFailureKind;
  replacing: boolean;
  onRetry: () => void;
  onManual?: () => void;
  manualBusy: boolean;
}) {
  const alertRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => alertRef.current?.focus(), []);
  const copy = generationFailureCopy(kind);
  return (
    <div
      ref={alertRef}
      className="notice info generation-failure"
      role="alert"
      tabIndex={-1}
    >
      <strong>{copy.title}</strong>
      <p>
        Your saved implementation material is unchanged
        {replacing ? ", and the current Change Map is still here" : ""}.
      </p>
      <p>{copy.correction}</p>
      <div className="row" style={{ marginTop: 10 }}>
        <button className="btn primary" type="button" onClick={onRetry}>
          Try again
        </button>
        {onManual && (
          <button className="btn" type="button" onClick={onManual} disabled={manualBusy}>
            {manualBusy ? "Creating manual map…" : "Create a Change Map manually"}
          </button>
        )}
        <Link className="btn" href="/app/phase/import">
          Review imported material
        </Link>
      </div>
    </div>
  );
}

export default function ChangeMapPage() {
  const wf = useWorkflowSection("implementation_import");
  const [map, setMap] = useState<StoredChangeMap | null>(null);
  const [review, setReview] = useState<ChangeMapReviewState | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [manualCreating, setManualCreating] = useState(false);
  const [generationFailed, setGenerationFailed] = useState(false);
  const [generationFailureKind, setGenerationFailureKind] =
    useState<ChangeMapGenerationFailureKind>("invalid_output");
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [justSaved, setJustSaved] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [justConfirmed, setJustConfirmed] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [regenerateOpen, setRegenerateOpen] = useState(false);
  const initializedMapSnapshot = useRef<string | null>(null);

  useEffect(() => {
    setMap(wf.changeMap);
  }, [wf.changeMap]);

  useEffect(() => {
    if (!map) {
      initializedMapSnapshot.current = null;
      setReview(null);
      setEditMode(false);
      return;
    }
    // The shared loader can resolve the same GET twice in development Strict
    // Mode. Treat an identical server map as the same baseline so a restored
    // local review draft is not replaced by that second response.
    const snapshot = JSON.stringify(map);
    if (initializedMapSnapshot.current === snapshot) return;
    initializedMapSnapshot.current = snapshot;
    setReview(reviewStateFromMap(map));
    setEditMode(map.status !== "confirmed" && !map.stale);
  }, [map]);

  const draftSurface = wf.phase && map ? changeMapDraftSurface(wf.phase.phase, map) : null;
  const draft = useDraft<ChangeMapReviewState>(draftSurface);
  const draftAppliedFor = useRef<string | null>(null);
  const dirtyTracker = useRef<{ surface: string | null; dirty: boolean }>({
    surface: null,
    dirty: false,
  });

  useEffect(() => {
    if (
      !map ||
      !review ||
      !draftSurface ||
      !draft.ready ||
      draft.loadedSurface !== draftSurface ||
      draftAppliedFor.current === draftSurface
    ) {
      return;
    }
    draftAppliedFor.current = draftSurface;
    const restored = restoreReviewDraft(map, draft.restored);
    if (restored && isReviewDirty(map, restored)) {
      setReview(restored);
      setEditMode(true);
    } else if (draft.restored) {
      draft.clear();
    }
  }, [draft, draftSurface, map, review]);

  const dirty = useMemo(
    () => Boolean(map && review && isReviewDirty(map, review)),
    [map, review]
  );
  const draftBlocked = Boolean(review && dirty && containsSecretMarker(JSON.stringify(review)));

  const saveLocalDraft = draft.save;
  useEffect(() => {
    if (
      !review ||
      !dirty ||
      !editMode ||
      map?.stale ||
      draft.loadedSurface !== draftSurface
    ) {
      return;
    }
    saveLocalDraft(review);
  }, [dirty, draft.loadedSurface, draftSurface, editMode, map?.stale, review, saveLocalDraft]);

  const clearLocalDraft = draft.clear;
  useEffect(() => {
    if (!draftSurface || draft.loadedSurface !== draftSurface) return;
    if (dirtyTracker.current.surface !== draftSurface) {
      dirtyTracker.current = { surface: draftSurface, dirty };
      return;
    }
    if (dirtyTracker.current.dirty && !dirty) clearLocalDraft();
    dirtyTracker.current = { surface: draftSurface, dirty };
  }, [clearLocalDraft, dirty, draft.loadedSurface, draftSurface]);

  if (wf.notReady) return <NotReady title="Review Your Change Map" />;

  async function runGeneration(replaceExisting: boolean) {
    if (!wf.phase || generating) return;
    setGenerating(true);
    setGenerationFailed(false);
    setGenerationError(null);
    setSaveError(null);
    setConfirmError(null);
    setJustSaved(false);
    setJustConfirmed(false);
    try {
      const generated = await generateChangeMap(wf.phase.phase, replaceExisting);
      if (replaceExisting) draft.clear();
      draftAppliedFor.current = null;
      setMap(generated);
      setReview(reviewStateFromMap(generated));
      setEditMode(true);
      setRegenerateOpen(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 502) {
        const code = error.code?.replace("change_map_", "");
        setGenerationFailureKind(
          code === "grounding_rejected" ||
            code === "provider_unavailable" ||
            code === "invalid_output"
            ? code
            : "invalid_output"
        );
        setGenerationFailed(true);
      } else {
        setGenerationError(
          error instanceof ApiError ? error.message : "Couldn’t create the Change Map. Try again."
        );
      }
      if (error instanceof ApiError && error.status === 409) await wf.reload();
    } finally {
      setGenerating(false);
    }
  }

  async function runManualCreation() {
    if (!wf.phase || manualCreating || map) return;
    setManualCreating(true);
    setGenerationError(null);
    try {
      const created = await createManualChangeMap(wf.phase.phase);
      draftAppliedFor.current = null;
      setMap(created);
      setReview(reviewStateFromMap(created));
      setEditMode(true);
      setGenerationFailed(false);
    } catch (error) {
      setGenerationError(
        error instanceof ApiError ? error.message : "Couldn’t create a manual Change Map. Try again."
      );
      if (error instanceof ApiError && error.status === 409) await wf.reload();
    } finally {
      setManualCreating(false);
    }
  }

  function setAiDecision(item: ChangeMapItem, decision: ChangeMapStudentDecision) {
    setReview((current) => {
      if (!current) return current;
      const existing = current.itemDecisions[item.item_id];
      if (!existing) return current;
      return {
        ...current,
        itemDecisions: {
          ...current.itemDecisions,
          [item.item_id]: {
            ...existing,
            studentDecision: decision,
            studentText:
              decision === "edited" && !existing.studentText
                ? item.draft_text ?? ""
                : existing.studentText,
          },
        },
      };
    });
    setJustSaved(false);
    setConfirmOpen(false);
  }

  function updateAiDraft(itemId: string, patch: Partial<AiItemReviewDraft>) {
    setReview((current) => {
      if (!current || !current.itemDecisions[itemId]) return current;
      return {
        ...current,
        itemDecisions: {
          ...current.itemDecisions,
          [itemId]: { ...current.itemDecisions[itemId], ...patch },
        },
      };
    });
    setJustSaved(false);
    setConfirmOpen(false);
  }

  function addStudentItem() {
    setReview((current) => {
      if (!current || current.studentAddedItems.length >= CHANGE_MAP_STUDENT_ITEMS_MAX) {
        return current;
      }
      const item: StudentAddedReviewDraft = {
        localId: `local-${Date.now()}-${current.studentAddedItems.length}`,
        category: "changed_file",
        studentText: "",
        studentNote: "",
        studentDecision: "confirmed",
      };
      return { ...current, studentAddedItems: [...current.studentAddedItems, item] };
    });
    setJustSaved(false);
    setEditMode(true);
  }

  function updateStudentItem(localId: string, patch: Partial<StudentAddedReviewDraft>) {
    setReview((current) =>
      current
        ? {
            ...current,
            studentAddedItems: current.studentAddedItems.map((item) =>
              item.localId === localId ? { ...item, ...patch } : item
            ),
          }
        : current
    );
    setJustSaved(false);
    setConfirmOpen(false);
  }

  function removeStudentItem(localId: string) {
    setReview((current) =>
      current
        ? {
            ...current,
            studentAddedItems: current.studentAddedItems.filter(
              (item) => item.localId !== localId
            ),
          }
        : current
    );
    setJustSaved(false);
    setConfirmOpen(false);
  }

  async function saveReview() {
    if (!map || !review || !wf.phase || saving || draftBlocked) return;
    const blocker = reviewBlocker(map, review);
    if (blocker) return;
    setSaving(true);
    setSaveError(null);
    setConfirmError(null);
    try {
      const saved = await updateChangeMap(wf.phase.phase, deriveSavePayload(map, review));
      draft.clear();
      setMap(saved);
      setReview(reviewStateFromMap(saved));
      setEditMode(true);
      setJustSaved(true);
      setJustConfirmed(false);
    } catch (error) {
      setSaveError(error instanceof ApiError ? error.message : "Couldn’t save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmReviewedMap() {
    if (!map || !review || !wf.phase || confirming) return;
    const readiness = confirmationReadiness(map, review, dirty);
    if (!readiness.allowed) return;
    setConfirming(true);
    setConfirmError(null);
    try {
      const confirmed = await confirmChangeMap(wf.phase.phase);
      draft.clear();
      setMap(confirmed);
      setReview(reviewStateFromMap(confirmed));
      setEditMode(false);
      setConfirmOpen(false);
      setJustConfirmed(true);
      setJustSaved(false);
    } catch (error) {
      setConfirmError(
        error instanceof ApiError ? error.message : "Couldn’t confirm the map. Try again."
      );
      if (error instanceof ApiError && error.status === 409) await wf.reload();
    } finally {
      setConfirming(false);
    }
  }

  function cancelConfirmedEditing() {
    if (!map) return;
    setReview(reviewStateFromMap(map));
    draft.clear();
    setEditMode(false);
    setJustSaved(false);
  }

  const retryIsReplacement = Boolean(map);
  const blocker = map && review ? reviewBlocker(map, review) : null;
  const progress = map && review ? deriveReviewProgress(map, review) : null;
  const readiness = map && review ? confirmationReadiness(map, review, dirty) : null;
  const canEdit = Boolean(map && review && editMode && !map.stale && !generating);
  const pageModel = deriveChangeMapPageModel(Boolean(wf.stored), map, generating, generationFailed);
  const groupedAi = map
    ? groupItemsByCategory(map.items.filter((item) => item.origin === "ai_inferred"))
    : [];
  const aiByCategory = new Map(groupedAi.map((group) => [group.category, group.items]));
  const visibleCategories = review
    ? CHANGE_MAP_CATEGORY_ORDER.filter(
        (category) =>
          (aiByCategory.get(category)?.length ?? 0) > 0 ||
          review.studentAddedItems.some((item) => item.category === category)
      )
    : [];

  return (
    <>
      <h1 className="page-title">{CHANGE_MAP_PAGE_TITLE}</h1>
      <p className="page-sub">
        {CHANGE_MAP_PAGE_INTRO} <strong>{CHANGE_MAP_HONESTY_LINE}</strong>
      </p>
      <AdaptiveStepGuide stage="change_map" />

      <p className="sr-only" aria-live="polite">
        {generating
          ? "Drafting your Change Map."
          : saving
            ? "Saving your review."
            : confirming
              ? "Confirming your reviewed Change Map."
              : justConfirmed
                ? "Change Map reviewed and confirmed."
                : justSaved
                  ? "Review saved."
                  : ""}
      </p>
      <p className="sr-only" role="alert">
        {saveError
          ? `Review save failed. ${saveError}`
          : confirmError
            ? `Confirmation failed. ${confirmError}`
            : ""}
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
            {wf.phase && (
              <p className="muted" style={{ marginBottom: 14 }}>
                For <strong>Phase {wf.phase.phase}: {wf.phase.phase_title}</strong>
              </p>
            )}

            {generationError && <ChangeMapErrorNotice message={generationError} />}

            {pageModel.state === "missing_import" && (
              <div className="card primary change-map-empty">
                <h2>Bring back implementation material first</h2>
                <p>
                  Add the AI response, changed code, diff, changed files, or your own summary. Then
                  Codize can draft a Change Map.
                </p>
                <Link href="/app/phase/import" className="btn primary">
                  Bring Back What Changed
                </Link>
              </div>
            )}

            {pageModel.state === "ready_to_generate" && (
              <div className="card primary change-map-empty">
                <h2>Turn your import into a Change Map</h2>
                <p>
                  Codize will draft what appears to have changed, where that idea came from, and
                  what may still need inspection.
                </p>
                <p className="muted">You will review every item before confirming the map.</p>
                <button className="btn primary" type="button" onClick={() => void runGeneration(false)}>
                  Create Change Map
                </button>
                <p className="hint" style={{ marginTop: 8 }}>Drafting may take a moment.</p>
                <details className="help">
                  <summary>What will Codize look for?</summary>
                  <div className="help-body">
                    <ul>
                      <li>changed files and behavior;</li>
                      <li>important implementation decisions;</li>
                      <li>areas needing review or testing;</li>
                      <li>project-specific questions.</li>
                    </ul>
                  </div>
                </details>
              </div>
            )}

            {pageModel.state === "generating" && (
              <div className="card primary generation-loading" role="status" aria-live="polite">
                <span className="loading" aria-hidden="true">drafting</span>
                <h2>Drafting your Change Map…</h2>
                <p>Codize is matching each suggestion back to the material you brought in.</p>
              </div>
            )}

            {generationFailed && (
              <GenerationFailure
                kind={generationFailureKind}
                replacing={retryIsReplacement}
                onRetry={() => void runGeneration(retryIsReplacement)}
                onManual={retryIsReplacement ? undefined : () => void runManualCreation()}
                manualBusy={manualCreating}
              />
            )}

            {map && review && (
              <>
                {generating && (
                  <div className="notice info" role="status" aria-live="polite">
                    <strong>Drafting a new Change Map…</strong>
                    <p>The current map stays visible until a safely grounded replacement is ready.</p>
                  </div>
                )}

                {map.stale && (
                  <div className="notice info stale-notice" role="status">
                    <strong>Your implementation material changed after this map was created.</strong>
                    <p>
                      {wf.stored
                        ? "Regenerate the Change Map to review the latest material."
                        : "Bring back implementation material again, then regenerate the Change Map."}
                    </p>
                    {wf.stored ? (
                      <button
                        className="btn primary"
                        type="button"
                        onClick={() => setRegenerateOpen(true)}
                      >
                        Regenerate from latest import
                      </button>
                    ) : (
                      <Link href="/app/phase/import" className="btn primary">
                        Bring Back What Changed
                      </Link>
                    )}
                  </div>
                )}

                {regenerateOpen && (
                  <div className="replacement-warning" role="alert">
                    <strong>Replace this Change Map?</strong>
                    <p>
                      Regenerating replaces this Change Map and its current review decisions. Your
                      saved implementation material stays unchanged.
                    </p>
                    <div className="row">
                      <button
                        className="btn primary"
                        type="button"
                        disabled={generating}
                        onClick={() => void runGeneration(true)}
                      >
                        {generating ? "Regenerating…" : "Replace and regenerate"}
                      </button>
                      <button className="btn" type="button" onClick={() => setRegenerateOpen(false)}>
                        Keep current map
                      </button>
                    </div>
                  </div>
                )}

                <section className="card primary change-map-surface" aria-labelledby="map-heading">
                  <div className="change-map-summary">
                    <div>
                      <span className={`pill ${map.stale ? "warn" : map.status === "confirmed" ? "ok" : "accent"}`}>
                        {humanSafeStatusCopy(map)}
                      </span>
                      <h2 id="map-heading">
                        {map.status === "confirmed" ? "Reviewed Change Map" : "Change Map draft"}
                      </h2>
                      <p>This appears to be what changed. Review and correct it.</p>
                    </div>
                    <div className="map-dates">
                      <span>Generated {new Date(map.generated_at).toLocaleString()}</span>
                      {map.confirmed_at && (
                        <span>Reviewed {new Date(map.confirmed_at).toLocaleString()}</span>
                      )}
                    </div>
                  </div>

                  {progress && (
                    <div className="review-progress">
                      <div className="spread">
                        <strong>{progress.reviewed} of {progress.total} items reviewed</strong>
                        <span className="muted">Review progress</span>
                      </div>
                      <div
                        className="review-meter"
                        role="progressbar"
                        aria-label="Change Map review progress"
                        aria-valuemin={0}
                        aria-valuemax={progress.total}
                        aria-valuenow={progress.reviewed}
                      >
                        <span
                          style={{
                            width: `${progress.total ? (progress.reviewed / progress.total) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {(pageModel.showRedactionNotice || pageModel.showTruncationNotice) && (
                    <div className="source-notices">
                      {pageModel.showRedactionNotice && (
                        <div className="notice info">
                          Credential-like values were removed before Codize generated this draft.
                          <span className="muted">
                            {" "}Your saved import remains unchanged; redaction applied only before AI analysis.
                          </span>
                        </div>
                      )}
                      {pageModel.showTruncationNotice && (
                        <div className="notice info">
                          Some long imported material was shortened before Change Map generation.
                          <span className="muted">
                            {" "}Review carefully because Codize did not analyze every character.
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {hasOnlyQuestionItems(map) && (
                    <p className="notice info">
                      The imported material supported questions more clearly than specific change
                      claims. Review these questions, or improve the import before regenerating.
                    </p>
                  )}

                  <div className="change-map-groups">
                    {visibleCategories.map((category) => {
                      const aiItems = aiByCategory.get(category) ?? [];
                      const studentItems = review.studentAddedItems.filter(
                        (item) => item.category === category
                      );
                      const count = aiItems.length + studentItems.length;
                      return (
                        <section className="change-map-group" key={category}>
                          <div className="category-heading">
                            <h3>{categoryLabel(category)} <span>({count})</span></h3>
                            <p>{categoryExplanation(category)}</p>
                          </div>
                          {aiItems.map((item) => (
                            <AiReviewItem
                              key={item.item_id}
                              item={item}
                              draft={review.itemDecisions[item.item_id]}
                              editable={canEdit}
                              onDecision={(decision) => setAiDecision(item, decision)}
                              onText={(studentText) => updateAiDraft(item.item_id, { studentText })}
                              onNote={(studentNote) => updateAiDraft(item.item_id, { studentNote })}
                            />
                          ))}
                          {studentItems.map((item) => (
                            <StudentAddedItem
                              key={item.localId}
                              item={item}
                              editable={canEdit}
                              onChange={(itemPatch) => updateStudentItem(item.localId, itemPatch)}
                              onRemove={() => removeStudentItem(item.localId)}
                            />
                          ))}
                        </section>
                      );
                    })}
                  </div>

                  {canEdit && review.studentAddedItems.length < CHANGE_MAP_STUDENT_ITEMS_MAX && (
                    <button className="btn" type="button" onClick={addStudentItem}>
                      Add something Codize missed
                    </button>
                  )}

                  {draftBlocked && (
                    <p className="notice info" role="alert">
                      Something in your review looks like a real key, so this draft is not being
                      kept on this device. Remove it before saving.
                    </p>
                  )}
                  {dirty && !draftBlocked && (
                    <p className="hint">
                      Codize will try to restore this unsaved review on this device for this map and
                      phase.
                    </p>
                  )}
                  {justSaved && (
                    <div className="notice ok" role="status">
                      <strong>Review saved.</strong> Your decisions are now part of this phase’s
                      Change Map.
                    </div>
                  )}
                  {blocker && dirty && <p className="field-error">{blocker}</p>}

                  {dirty && canEdit && (
                    <SaveBar
                      saving={saving}
                      saveError={saveError}
                      savedAt={null}
                      onSave={() => void saveReview()}
                      label="Save review"
                      disabled={blocker != null || draftBlocked}
                    />
                  )}
                  {!dirty && saveError && <div className="notice error">{saveError}</div>}

                  {map.status === "draft" && !map.stale && readiness && (
                    <div className="confirmation-area">
                      <p className={readiness.allowed ? "notice ok" : "notice info"} role="status">
                        {readiness.message}
                      </p>
                      {readiness.allowed && !confirmOpen && (
                        <button
                          className="btn primary"
                          type="button"
                          onClick={() => setConfirmOpen(true)}
                        >
                          Confirm reviewed map
                        </button>
                      )}
                      {confirmOpen && (
                        <div className="confirmation-disclosure">
                          <strong>What confirmation means</strong>
                          <p>
                            Confirming means you reviewed this map and recorded what you accept,
                            corrected, rejected, or still need to inspect. It does not mean the
                            implementation is proven correct.
                          </p>
                          <div className="row">
                            <button
                              className="btn primary"
                              type="button"
                              disabled={confirming}
                              onClick={() => void confirmReviewedMap()}
                            >
                              {confirming ? "Confirming…" : "Yes, confirm reviewed map"}
                            </button>
                            <button className="btn" type="button" onClick={() => setConfirmOpen(false)}>
                              Not yet
                            </button>
                          </div>
                        </div>
                      )}
                      {confirmError && <div className="notice error">{confirmError}</div>}
                    </div>
                  )}

                  {map.status === "confirmed" && !map.stale && !editMode && (
                    <div className="confirmed-actions">
                      <div className="notice ok" role="status">
                        <strong>{justConfirmed ? "Change Map reviewed" : "Reviewed and confirmed"}.</strong>
                        <p>
                          Your decisions and remaining uncertainties are part of this phase’s record.
                        </p>
                      </div>
                      <div className="row">
                        <Link href="/app/phase/review" className="btn primary">
                          Continue Review
                        </Link>
                        <button className="btn" type="button" onClick={() => setEditMode(true)}>
                          Edit reviewed map
                        </button>
                      </div>
                    </div>
                  )}

                  {map.status === "confirmed" && !map.stale && editMode && (
                    <div className="notice info">
                      Saving a new decision returns this map to draft and requires confirmation
                      again. Nothing changes until you select <strong>Save review</strong>.
                      {!dirty && (
                        <button
                          className="btn small"
                          style={{ marginLeft: 10 }}
                          type="button"
                          onClick={cancelConfirmedEditing}
                        >
                          Cancel editing
                        </button>
                      )}
                    </div>
                  )}

                  {!map.stale && (
                    <details className="help more-options">
                      <summary>More options</summary>
                      <div className="help-body">
                        <p>
                          Regenerating creates a new draft from the saved import and replaces this
                          map, including its review decisions.
                        </p>
                        <button className="btn small" type="button" onClick={() => setRegenerateOpen(true)}>
                          Regenerate Change Map
                        </button>
                      </div>
                    </details>
                  )}
                </section>
              </>
            )}
          </div>

          <aside className="ws-rail" aria-label="Change Map guidance">
            <GuideCard title="How to read this map">
              <p>
                <strong>Codize draft</strong> means an AI-inferred suggestion. <strong>Added by
                you</strong> means your own wording. A source excerpt explains why Codize suggested
                something; it does not prove the suggestion is correct.
              </p>
            </GuideCard>
            <GuideCard title="What does “needs inspection” mean?">
              <p>
                Look at the code or behavior before deciding. You can confirm that you reviewed
                the map while honestly keeping uncertain and needs-inspection items visible.
              </p>
            </GuideCard>
            <GuideCard title="Already in a patch loop?">
              <p>
                Reviewing a Change Map can help rebuild a clear record of what changed and what
                still needs inspection. The same review flow works whether you are preventing a
                patch loop or recovering from one.
              </p>
            </GuideCard>
            <GuideCard title="Confirmation is not verification">
              <p>
                Confirmation records that you reviewed the map. Codize does not execute your code
                or independently prove that the implementation is correct.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
