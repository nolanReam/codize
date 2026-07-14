"use client";

import React from "react";

import {
  VERIFICATION_HONESTY_LINE,
  VERIFICATION_RESULTS,
  VERIFICATION_TEXT_MAX,
  resultNotesGuidance,
  resultNotesLabel,
  verificationCharacterCount,
  verificationResultDescription,
  verificationResultLabel,
  validateVerificationTarget,
  type LinkedVerificationTargetForm,
} from "../lib/verification";
import type { LinkedVerificationTarget, VerificationResult } from "../lib/types";

export function VerificationSourceSnapshot({
  target,
}: {
  target: LinkedVerificationTarget;
}) {
  return (
    <div className="verification-source" aria-label="From your Review">
      <span className="verification-source-label">From your Review</span>
      <p className="verification-source-text">{target.source_text}</p>
      {target.source_rationale && (
        <div className="verification-rationale">
          <span>Why you marked this for testing</span>
          <p>{target.source_rationale}</p>
        </div>
      )}
    </div>
  );
}

export function SuggestedVerificationCheck({
  target,
}: {
  target: LinkedVerificationTarget;
}) {
  return (
    <div className="verification-suggestion">
      <span className="verification-source-label">Suggested check</span>
      <p>{target.suggested_check}</p>
      <small>Use this as written or adjust it to match what you can actually test.</small>
    </div>
  );
}

export default function LinkedVerificationTargetRow({
  target,
  index,
  form,
  disabled,
  onChange,
}: {
  target: LinkedVerificationTarget;
  index: number;
  form: LinkedVerificationTargetForm;
  disabled: boolean;
  onChange: (patch: Partial<LinkedVerificationTargetForm>) => void;
}) {
  const prefix = `verification-check-${index + 1}`;
  const errors = validateVerificationTarget(form);
  const checkCount = verificationCharacterCount(form.studentCheck);
  const notesCount = verificationCharacterCount(form.resultNotes);
  const usingSuggestion = form.studentCheck.trim() === target.suggested_check;

  return (
    <article className="linked-verification-target">
      <VerificationSourceSnapshot target={target} />
      <SuggestedVerificationCheck target={target} />

      <div className="field verification-student-check">
        <div className="verification-field-heading">
          <label htmlFor={`${prefix}-student-check`}>Check you will perform</label>
          <button
            className="btn small"
            type="button"
            disabled={disabled || usingSuggestion}
            onClick={() => onChange({ studentCheck: target.suggested_check })}
          >
            {usingSuggestion ? "Using suggested check" : "Use suggested check"}
          </button>
        </div>
        <textarea
          id={`${prefix}-student-check`}
          rows={3}
          value={form.studentCheck}
          disabled={disabled}
          onChange={(event) => onChange({ studentCheck: event.target.value })}
          placeholder="Use the suggested check, or write the check you can actually perform."
          aria-invalid={Boolean(errors.studentCheck)}
          aria-describedby={`${prefix}-student-check-help${errors.studentCheck ? ` ${prefix}-student-check-error` : ""}`}
        />
        <div className="field-meta" id={`${prefix}-student-check-help`}>
          <span>
            {form.studentCheck.trim()
              ? "Your wording will be saved for this check."
              : "If left blank, the suggested wording above remains the effective check."}
          </span>
          <span className={checkCount > VERIFICATION_TEXT_MAX ? "field-error" : ""}>
            {checkCount.toLocaleString()} / {VERIFICATION_TEXT_MAX.toLocaleString()}
          </span>
        </div>
        {errors.studentCheck && (
          <p className="field-error" id={`${prefix}-student-check-error`}>
            {errors.studentCheck}
          </p>
        )}
      </div>

      <fieldset className="verification-result-picker" disabled={disabled}>
        <legend>Your result</legend>
        <p className="hint">{VERIFICATION_HONESTY_LINE}</p>
        <div className="verification-result-grid">
          {VERIFICATION_RESULTS.map((result) => {
            const value = result ?? "unrecorded";
            const inputId = `${prefix}-${value}`;
            return (
              <label
                className={`verification-result${form.result === result ? " active" : ""}${result ? ` ${result}` : ""}`}
                key={value}
                htmlFor={inputId}
              >
                <input
                  id={inputId}
                  type="radio"
                  name={`${prefix}-result`}
                  value={value}
                  checked={form.result === result}
                  disabled={disabled}
                  onChange={() =>
                    onChange({
                      result,
                      resultNotes: form.result === result ? form.resultNotes : "",
                    })
                  }
                />
                <span>
                  <strong>{verificationResultLabel(result)}</strong>
                  <small>{verificationResultDescription(result)}</small>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {form.result !== null && (
        <div className="field verification-result-notes">
          <label htmlFor={`${prefix}-result-notes`}>
            {resultNotesLabel(form.result as VerificationResult)}
          </label>
          <textarea
            id={`${prefix}-result-notes`}
            rows={3}
            value={form.resultNotes}
            disabled={disabled}
            onChange={(event) => onChange({ resultNotes: event.target.value })}
            placeholder="Record what you did and what you observed."
            aria-invalid={Boolean(errors.resultNotes)}
            aria-describedby={`${prefix}-result-notes-help${errors.resultNotes ? ` ${prefix}-result-notes-error` : ""}`}
          />
          <div className="field-meta" id={`${prefix}-result-notes-help`}>
            <span>{resultNotesGuidance(form.result)}</span>
            <span className={notesCount > VERIFICATION_TEXT_MAX ? "field-error" : ""}>
              {notesCount.toLocaleString()} / {VERIFICATION_TEXT_MAX.toLocaleString()}
            </span>
          </div>
          {errors.resultNotes && (
            <p className="field-error" id={`${prefix}-result-notes-error`}>
              {errors.resultNotes}
            </p>
          )}
        </div>
      )}
    </article>
  );
}
