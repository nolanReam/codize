"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  AI_CHANGE_CHOICES,
  CODING_CONFIDENCE_CHOICES,
  ENTRY_SITUATIONS,
  QUICK_START_STEPS,
  recommendationFor,
  SITUATION_LABELS,
  STARTING_RECOMMENDATIONS,
  TRAP_DEFINITION,
} from "@/lib/entryProfile";
import type {
  AiChangeState,
  CodingConfidence,
  EntryProfile,
  EntryProfileUpdate,
  EntrySituation,
} from "@/lib/types";

interface AdaptiveEntryProps {
  profile: EntryProfile | null;
  preferencesOnly?: boolean;
  onSave: (updates: EntryProfileUpdate) => Promise<EntryProfile>;
  onContinue: () => void;
}

export default function AdaptiveEntry({
  profile,
  preferencesOnly = false,
  onSave,
  onContinue,
}: AdaptiveEntryProps) {
  const initialStep = preferencesOnly
    ? "confidence"
    : !profile?.current_situation
      ? "situation"
      : !profile.coding_confidence
        ? "confidence"
        : profile.current_situation === "already_building" && !profile.ai_changed_files
          ? "ai_changes"
          : "recommendation";
  const [step, setStep] = useState<
    "situation" | "confidence" | "ai_changes" | "recommendation" | "saved"
  >(initialStep);
  const [situation, setSituation] = useState<EntrySituation | null>(
    profile?.current_situation ?? null
  );
  const [confidence, setConfidence] = useState<CodingConfidence | null>(
    profile?.coding_confidence ?? null
  );
  const [aiChanged, setAiChanged] = useState<AiChangeState | null>(
    profile?.ai_changed_files ?? null
  );
  const [currentProfile, setCurrentProfile] = useState(profile);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stepNumber = preferencesOnly
    ? 1
    : step === "situation"
      ? 1
      : step === "confidence"
        ? 2
        : step === "ai_changes"
          ? 3
          : situation === "already_building"
            ? 4
            : 3;
  const totalSteps = preferencesOnly ? 1 : situation === "already_building" ? 4 : 3;

  async function save(updates: EntryProfileUpdate, next: typeof step) {
    setBusy(true);
    setError(null);
    try {
      const saved = await onSave(updates);
      setCurrentProfile(saved);
      setStep(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn’t save that choice. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const recommendation = useMemo(
    () => recommendationFor(currentProfile),
    [currentProfile]
  );

  return (
    <section className="card primary entry-card" aria-labelledby="entry-heading">
      <div className="entry-progress" role="status" aria-live="polite">
        {preferencesOnly
          ? "Guidance preference"
          : step === "recommendation"
            ? "Recommended starting point"
            : `Step ${stepNumber} of ${totalSteps}`}
      </div>

      {step === "situation" && (
        <>
          <h2 id="entry-heading">Where are you right now?</h2>
          <p className="muted">Choose the closest fit. You can update this later.</p>
          <fieldset className="entry-choice-group">
            <legend className="sr-only">Current project situation</legend>
            {ENTRY_SITUATIONS.map((choice) => (
              <label className="entry-choice" key={choice.value}>
                <input
                  type="radio"
                  name="entry-situation"
                  value={choice.value}
                  checked={situation === choice.value}
                  onChange={() => {
                    setSituation(choice.value);
                    if (choice.value !== "already_building") setAiChanged(null);
                  }}
                />
                <span>
                  <strong>{choice.label}</strong>
                  <small>{choice.description}</small>
                </span>
              </label>
            ))}
          </fieldset>
          <EntryError error={error} />
          <button
            className="btn primary"
            type="button"
            disabled={busy || !situation}
            onClick={() =>
              situation &&
              void save(
                { current_situation: situation },
                currentProfile?.coding_confidence
                  ? situation === "already_building"
                    ? "ai_changes"
                    : "recommendation"
                  : "confidence"
              )
            }
          >
            {busy ? "Saving…" : "Continue"}
          </button>
        </>
      )}

      {step === "confidence" && (
        <>
          <h2 id="entry-heading">How comfortable are you with code right now?</h2>
          <p className="muted">This changes explanation depth, not which features you can use.</p>
          <fieldset className="entry-choice-group compact">
            <legend className="sr-only">Coding confidence</legend>
            {CODING_CONFIDENCE_CHOICES.map((choice) => (
              <label className="entry-choice" key={choice.value}>
                <input
                  type="radio"
                  name="coding-confidence"
                  value={choice.value}
                  checked={confidence === choice.value}
                  onChange={() => setConfidence(choice.value)}
                />
                <span><strong>{choice.label}</strong></span>
              </label>
            ))}
          </fieldset>
          <EntryError error={error} />
          <div className="row entry-actions">
            <button
              className="btn primary"
              type="button"
              disabled={busy || !confidence}
              onClick={() =>
                confidence &&
                void save(
                  { coding_confidence: confidence },
                  preferencesOnly
                    ? "saved"
                    : situation === "already_building" && !aiChanged
                      ? "ai_changes"
                      : "recommendation"
                )
              }
            >
              {busy ? "Saving…" : preferencesOnly ? "Save guidance preference" : "Continue"}
            </button>
            {!preferencesOnly && (
              <button className="btn" type="button" disabled={busy} onClick={() => setStep("situation")}>
                Back
              </button>
            )}
            {preferencesOnly && <Link className="btn" href="/app">Cancel</Link>}
          </div>
        </>
      )}

      {step === "ai_changes" && (
        <>
          <h2 id="entry-heading">Has AI already changed code or files in this project?</h2>
          <p className="muted">Choose “I am not sure” if you have an AI response but cannot tell exactly what changed.</p>
          <fieldset className="entry-choice-group compact">
            <legend className="sr-only">Whether AI changed project files</legend>
            {AI_CHANGE_CHOICES.map((choice) => (
              <label className="entry-choice" key={choice.value}>
                <input
                  type="radio"
                  name="ai-changed-files"
                  value={choice.value}
                  checked={aiChanged === choice.value}
                  onChange={() => setAiChanged(choice.value)}
                />
                <span><strong>{choice.label}</strong></span>
              </label>
            ))}
          </fieldset>
          <EntryError error={error} />
          <div className="row entry-actions">
            <button
              className="btn primary"
              type="button"
              disabled={busy || !aiChanged}
              onClick={() => aiChanged && void save({ ai_changed_files: aiChanged }, "recommendation")}
            >
              {busy ? "Saving…" : "Show my starting point"}
            </button>
            <button className="btn" type="button" disabled={busy} onClick={() => setStep("confidence")}>
              Back
            </button>
          </div>
        </>
      )}

      {step === "recommendation" && recommendation && (
        <div role="status" aria-live="polite">
          <p className="entry-kicker">Start here</p>
          <h2 id="entry-heading">{recommendation.label}</h2>
          <p className="entry-reason">{recommendation.reason}</p>
          {recommendation.id === "quick_start" && (
            <p className="muted">You will see the short recovery plan after your project workspace is ready.</p>
          )}
          <p className="muted">
            First, finish the existing project details so Codize can prepare your workspace.
            Codize will continue guiding you from this point.
          </p>
          <details className="help entry-why">
            <summary>Why this path?</summary>
            <p>
              This recommendation is based only on what you selected. It is not permanent, and
              saved workflow progress will take priority once you begin.
            </p>
          </details>
          <div className="row entry-actions">
            <button className="btn primary" type="button" onClick={onContinue}>
              Continue project details
            </button>
            <button className="btn" type="button" onClick={() => setStep("situation")}>
              Review choices
            </button>
          </div>
        </div>
      )}

      {step === "recommendation" && !recommendation && (
        <div role="alert" className="notice error">
          Your starting point could not be read safely. Review your choices and try again.
          <div style={{ marginTop: 10 }}>
            <button className="btn" type="button" onClick={() => setStep("situation")}>Review choices</button>
          </div>
        </div>
      )}

      {step === "saved" && (
        <div role="status" aria-live="polite">
          <p className="entry-kicker">Preference saved</p>
          <h2 id="entry-heading">Your workflow stays exactly where it is.</h2>
          <p className="muted">Only explanation depth changed. No project work or drafts were reset.</p>
          <Link className="btn primary" href="/app">Return to Project Home</Link>
        </div>
      )}
    </section>
  );
}

function EntryError({ error }: { error: string | null }) {
  return error ? <div className="notice error entry-error" role="alert">{error}</div> : null;
}

export function QuickStartPanel() {
  return (
    <section className="card primary quick-start-card" aria-labelledby="quick-start-title">
      <p className="entry-kicker">Recovery path</p>
      <h2 id="quick-start-title">The 80% Trap Quick Start</h2>
      <p>{TRAP_DEFINITION}</p>
      <p className="muted">This can happen during AI-assisted work. It does not mean you need to start over.</p>
      <ol className="quick-start-steps">
        {QUICK_START_STEPS.map((step) => <li key={step}>{step}</li>)}
      </ol>
      <p className="muted">
        The next page uses the existing Bring Back What Changed workflow. Paste or summarize the
        latest AI change there once—there is no separate recovery import.
      </p>
      <div className="row entry-actions">
        <Link className="btn primary" href="/app/phase/import">
          Bring Back What Changed
        </Link>
        <Link className="btn" href="/app">Back to Project Home</Link>
      </div>
    </section>
  );
}

export function StartingPathSummary({ profile }: { profile: EntryProfile }) {
  const recommendation = recommendationFor(profile);
  if (!profile.current_situation || !recommendation) return null;
  return (
    <section className="starting-path-summary" aria-labelledby="starting-path-title">
      <div>
        <p className="entry-kicker">Your starting path</p>
        <h3 id="starting-path-title">{SITUATION_LABELS[profile.current_situation]}</h3>
        <p className="muted">Started with {STARTING_RECOMMENDATIONS[recommendation.id].label}</p>
      </div>
      <Link className="text-link" href="/app/intake?preferences=1">
        Update guidance preferences
      </Link>
    </section>
  );
}
