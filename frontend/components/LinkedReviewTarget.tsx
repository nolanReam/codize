"use client";

import React from "react";

import {
  REVIEW_DECISIONS,
  REVIEW_DECISION_MEANINGS,
  REVIEW_TEXT_MAX,
  reviewCharacterCount,
  reviewDecisionLabel,
  sourceResolutionGuidance,
  sourceResolutionLabel,
  validateReviewTarget,
  type LinkedReviewTargetForm,
} from "../lib/review";
import type { LinkedReviewTarget, ReviewDecision } from "../lib/types";

export function ReviewSourceSnapshot({
  target,
}: {
  target: LinkedReviewTarget;
}) {
  const guidance = sourceResolutionGuidance(target);
  const tone = target.source_resolution === "unresolved"
    ? "warn"
    : target.change_map_origin === "student_added" ||
        target.change_map_student_decision === "edited"
      ? "accent"
      : "";
  return (
    <div className="review-source" aria-label="From your Change Map">
      <div className="review-source-heading">
        <span>From your Change Map</span>
        <span className={`pill ${tone}`}>{sourceResolutionLabel(target)}</span>
      </div>
      <p className="review-source-text">{target.change_text}</p>
      {guidance && <p className="review-source-guidance">{guidance}</p>}
    </div>
  );
}

function rationaleLabel(decision: ReviewDecision): string {
  if (decision === "remove") return "Why should this be removed? (optional)";
  if (decision === "needs_verification") return "What still needs to be checked? (optional)";
  if (decision === "uncertain") return "What are you unsure about? (optional)";
  return "Why should this be revised? (optional)";
}

export default function LinkedReviewTargetRow({
  target,
  index,
  form,
  disabled,
  onChange,
}: {
  target: LinkedReviewTarget;
  index: number;
  form: LinkedReviewTargetForm;
  disabled: boolean;
  onChange: (patch: Partial<LinkedReviewTargetForm>) => void;
}) {
  const errors = validateReviewTarget(form);
  const rationaleActive = form.reviewDecision === "revise" ||
    form.reviewDecision === "remove" ||
    form.reviewDecision === "needs_verification" ||
    form.reviewDecision === "uncertain";
  const prefix = `review-item-${index + 1}`;
  const revisionCount = reviewCharacterCount(form.studentRevision);
  const rationaleCount = reviewCharacterCount(form.studentRationale);

  return (
    <article className="linked-review-target">
      <ReviewSourceSnapshot target={target} />

      <fieldset className="review-decision-picker" disabled={disabled}>
        <legend>Your decision</legend>
        <div className="review-decision-grid">
          {REVIEW_DECISIONS.map((decision) => {
            const inputId = `${prefix}-${decision}`;
            return (
              <label
                className={`review-decision${form.reviewDecision === decision ? " active" : ""}`}
                key={decision}
                htmlFor={inputId}
              >
                <input
                  id={inputId}
                  type="radio"
                  name={`${prefix}-decision`}
                  value={decision}
                  checked={form.reviewDecision === decision}
                  onChange={() => onChange({ reviewDecision: decision })}
                />
                <span>
                  <strong>{reviewDecisionLabel(decision)}</strong>
                  <small>{REVIEW_DECISION_MEANINGS[decision]}</small>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {form.reviewDecision === "revise" && (
        <div className="field review-student-field">
          <label htmlFor={`${prefix}-revision`}>What should change?</label>
          <textarea
            id={`${prefix}-revision`}
            rows={3}
            value={form.studentRevision}
            onChange={(event) => onChange({ studentRevision: event.target.value })}
            placeholder="Describe the change you want to make next."
            aria-invalid={Boolean(errors.revision)}
            aria-describedby={`${prefix}-revision-help${errors.revision ? ` ${prefix}-revision-error` : ""}`}
          />
          <div className="field-meta" id={`${prefix}-revision-help`}>
            <span>Describe the revision, or explain the reason below.</span>
            <span className={revisionCount > REVIEW_TEXT_MAX ? "field-error" : ""}>
              {revisionCount.toLocaleString()} / {REVIEW_TEXT_MAX.toLocaleString()}
            </span>
          </div>
          {errors.revision && (
            <p className="field-error" id={`${prefix}-revision-error`}>{errors.revision}</p>
          )}
        </div>
      )}

      {rationaleActive && (
        <div className="field review-student-field">
          <label htmlFor={`${prefix}-rationale`}>{rationaleLabel(form.reviewDecision)}</label>
          <textarea
            id={`${prefix}-rationale`}
            rows={2}
            value={form.studentRationale}
            onChange={(event) => onChange({ studentRationale: event.target.value })}
            placeholder="Add the reasoning you want to remember."
            aria-invalid={Boolean(errors.rationale)}
            aria-describedby={`${prefix}-rationale-count${errors.rationale ? ` ${prefix}-rationale-error` : ""}`}
          />
          <div className="field-meta" id={`${prefix}-rationale-count`}>
            <span />
            <span className={rationaleCount > REVIEW_TEXT_MAX ? "field-error" : ""}>
              {rationaleCount.toLocaleString()} / {REVIEW_TEXT_MAX.toLocaleString()}
            </span>
          </div>
          {errors.rationale && (
            <p className="field-error" id={`${prefix}-rationale-error`}>{errors.rationale}</p>
          )}
        </div>
      )}
    </article>
  );
}
