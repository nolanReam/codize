"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import Async from "@/components/Async";
import { GuidedContinueAction } from "@/components/GuidedProjectNav";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import {
  ApiError,
  getEvidenceHandoffPreview,
  initializeEvidenceFromVerification,
} from "@/lib/api";
import { containsSecretMarker, useDraft } from "@/lib/drafts";
import {
  EVIDENCE_CONTENT_MAX,
  EVIDENCE_ENTRY_MAX,
  EVIDENCE_HONESTY_LINE,
  EVIDENCE_KIND_OPTIONS,
  EVIDENCE_PAGE_INTRO,
  EVIDENCE_PAGE_TITLE,
  EVIDENCE_STATUSES,
  EVIDENCE_TARGET_MAX,
  EVIDENCE_TEXT_MAX,
  canRebuildEvidenceFromPreview,
  deriveEvidenceSavePayload,
  eligibleEvidenceTargets,
  evidenceArtifactMode,
  evidenceCharacterCount,
  evidenceCompletionSummary,
  evidenceFormBlocker,
  evidenceKindLabel,
  evidenceKindOption,
  evidencePreviewState,
  evidenceResultDescription,
  evidenceResultLabel,
  evidenceStatusDescription,
  evidenceStatusLabel,
  ineligibleEvidenceTargets,
  isEvidenceHandoffPreview,
  isLinkedEvidenceArtifact,
  isLinkedEvidenceDirty,
  linkedEvidenceDraftSurface,
  linkedEvidenceDraftValue,
  linkedEvidenceProgress,
  linkedEvidenceServerRevision,
  normalizeEvidenceSelection,
  restoreLinkedEvidenceDraft,
  savedLinkedEvidenceProgress,
  safeEvidenceLink,
  selectedEvidenceTargetCount,
  shouldKeepEvidenceSaveNotice,
  targetFormFromEvidence,
  updateEvidenceSelection,
  validateEvidenceEntry,
  validateEvidenceTarget,
  type LinkedEvidenceDraft,
  type LinkedEvidenceFormState,
} from "@/lib/evidence";
import { useWorkflowSection } from "@/lib/useWorkflowSection";
import type {
  EvidenceArtifact,
  EvidenceEntry,
  EvidenceHandoffPreview,
  EvidenceKind,
  EvidenceSaveRequest,
  LinkedEvidenceArtifact,
  PhaseView,
  StoredEvidenceArtifact,
} from "@/lib/types";

const EMPTY_MANUAL_EVIDENCE: EvidenceArtifact = { entries: [], summary: null };

function EvidencePageHeading() {
  return (
    <>
      <h1 className="page-title">{EVIDENCE_PAGE_TITLE}</h1>
      <p className="page-sub">{EVIDENCE_PAGE_INTRO}</p>
      <p className="evidence-honesty">{EVIDENCE_HONESTY_LINE}</p>
    </>
  );
}

function PreviewUnavailable({ preview }: { preview: EvidenceHandoffPreview }) {
  const state = evidencePreviewState(preview);
  const content = {
    verification_required: {
      title: "Complete Verification first",
      body: "Perform the suggested checks and record what happened before adding supporting Evidence.",
      action: "Go to Verification",
    },
    incomplete_verification: {
      title: "Finish recording your Verification results",
      body: "Evidence comes after you record an outcome for every suggested check.",
      action: "Continue Verification",
    },
    stale_verification: {
      title: "Update Verification first",
      body: "Review changed after these Verification checks were created.",
      action: "Rebuild Verification",
    },
    zero_eligible: {
      title: "No performed checks are available for Evidence",
      body: "Evidence handoff is available for checks recorded as Passed or Failed.",
      action: "Review Verification results",
    },
    manual_verification: {
      title: "Manual Verification preserved",
      body: "This phase uses the original manual workflow, so its Evidence remains separate.",
      action: "Review Verification",
    },
    ready: {
      title: "Choose what to support with Evidence",
      body: "Select the performed checks you want to support with Evidence.",
      action: "Continue",
    },
  }[state];
  return (
    <div className="card primary evidence-empty">
      <h2>{content.title}</h2>
      <p>{content.body}</p>
      <Link className="btn primary" href="/app/phase/verify">
        {content.action}
      </Link>
      {state === "zero_eligible" && ineligibleEvidenceTargets(preview).length > 0 && (
        <IneligibleTargets targets={ineligibleEvidenceTargets(preview)} />
      )}
    </div>
  );
}

function IneligibleTargets({
  targets,
}: {
  targets: ReturnType<typeof ineligibleEvidenceTargets>;
}) {
  if (targets.length === 0) return null;
  return (
    <details className="help evidence-ineligible">
      <summary>Not available for Evidence handoff ({targets.length})</summary>
      <div className="help-body">
        {targets.map((target) => (
          <div className="evidence-ineligible-row" key={target.verification_target_id}>
            <strong>{evidenceResultLabel(target.result)}</strong>
            <p>{evidenceResultDescription(target.result)}</p>
            <p className="evidence-plain-text">{target.check}</p>
          </div>
        ))}
      </div>
    </details>
  );
}

function EvidenceSelectionPanel({
  preview,
  replaceExisting,
  busy,
  error,
  onCreate,
  onCancel,
}: {
  preview: EvidenceHandoffPreview;
  replaceExisting: boolean;
  busy: boolean;
  error: string | null;
  onCreate: (selectedIds: string[]) => Promise<boolean>;
  onCancel?: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const state = evidencePreviewState(preview);
  const eligible = eligibleEvidenceTargets(preview);
  const ineligible = ineligibleEvidenceTargets(preview);
  const normalized = normalizeEvidenceSelection(preview, selected);
  const selectedCount = selectedEvidenceTargetCount(normalized);

  useEffect(() => {
    setSelected([]);
    setConfirming(false);
    setSelectionError(null);
  }, [preview]);

  if (state !== "ready") return <PreviewUnavailable preview={preview} />;

  async function submit() {
    if (selectedCount === 0) return;
    if (selectedCount > EVIDENCE_TARGET_MAX) {
      setSelectionError(`Select at most ${EVIDENCE_TARGET_MAX} performed checks.`);
      return;
    }
    setSelectionError(null);
    await onCreate(normalized);
  }

  return (
    <section className="card primary evidence-selection" aria-labelledby="evidence-selection-title">
      <div className="linked-evidence-summary">
        <div>
          <span className="pill accent">Current Verification</span>
          <h2 id="evidence-selection-title">Choose what to support with Evidence</h2>
          <p>
            Select the performed checks you want to support with Evidence. Passed and failed
            checks may both have useful Evidence.
          </p>
        </div>
        <strong role="status" aria-live="polite">{selectedCount} selected</strong>
      </div>

      <div className="evidence-selection-list">
        {eligible.map((target) => {
          const checked = normalized.includes(target.verification_target_id);
          const inputId = `evidence-select-${target.verification_target_id}`;
          return (
            <div className={`evidence-selection-row${checked ? " selected" : ""}`} key={target.verification_target_id}>
              <label htmlFor={inputId} className="evidence-selection-control">
                <input
                  id={inputId}
                  type="checkbox"
                  checked={checked}
                  disabled={busy}
                  aria-label={`Select performed check: ${target.check} Recorded result: ${evidenceResultLabel(target.result)}`}
                  onChange={(event) => {
                    const update = updateEvidenceSelection(
                      preview,
                      selected,
                      target.verification_target_id,
                      event.target.checked
                    );
                    setSelected(update.selectedIds);
                    setSelectionError(update.limitReached
                      ? `Select at most ${EVIDENCE_TARGET_MAX} performed checks.`
                      : null);
                  }}
                />
                <span>Select this performed check</span>
              </label>
              <dl className="evidence-source-grid">
                <div><dt>Check performed</dt><dd>{target.check}</dd></div>
                <div>
                  <dt>Recorded result</dt>
                  <dd>
                    <span className={`pill ${target.result === "fail" ? "danger" : "ok"}`}>
                      {evidenceResultLabel(target.result)}
                    </span>
                    <small>{evidenceResultDescription(target.result)}</small>
                  </dd>
                </div>
                <div><dt>What you recorded</dt><dd>{target.result_notes || "No additional result notes were saved."}</dd></div>
              </dl>
              {target.result === "fail" && (
                <p className="hint">Evidence can document a failure, error, or unexpected result.</p>
              )}
            </div>
          );
        })}
      </div>

      {selectionError && <div className="notice error" role="alert">{selectionError}</div>}
      {error && <div className="notice error" role="alert">{error}</div>}
      {busy && (
        <div className="notice info" role="status" aria-live="polite">
          <strong>Preparing your Evidence workspace...</strong>
          <p>Codize is linking the performed checks you selected. No Evidence is added automatically.</p>
        </div>
      )}

      {!replaceExisting || !confirming ? (
        <div className="row evidence-selection-actions">
          <button
            className="btn primary"
            type="button"
            disabled={busy || selectedCount === 0 || selectedCount > EVIDENCE_TARGET_MAX}
            onClick={() => replaceExisting ? setConfirming(true) : void submit()}
          >
            {busy ? "Preparing…" : replaceExisting ? "Continue to rebuild" : "Create Evidence workspace"}
          </button>
          {onCancel && (
            <button className="btn" type="button" disabled={busy} onClick={onCancel}>
              Keep current Evidence
            </button>
          )}
        </div>
      ) : (
        <div className="replacement-warning" role="group" aria-labelledby="evidence-rebuild-title">
          <strong id="evidence-rebuild-title">Replace this Evidence workspace?</strong>
          <p>
            Rebuilding replaces the current Evidence targets, Evidence entries, explanations, and
            unavailable reasons with a new workspace from the current Verification results.
          </p>
          <div className="row">
            <button className="btn primary" type="button" disabled={busy} onClick={() => void submit()}>
              {busy ? "Preparing…" : "Rebuild Evidence"}
            </button>
            <button className="btn" type="button" disabled={busy} onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
      <IneligibleTargets targets={ineligible} />
    </section>
  );
}

function EvidenceEntryEditor({
  entry,
  targetIndex,
  entryIndex,
  disabled,
  onChange,
  onRemove,
}: {
  entry: EvidenceEntry;
  targetIndex: number;
  entryIndex: number;
  disabled: boolean;
  onChange: (entry: EvidenceEntry) => void;
  onRemove: () => void;
}) {
  const error = validateEvidenceEntry(entry);
  const kindId = `evidence-kind-${targetIndex}-${entryIndex}`;
  const contentId = `evidence-content-${targetIndex}-${entryIndex}`;
  const errorId = `${contentId}-error`;
  const safeLink = safeEvidenceLink(entry);
  const option = evidenceKindOption(entry.kind);
  return (
    <div className="evidence-entry">
      <div className="evidence-entry-heading">
        <strong>Evidence {entryIndex + 1}</strong>
        <button
          className="btn small"
          type="button"
          disabled={disabled}
          aria-label={`Remove Evidence ${entryIndex + 1}`}
          onClick={onRemove}
        >
          Remove
        </button>
      </div>
      <div className="field">
        <label htmlFor={kindId}>Evidence type</label>
        <select
          id={kindId}
          value={entry.kind}
          disabled={disabled}
          onChange={(event) => onChange({ ...entry, kind: event.target.value as EvidenceKind })}
        >
          {EVIDENCE_KIND_OPTIONS.map((kind) => (
            <option key={kind.value} value={kind.value}>{kind.label}</option>
          ))}
        </select>
        <p className="hint">{option.guidance}</p>
      </div>
      <div className="field">
        <label htmlFor={contentId}>{evidenceKindLabel(entry.kind)}</label>
        <textarea
          id={contentId}
          rows={4}
          value={entry.content}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : `${contentId}-meta`}
          onChange={(event) => onChange({ ...entry, content: event.target.value })}
          placeholder={option.placeholder}
        />
        <div className="field-meta" id={`${contentId}-meta`}>
          <span>Student-provided material; Codize does not fetch or execute it.</span>
          <span className={evidenceCharacterCount(entry.content) > EVIDENCE_CONTENT_MAX ? "field-error" : ""}>
            {evidenceCharacterCount(entry.content).toLocaleString()} / {EVIDENCE_CONTENT_MAX.toLocaleString()}
          </span>
        </div>
        {error && <p className="field-error" id={errorId}>{error}</p>}
        {safeLink && (
          <a href={safeLink} target="_blank" rel="noopener noreferrer" className="mono evidence-safe-link">
            Open saved link in a new tab
          </a>
        )}
      </div>
    </div>
  );
}

function LinkedEvidenceBoard({
  evidence,
  phase,
  saving,
  saveError,
  replacementPanel,
  onSave,
  onStartRebuild,
}: {
  evidence: LinkedEvidenceArtifact;
  phase: PhaseView;
  saving: boolean;
  saveError: string | null;
  replacementPanel: React.ReactNode;
  onSave: (payload: EvidenceSaveRequest) => Promise<StoredEvidenceArtifact | null>;
  onStartRebuild: () => void;
}) {
  const [form, setForm] = useState<LinkedEvidenceFormState>(() => targetFormFromEvidence(evidence));
  const [justSaved, setJustSaved] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const [moreOptionsOpen, setMoreOptionsOpen] = useState(false);
  const acknowledgedSaveRevision = useRef<string | null>(null);
  const evidenceRef = useRef(evidence);
  evidenceRef.current = evidence;
  const serverRevision = linkedEvidenceServerRevision(evidence);

  useEffect(() => {
    setForm(targetFormFromEvidence(evidenceRef.current));
    if (shouldKeepEvidenceSaveNotice(acknowledgedSaveRevision.current, serverRevision)) {
      acknowledgedSaveRevision.current = null;
    } else {
      setJustSaved(false);
    }
  }, [serverRevision]);

  const draftSurface = linkedEvidenceDraftSurface(phase.phase, evidence);
  const draft = useDraft<LinkedEvidenceDraft>(draftSurface);
  const draftAppliedFor = useRef<string | null>(null);
  useEffect(() => {
    if (!draft.ready || draft.loadedSurface !== draftSurface || draftAppliedFor.current === draftSurface) return;
    draftAppliedFor.current = draftSurface;
    const restored = restoreLinkedEvidenceDraft(evidence, draft.restored);
    if (restored && isLinkedEvidenceDirty(evidence, restored)) setForm(restored);
    else if (draft.restored) draft.clear();
  }, [draft, draftSurface, evidence]);

  const dirty = useMemo(() => isLinkedEvidenceDirty(evidence, form), [evidence, form]);
  const blocker = useMemo(() => evidenceFormBlocker(evidence, form), [evidence, form]);
  const progress = useMemo(() => savedLinkedEvidenceProgress(evidence), [evidence]);
  const draftProgress = useMemo(() => linkedEvidenceProgress(evidence, form), [evidence, form]);
  const draftBlocked = dirty && containsSecretMarker(JSON.stringify(form));
  const saveLocalDraft = draft.save;
  useEffect(() => {
    if (draftAppliedFor.current !== draftSurface || evidence.stale) return;
    if (dirty) saveLocalDraft(linkedEvidenceDraftValue(evidence, form));
  }, [dirty, draftSurface, evidence, form, saveLocalDraft]);

  function updateTarget(targetId: string, patch: Partial<LinkedEvidenceFormState[string]>) {
    setForm((current) => ({
      ...current,
      [targetId]: { ...current[targetId], ...patch },
    }));
    setJustSaved(false);
  }

  async function save() {
    if (!dirty || blocker || evidence.stale || draftBlocked) return;
    const result = await onSave(deriveEvidenceSavePayload(evidence, form));
    if (result && isLinkedEvidenceArtifact(result)) {
      acknowledgedSaveRevision.current = linkedEvidenceServerRevision(result);
      draft.clear();
      setForm(targetFormFromEvidence(result));
      setJustSaved(true);
      setAnnouncement("Evidence saved.");
    }
  }

  return (
    <>
      <EvidencePageHeading />
      <div className="workspace">
        <div>
          <p className="muted evidence-phase-line">Phase {phase.phase}: {phase.phase_title}</p>

          {evidence.stale && (
            <div className="notice info stale-notice" role="status">
              <strong>Verification changed after this Evidence workspace was created.</strong>
              <p>Rebuild Evidence to use the current saved Verification results.</p>
              {!replacementPanel && (
                <button className="btn primary" type="button" onClick={onStartRebuild}>
                  Rebuild Evidence from current Verification
                </button>
              )}
            </div>
          )}

          {replacementPanel}

          <section className="card primary linked-evidence-surface" aria-labelledby="linked-evidence-heading">
            <div className="linked-evidence-summary">
              <div>
                <span className={`pill ${evidence.stale ? "warn" : "accent"}`}>
                  {evidence.stale ? "Needs rebuild" : "Current Evidence"}
                </span>
                <h2 id="linked-evidence-heading">Evidence</h2>
                <p>Created from the performed Verification checks you selected.</p>
              </div>
              <strong>{evidenceCompletionSummary(progress)}</strong>
            </div>
            <p className="evidence-source-statement">
              Verification results describe what you observed. Evidence is the supporting material you add.
            </p>

            <div
              className="review-meter evidence-meter"
              role="progressbar"
              aria-label="Evidence records addressed"
              aria-valuemin={0}
              aria-valuemax={progress.total}
              aria-valuenow={progress.addressed}
              aria-valuetext={evidenceCompletionSummary(progress)}
            >
              <span style={{ width: `${progress.total ? (progress.addressed / progress.total) * 100 : 0}%` }} />
            </div>

            {progress.addressed > 0 && (
              <dl className="evidence-progress-summary" aria-label="Evidence record summary">
                <div><dt>Evidence recorded</dt><dd>{progress.recorded}</dd></div>
                <div><dt>Evidence unavailable</dt><dd>{progress.unavailable}</dd></div>
                <div><dt>Not addressed</dt><dd>{progress.unaddressed}</dd></div>
                <div><dt>Evidence entries</dt><dd>{progress.entries}</dd></div>
              </dl>
            )}

            <div className="linked-evidence-targets">
              {evidence.evidence_targets.map((target, targetIndex) => {
                const targetForm = form[target.evidence_target_id];
                if (!targetForm) return null;
                const validation = validateEvidenceTarget(targetForm);
                const disabled = evidence.stale || saving;
                return (
                  <section className="linked-evidence-target" key={target.evidence_target_id} aria-labelledby={`evidence-target-${targetIndex}`}>
                    <div className="evidence-source">
                      <span className="evidence-source-label">From your Verification</span>
                      <h3 id={`evidence-target-${targetIndex}`}>
                        Check performed<span className="sr-only">: {target.check_snapshot}</span>
                      </h3>
                      <p className="evidence-plain-text">{target.check_snapshot}</p>
                      <dl className="evidence-source-grid compact">
                        <div>
                          <dt>Recorded result</dt>
                          <dd>
                            <span className={`pill ${target.verification_result_snapshot === "fail" ? "danger" : "ok"}`}>
                              {evidenceResultLabel(target.verification_result_snapshot)}
                            </span>
                            <small>{evidenceResultDescription(target.verification_result_snapshot)}</small>
                          </dd>
                        </div>
                        <div><dt>What you recorded</dt><dd>{target.verification_result_notes_snapshot || "No additional result notes were saved."}</dd></div>
                      </dl>
                    </div>

                    <fieldset className="evidence-status-picker" disabled={disabled}>
                      <legend>Your Evidence decision</legend>
                      <div className="evidence-status-grid">
                        {EVIDENCE_STATUSES.map((status) => (
                          <label className={`evidence-status${targetForm.status === status ? " active" : ""}`} key={status}>
                            <input
                              type="radio"
                              name={`evidence-status-${target.evidence_target_id}`}
                              value={status}
                              checked={targetForm.status === status}
                              onChange={() => {
                                updateTarget(target.evidence_target_id, { status });
                                setAnnouncement(`${evidenceStatusLabel(status)} selected.`);
                              }}
                            />
                            <span><strong>{evidenceStatusLabel(status)}</strong><small>{evidenceStatusDescription(status)}</small></span>
                          </label>
                        ))}
                      </div>
                    </fieldset>

                    {targetForm.status === "evidence_recorded" && (
                      <div className="evidence-active-fields">
                        <div className="evidence-field-heading">
                          <div>
                            <h4>Supporting Evidence</h4>
                            <p>Add material that supports what you observed. The Verification result itself is not an entry.</p>
                          </div>
                          <span className="muted">{targetForm.entries.length} entries</span>
                        </div>
                        {targetForm.entries.map((entry, entryIndex) => (
                          <EvidenceEntryEditor
                            key={entryIndex}
                            entry={entry}
                            targetIndex={targetIndex}
                            entryIndex={entryIndex}
                            disabled={disabled}
                            onChange={(next) => updateTarget(target.evidence_target_id, {
                              entries: targetForm.entries.map((current, index) => index === entryIndex ? next : current),
                            })}
                            onRemove={() => updateTarget(target.evidence_target_id, {
                              entries: targetForm.entries.filter((_, index) => index !== entryIndex),
                            })}
                          />
                        ))}
                        <button
                          className="btn"
                          type="button"
                          disabled={disabled || draftProgress.entries >= EVIDENCE_ENTRY_MAX}
                          onClick={() => updateTarget(target.evidence_target_id, {
                            entries: [...targetForm.entries, { kind: "screenshot_note", content: "" }],
                          })}
                        >
                          Add Evidence
                        </button>
                        {validation.entries && <p className="field-error" role="alert">{validation.entries}</p>}

                        <div className="field evidence-explanation">
                          <label htmlFor={`evidence-explanation-${targetIndex}`}>What does this Evidence show? <span className="muted">(optional)</span></label>
                          <textarea
                            id={`evidence-explanation-${targetIndex}`}
                            rows={3}
                            value={targetForm.explanation}
                            disabled={disabled}
                            aria-invalid={Boolean(validation.explanation)}
                            aria-describedby={validation.explanation ? `evidence-explanation-${targetIndex}-error` : undefined}
                            onChange={(event) => updateTarget(target.evidence_target_id, { explanation: event.target.value })}
                            placeholder="Explain how the material relates to the check and result above."
                          />
                          <div className="field-meta">
                            <span>Explain the relationship without claiming total correctness.</span>
                            <span className={evidenceCharacterCount(targetForm.explanation) > EVIDENCE_TEXT_MAX ? "field-error" : ""}>
                              {evidenceCharacterCount(targetForm.explanation).toLocaleString()} / {EVIDENCE_TEXT_MAX.toLocaleString()}
                            </span>
                          </div>
                          {validation.explanation && <p className="field-error" id={`evidence-explanation-${targetIndex}-error`}>{validation.explanation}</p>}
                        </div>
                      </div>
                    )}

                    {targetForm.status === "evidence_unavailable" && (
                      <div className="evidence-active-fields">
                        <div className="field">
                          <label htmlFor={`evidence-unavailable-${targetIndex}`}>Why is Evidence unavailable?</label>
                          <textarea
                            id={`evidence-unavailable-${targetIndex}`}
                            rows={3}
                            value={targetForm.unavailableReason}
                            disabled={disabled}
                            required
                            aria-invalid={Boolean(validation.unavailableReason)}
                            aria-describedby={`evidence-unavailable-${targetIndex}-hint${validation.unavailableReason ? ` evidence-unavailable-${targetIndex}-error` : ""}`}
                            onChange={(event) => updateTarget(target.evidence_target_id, { unavailableReason: event.target.value })}
                            placeholder="For example: the hosted logs expired before I could save them."
                          />
                          <div className="field-meta" id={`evidence-unavailable-${targetIndex}-hint`}>
                            <span>This explanation stays in the project record, but it is not Evidence.</span>
                            <span className={evidenceCharacterCount(targetForm.unavailableReason) > EVIDENCE_TEXT_MAX ? "field-error" : ""}>
                              {evidenceCharacterCount(targetForm.unavailableReason).toLocaleString()} / {EVIDENCE_TEXT_MAX.toLocaleString()}
                            </span>
                          </div>
                          {validation.unavailableReason && <p className="field-error" id={`evidence-unavailable-${targetIndex}-error`}>{validation.unavailableReason}</p>}
                        </div>
                      </div>
                    )}
                  </section>
                );
              })}
            </div>

            {draftBlocked && (
              <div className="notice error" role="alert">
                This draft looks like it contains a secret. Remove the key-like text before saving;
                Codize is not keeping this draft on this device.
              </div>
            )}
            {blocker && dirty && <p className="field-error" role="alert">{blocker}</p>}
            {dirty && !evidence.stale && (
              <SaveBar
                saving={saving}
                saveError={saveError}
                savedAt={null}
                onSave={() => void save()}
                label="Save Evidence"
                disabled={Boolean(blocker) || draftBlocked}
              />
            )}
            {!dirty && saveError && <div className="notice error" role="alert">{saveError}</div>}
            {justSaved && <div className="notice ok" role="status"><strong>Evidence saved.</strong></div>}

            {!evidence.stale && !dirty && evidence.evidence_record_complete && (
              <div className="evidence-complete" role="status">
                <strong>Evidence record complete</strong>
                <p>Every selected Verification result now has supporting Evidence or an explanation that Evidence is unavailable.</p>
                <p>This records the Evidence available for these checks. It does not prove the entire implementation is correct.</p>
                <GuidedContinueAction className="btn primary" />
              </div>
            )}
          </section>

          {!evidence.stale && !replacementPanel && (
            <details className="help more-options" open={moreOptionsOpen} onToggle={(event) => setMoreOptionsOpen(event.currentTarget.open)}>
              <summary>More options</summary>
              <div className="help-body">
                <p>Rebuild only when you deliberately want a new workspace from current Verification results.</p>
                <button className="btn" type="button" onClick={onStartRebuild}>Rebuild from Verification</button>
              </div>
            </details>
          )}
        </div>

        <aside className="ws-rail" aria-label="Guidance">
          <GuideCard title="Result versus Evidence">
            <p>A Verification result records what happened. Evidence is the supporting material you choose to keep with it.</p>
          </GuideCard>
          <GuideCard title="Failed checks are useful">
            <p>Evidence can document a failure, error, or unexpected result. It does not turn that failure into a pass.</p>
          </GuideCard>
          <GuideCard title="Already in a patch loop?">
            <p>Save the output, error, or observation before asking AI for another patch.</p>
          </GuideCard>
        </aside>
      </div>
      <p className="sr-only" role="status" aria-live="polite">
        {saving ? "Saving Evidence." : announcement || (justSaved ? "Evidence saved." : "")}
      </p>
    </>
  );
}

function LegacyEvidencePanel({
  artifact,
  phase,
  saving,
  saveError,
  savedAt,
  replacementReady,
  replacementPanel,
  onSave,
  onStartReplacement,
}: {
  artifact: EvidenceArtifact;
  phase: PhaseView;
  saving: boolean;
  saveError: string | null;
  savedAt: string | null;
  replacementReady: boolean;
  replacementPanel: React.ReactNode;
  onSave: (payload: EvidenceSaveRequest) => Promise<StoredEvidenceArtifact | null>;
  onStartReplacement: () => void;
}) {
  const [entries, setEntries] = useState<EvidenceEntry[]>(artifact.entries ?? []);
  const [summary, setSummary] = useState(artifact.summary ?? "");
  const [kind, setKind] = useState<EvidenceKind>("screenshot_note");
  const [content, setContent] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setEntries(artifact.entries ?? []);
    setSummary(artifact.summary ?? "");
  }, [artifact]);

  type EvidenceDraft = { entries: EvidenceEntry[]; summary: string; kind: EvidenceKind; content: string };
  const draft = useDraft<EvidenceDraft>(`evidence:${phase.phase}`);
  const draftApplied = useRef(false);
  useEffect(() => {
    if (!draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) {
      setEntries(draft.restored.entries ?? []);
      setSummary(draft.restored.summary ?? "");
      setKind(draft.restored.kind ?? "screenshot_note");
      setContent(draft.restored.content ?? "");
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
    saveDraft({ entries, summary, kind, content });
  }, [entries, summary, kind, content, saveDraft]);

  function addEntry() {
    const trimmed = content.trim();
    if (!trimmed) return;
    if (entries.length >= EVIDENCE_ENTRY_MAX) {
      setFormError(`Evidence is capped at ${EVIDENCE_ENTRY_MAX} entries per phase—remove one first.`);
      return;
    }
    const next = { kind, content: trimmed };
    const error = validateEvidenceEntry(next);
    if (error) {
      setFormError(error);
      return;
    }
    setFormError(null);
    setEntries([...entries, next]);
    setContent("");
  }

  async function save() {
    const result = await onSave({ entries, summary: summary.trim() ? summary.trim() : null });
    if (result) {
      skipDraftEcho.current = true;
      draft.clear();
    }
  }

  return (
    <>
      <h1 className="page-title">Evidence</h1>
      <p className="page-sub">Keep one useful piece of supporting material for this phase.</p>
      <div className="workspace">
        <div>
          <p className="muted evidence-phase-line">Evidence for Phase {phase.phase}: {phase.phase_title}</p>
          {replacementPanel}
          <div className="card primary">
            <h2>Add one piece of Evidence</h2>
            {formError && <div className="notice error" role="alert">{formError}</div>}
            <div className="chips" style={{ marginTop: 0 }}>
              {EVIDENCE_KIND_OPTIONS.filter((option) => option.primary).map((option) => (
                <button key={option.value} type="button" className={`chip${kind === option.value ? " active" : ""}`} onClick={() => setKind(option.value)}>
                  {option.label}
                </button>
              ))}
            </div>
            <details className="help">
              <summary>More types</summary>
              <div className="help-body"><div className="chips" style={{ marginTop: 0 }}>
                {EVIDENCE_KIND_OPTIONS.filter((option) => !option.primary).map((option) => (
                  <button key={option.value} type="button" className={`chip${kind === option.value ? " active" : ""}`} onClick={() => setKind(option.value)}>
                    {option.label}
                  </button>
                ))}
              </div></div>
            </details>
            <div className="field" style={{ marginTop: 10 }}>
              <label htmlFor="manual-evidence-content">{evidenceKindLabel(kind)}</label>
              <textarea id="manual-evidence-content" rows={3} value={content} onChange={(event) => setContent(event.target.value)} placeholder={evidenceKindOption(kind).placeholder} />
              <div className="field-meta"><span>{evidenceKindOption(kind).guidance}</span><span>{evidenceCharacterCount(content).toLocaleString()} / {EVIDENCE_CONTENT_MAX.toLocaleString()}</span></div>
            </div>
            <button className="btn primary" type="button" onClick={addEntry} disabled={!content.trim()}>Add entry</button>
          </div>

          <div className="card">
            <h2>Collected Evidence ({entries.length}/{EVIDENCE_ENTRY_MAX})</h2>
            {entries.length === 0 && <p className="empty">Nothing attached yet—add one useful piece when it is available.</p>}
            {entries.map((entry, index) => (
              <div className="task" key={`${index}-${entry.kind}`}>
                <span className="tag">{evidenceKindLabel(entry.kind)}</span>
                <span className="mono evidence-plain-text" style={{ flex: 1 }}>{entry.content}</span>
                <button className="btn small" type="button" onClick={() => setEntries(entries.filter((_, entryIndex) => entryIndex !== index))}>Remove</button>
              </div>
            ))}
            <div className="field" style={{ marginTop: 14 }}>
              <label htmlFor="manual-evidence-summary">What does this Evidence show, in one or two sentences?</label>
              <textarea id="manual-evidence-summary" rows={2} value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Explain what the material supports and what remains uncertain." />
              <div className="field-meta"><span>Student-provided summary.</span><span>{evidenceCharacterCount(summary).toLocaleString()} / {EVIDENCE_TEXT_MAX.toLocaleString()}</span></div>
            </div>
          </div>

          <SaveBar saving={saving} saveError={saveError} savedAt={savedAt} onSave={() => void save()} label="Save evidence" />

          {replacementReady && !replacementPanel && (
            <details className="help more-options">
              <summary>More options</summary>
              <div className="help-body">
                <p>Starting from Verification replaces the current Evidence work for this phase.</p>
                <button className="btn" type="button" onClick={onStartReplacement}>Start over from Verification</button>
              </div>
            </details>
          )}
        </div>
        <aside className="ws-rail" aria-label="Guidance">
          <GuideCard title="Existing Evidence preserved"><p>This phase uses the original manual Evidence format. Codize will not convert or replace it unless you deliberately start over from Verification.</p></GuideCard>
          <GuideCard title="Your text is kept"><p>Unsaved manual Evidence stays on this device for your account and phase. Save evidence to store it with your project.</p></GuideCard>
        </aside>
      </div>
    </>
  );
}

export default function EvidencePanelPage() {
  const wf = useWorkflowSection("evidence");
  const [preview, setPreview] = useState<EvidenceHandoffPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(false);
  const [initializationError, setInitializationError] = useState<string | null>(null);
  const [replacementOpen, setReplacementOpen] = useState(false);
  const mode = evidenceArtifactMode(wf.stored);

  const loadPreview = useCallback(async () => {
    if (!wf.phase) return null;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const result = await getEvidenceHandoffPreview(wf.phase.phase);
      if (!isEvidenceHandoffPreview(result)) {
        setPreviewError("The Verification handoff could not be read safely. Reload and try again.");
        return null;
      }
      setPreview(result);
      return result;
    } catch (error) {
      setPreviewError(error instanceof ApiError ? error.message : "Couldn’t load the Verification handoff.");
      return null;
    } finally {
      setPreviewLoading(false);
    }
  }, [wf.phase]);

  useEffect(() => {
    if (wf.loading || !wf.phase || mode === "linked" || mode === "invalid_linked") return;
    void loadPreview();
  }, [loadPreview, mode, wf.loading, wf.phase]);

  if (wf.notReady) return <NotReady title="Evidence" />;

  async function initialize(selectedIds: string[], replaceExisting: boolean): Promise<boolean> {
    if (!wf.phase || initializing) return false;
    setInitializing(true);
    setInitializationError(null);
    try {
      const result = await initializeEvidenceFromVerification(wf.phase.phase, selectedIds, replaceExisting);
      wf.applyArtifact(result.artifact);
      setReplacementOpen(false);
      setPreview(null);
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409 && !replaceExisting) {
        await wf.reload();
      } else {
        setInitializationError(error instanceof ApiError ? error.message : "Couldn’t prepare this Evidence workspace. Try again.");
      }
      return false;
    } finally {
      setInitializing(false);
    }
  }

  async function startReplacement() {
    setReplacementOpen(true);
    setInitializationError(null);
    await loadPreview();
  }

  const replacementPanel = replacementOpen ? (
    previewLoading ? (
      <div className="card evidence-rebuild-loading" role="status">Loading current Verification results…</div>
    ) : preview ? (
      <EvidenceSelectionPanel
        preview={preview}
        replaceExisting
        busy={initializing}
        error={initializationError}
        onCreate={(ids) => initialize(ids, true)}
        onCancel={() => {
          setReplacementOpen(false);
          setInitializationError(null);
        }}
      />
    ) : (
      <div className="notice error" role="alert">
        {previewError || "Couldn’t load current Verification results."}
        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn" type="button" onClick={() => void loadPreview()}>Retry</button>
          <button className="btn" type="button" onClick={() => setReplacementOpen(false)}>Keep current Evidence</button>
        </div>
      </div>
    )
  ) : null;

  return (
    <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
      {wf.phase && (() => {
        if (mode === "invalid_linked") {
          return (
            <>
              <EvidencePageHeading />
              <div className="notice error" role="alert">
                This linked Evidence record could not be read safely.
                <div style={{ marginTop: 10 }}><button className="btn" type="button" onClick={wf.reload}>Reload</button></div>
              </div>
            </>
          );
        }
        if (mode === "linked" && isLinkedEvidenceArtifact(wf.stored)) {
          return (
            <LinkedEvidenceBoard
              evidence={wf.stored}
              phase={wf.phase}
              saving={wf.saving}
              saveError={wf.saveError}
              replacementPanel={replacementPanel}
              onSave={wf.save}
              onStartRebuild={() => void startReplacement()}
            />
          );
        }
        if (mode === "legacy" && wf.stored) {
          return (
            <LegacyEvidencePanel
              artifact={wf.stored}
              phase={wf.phase}
              saving={wf.saving}
              saveError={wf.saveError}
              savedAt={wf.savedAt}
              replacementReady={canRebuildEvidenceFromPreview(preview)}
              replacementPanel={replacementPanel}
              onSave={wf.save}
              onStartReplacement={() => void startReplacement()}
            />
          );
        }
        if (previewLoading) {
          return (
            <>
              <EvidencePageHeading />
              <div className="card primary evidence-initializing" role="status">Loading saved Verification results…</div>
            </>
          );
        }
        if (previewError || !preview) {
          return (
            <>
              <EvidencePageHeading />
              <div className="notice error" role="alert">
                {previewError || "Couldn’t load the Verification handoff."}
                <div style={{ marginTop: 10 }}><button className="btn" type="button" onClick={() => void loadPreview()}>Retry</button></div>
              </div>
            </>
          );
        }
        if (evidencePreviewState(preview) === "manual_verification") {
          return (
            <LegacyEvidencePanel
              artifact={EMPTY_MANUAL_EVIDENCE}
              phase={wf.phase}
              saving={wf.saving}
              saveError={wf.saveError}
              savedAt={wf.savedAt}
              replacementReady={false}
              replacementPanel={null}
              onSave={wf.save}
              onStartReplacement={() => undefined}
            />
          );
        }
        return (
          <>
            <EvidencePageHeading />
            <div className="workspace">
              <div>
                <p className="muted evidence-phase-line">Phase {wf.phase.phase}: {wf.phase.phase_title}</p>
                {evidencePreviewState(preview) === "ready" ? (
                  <EvidenceSelectionPanel preview={preview} replaceExisting={false} busy={initializing} error={initializationError} onCreate={(ids) => initialize(ids, false)} />
                ) : (
                  <PreviewUnavailable preview={preview} />
                )}
              </div>
              <aside className="ws-rail" aria-label="Guidance">
                <GuideCard title="Result versus Evidence"><p>A result records what happened. Evidence is the material you deliberately keep with that result.</p></GuideCard>
                <GuideCard title="Keep it while it is clear"><p>Save the useful output, screenshot, response, link, or observation before the next patch changes the context.</p></GuideCard>
              </aside>
            </div>
          </>
        );
      })()}
    </Async>
  );
}
