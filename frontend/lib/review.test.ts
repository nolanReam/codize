import { describe, expect, it } from "vitest";

import { writeDraft } from "./drafts";
import {
  REVIEW_DECISIONS,
  REVIEW_TARGET_CATEGORY_ORDER,
  REVIEW_TEXT_MAX,
  canReplaceReviewFromMap,
  deriveReviewSavePayload,
  groupReviewTargets,
  isLinkedReviewArtifact,
  isLinkedReviewDirty,
  isReviewTargetCategory,
  linkedReviewAllowsVerification,
  linkedReviewComplete,
  linkedReviewDraftSurface,
  linkedReviewDraftValue,
  linkedReviewProgress,
  linkedReviewServerRevision,
  restoreLinkedReviewDraft,
  reviewArtifactMode,
  reviewCategoryLabel,
  reviewCharacterCount,
  reviewDecisionLabel,
  reviewFormBlocker,
  reviewInitializationBody,
  reviewPrerequisiteState,
  reviewStepStatus,
  showFullReviewInitializationState,
  sourceResolutionLabel,
  targetFormFromReview,
  validateReviewTarget,
  type LinkedReviewFormState,
} from "./review";
import type {
  LinkedReviewBoardArtifact,
  LinkedReviewTarget,
  ReviewDecision,
  StoredChangeMap,
} from "./types";

function target(overrides: Partial<LinkedReviewTarget> = {}): LinkedReviewTarget {
  return {
    review_target_id: "rv-0123456789ab",
    change_map_item_id: "cm-0123456789ab",
    change_map_category: "implementation_decision",
    change_map_origin: "ai_inferred",
    change_map_student_decision: "confirmed",
    change_text: "The route now filters reads by owner.",
    source_resolution: "confirmed",
    review_decision: "pending",
    student_rationale: null,
    student_revision: null,
    ...overrides,
  };
}

function linked(
  targets: LinkedReviewTarget[] = [target()],
  overrides: Partial<LinkedReviewBoardArtifact> = {}
): LinkedReviewBoardArtifact {
  return {
    files_changed: [],
    ai_generated: null,
    accepted: null,
    rejected: null,
    edited_manually: null,
    ai_assumptions: null,
    least_confident: null,
    out_of_scope_changes: null,
    saved_at: "2026-07-13T12:00:00Z",
    source_change_map_generated_at: "2026-07-13T10:00:00Z",
    source_change_map_confirmed_at: "2026-07-13T11:00:00Z",
    initialized_from_change_map: true,
    stale: false,
    review_targets: targets,
    ...overrides,
  };
}

function map(overrides: Partial<StoredChangeMap> = {}): StoredChangeMap {
  return {
    schema_version: "1.0",
    status: "confirmed",
    source_import_saved_at: "2026-07-13T09:00:00Z",
    generated_at: "2026-07-13T10:00:00Z",
    confirmed_at: "2026-07-13T11:00:00Z",
    source_redacted: false,
    source_truncated: false,
    stale: false,
    items: [],
    ...overrides,
  };
}

function stateFor(review: LinkedReviewBoardArtifact): LinkedReviewFormState {
  return targetFormFromReview(review);
}

describe("exact linked Review labels and mode detection", () => {
  it("maps every backend decision to beginner-facing language", () => {
    expect(REVIEW_DECISIONS).toEqual([
      "pending", "keep", "revise", "remove", "needs_verification", "uncertain",
    ]);
    expect(REVIEW_DECISIONS.map(reviewDecisionLabel)).toEqual([
      "Not reviewed yet", "Keep", "Revise", "Remove", "Needs testing", "I’m not sure",
    ]);
    expect(REVIEW_DECISIONS.map(reviewDecisionLabel).join(" ")).not.toMatch(
      /approve|correct|verified|safe|AI recommendation/i
    );
  });

  it("uses the exact category policy and human Change Map labels", () => {
    expect(REVIEW_TARGET_CATEGORY_ORDER).toEqual([
      "behavior_change",
      "implementation_decision",
      "out_of_scope_change",
      "security_sensitive_area",
      "unresolved_risk",
      "unverified_behavior",
    ]);
    expect(reviewCategoryLabel("security_sensitive_area")).toBe("Areas to review carefully");
    expect(isReviewTargetCategory("changed_file")).toBe(false);
    expect(isReviewTargetCategory("question_to_understand")).toBe(false);
  });

  it("distinguishes no artifact, linked Review, legacy Review, and malformed linked data", () => {
    expect(reviewArtifactMode(null)).toBe("none");
    expect(reviewArtifactMode(linked())).toBe("linked");
    expect(reviewArtifactMode({ files_changed: [], accepted: "Kept it." })).toBe("legacy");
    expect(reviewArtifactMode({ initialized_from_change_map: true, review_targets: "bad" })).toBe(
      "legacy"
    );
    expect(isLinkedReviewArtifact(linked())).toBe(true);
  });
});

describe("initialization and prerequisites", () => {
  it("omits the normal body and emits replacement intent only deliberately", () => {
    expect(reviewInitializationBody(false)).toBeUndefined();
    expect(reviewInitializationBody(true)).toEqual({ replace_existing: true });
  });

  it("uses the full preparation screen only when there is no Review to preserve", () => {
    expect(showFullReviewInitializationState(true, false)).toBe(true);
    expect(showFullReviewInitializationState(true, true)).toBe(false);
    expect(showFullReviewInitializationState(false, false)).toBe(false);
  });

  it("derives calm missing, draft, stale, and confirmed states", () => {
    expect(reviewPrerequisiteState(null)).toBe("missing_change_map");
    expect(reviewPrerequisiteState(map({ status: "draft", confirmed_at: null }))).toBe(
      "draft_change_map"
    );
    expect(reviewPrerequisiteState(map({ stale: true }))).toBe("stale_change_map");
    expect(reviewPrerequisiteState(map())).toBe("ready");
    expect(canReplaceReviewFromMap(map())).toBe(true);
    expect(canReplaceReviewFromMap(map({ stale: true }))).toBe(false);
  });
});

describe("target grouping and source resolution", () => {
  it("keeps fixed category order, source order, unresolved targets, and omits empty groups", () => {
    const targets = [
      target({ review_target_id: "rv-000000000001", change_map_item_id: "cm-1", change_map_category: "unresolved_risk", source_resolution: "unresolved", change_map_student_decision: "uncertain" }),
      target({ review_target_id: "rv-000000000002", change_map_item_id: "cm-2", change_map_category: "behavior_change" }),
      target({ review_target_id: "rv-000000000003", change_map_item_id: "cm-3", change_map_category: "behavior_change" }),
    ];
    const groups = groupReviewTargets(targets);
    expect(groups.map((group) => group.category)).toEqual(["behavior_change", "unresolved_risk"]);
    expect(groups[0].targets.map((item) => item.change_map_item_id)).toEqual(["cm-2", "cm-3"]);
    expect(groups[1].targets[0].source_resolution).toBe("unresolved");
  });

  it("describes confirmed, edited, student-added, uncertain, and inspection sources honestly", () => {
    expect(sourceResolutionLabel(target())).toBe("Confirmed in Change Map");
    expect(sourceResolutionLabel(target({ change_map_student_decision: "edited" }))).toBe(
      "Corrected by you in Change Map"
    );
    expect(sourceResolutionLabel(target({ change_map_origin: "student_added" }))).toBe("Added by you");
    expect(sourceResolutionLabel(target({ change_map_student_decision: "uncertain", source_resolution: "unresolved" }))).toBe(
      "Marked uncertain in Change Map"
    );
    expect(sourceResolutionLabel(target({ change_map_student_decision: "needs_inspection", source_resolution: "unresolved" }))).toBe(
      "Still needs inspection"
    );
  });
});

describe("progress, validation, and completion", () => {
  it.each<ReviewDecision>(["keep", "revise", "remove", "needs_verification", "uncertain"])(
    "%s counts as reviewed",
    (decision) => {
      const item = target({
        review_decision: decision,
        ...(decision === "revise" ? { student_revision: "Use a narrower query." } : {}),
      });
      const review = linked([item]);
      const state = stateFor(review);
      expect(linkedReviewProgress(review, state)).toEqual({ reviewed: 1, total: 1, pending: 0 });
      expect(linkedReviewComplete(review, state)).toBe(true);
    }
  );

  it("keeps pending incomplete, supports mixed progress, and treats zero targets separately", () => {
    const review = linked([
      target({ review_target_id: "rv-000000000001", change_map_item_id: "cm-1" }),
      target({ review_target_id: "rv-000000000002", change_map_item_id: "cm-2", review_decision: "uncertain" }),
    ]);
    const state = stateFor(review);
    expect(linkedReviewProgress(review, state)).toEqual({ reviewed: 1, total: 2, pending: 1 });
    expect(linkedReviewComplete(review, state)).toBe(false);
    const empty = linked([]);
    expect(linkedReviewComplete(empty, {})).toBe(false);
    expect(linkedReviewAllowsVerification(empty, {})).toBe(true);
  });

  it("matches the backend revise rule and Unicode code-point limit without clipping", () => {
    expect(validateReviewTarget({ reviewDecision: "keep", studentRationale: "", studentRevision: "" })).toEqual({});
    expect(validateReviewTarget({ reviewDecision: "revise", studentRationale: "   ", studentRevision: "" }).revision).toMatch(/describe/i);
    expect(validateReviewTarget({ reviewDecision: "revise", studentRationale: "The query is broad.", studentRevision: "" })).toEqual({});
    const exact = "😀".repeat(REVIEW_TEXT_MAX);
    const over = `${exact}😀`;
    expect(reviewCharacterCount(exact)).toBe(REVIEW_TEXT_MAX);
    expect(validateReviewTarget({ reviewDecision: "revise", studentRationale: "", studentRevision: exact })).toEqual({});
    expect(validateReviewTarget({ reviewDecision: "revise", studentRationale: "", studentRevision: over }).revision).toMatch(/2,000/);
    expect(over).toHaveLength((REVIEW_TEXT_MAX + 1) * 2);
  });
});

describe("student-only payload and canonical dirty state", () => {
  it("sends only the target reference and three student-owned fields", () => {
    const review = linked();
    const state = stateFor(review);
    state[review.review_targets[0].review_target_id] = {
      reviewDecision: "needs_verification",
      studentRationale: "Run the wrong-user behavior check.",
      studentRevision: "hidden text",
    };
    const payload = deriveReviewSavePayload(review, state);
    expect(payload.target_updates).toHaveLength(1);
    expect(Object.keys(payload.target_updates![0]).sort()).toEqual([
      "review_decision", "review_target_id", "student_rationale", "student_revision",
    ]);
    expect(payload.target_updates![0]).toMatchObject({
      review_decision: "needs_verification",
      student_rationale: "Run the wrong-user behavior check.",
      student_revision: null,
    });
    const serialized = JSON.stringify(payload);
    for (const forbidden of [
      "change_map_item_id", "change_map_category", "change_map_origin",
      "change_map_student_decision", "change_text", "source_resolution",
      "source_change_map", "stale", "generated_at",
    ]) expect(serialized).not.toContain(forbidden);
  });

  it("ignores hidden revision/rationale for dirty state and emits no contradictory fields", () => {
    const kept = target({ review_decision: "keep" });
    const review = linked([kept]);
    const state = stateFor(review);
    state[kept.review_target_id].studentRevision = "local hidden revision";
    state[kept.review_target_id].studentRationale = "local hidden rationale";
    expect(isLinkedReviewDirty(review, state)).toBe(false);
    expect(deriveReviewSavePayload(review, state)).toEqual({ target_updates: [] });
  });

  it.each<ReviewDecision>(["keep", "remove", "needs_verification", "uncertain"])(
    "Revise → %s drops the old revision from the safe payload",
    (decision) => {
      const revised = target({ review_decision: "revise", student_revision: "Old proposal" });
      const review = linked([revised]);
      const state = stateFor(review);
      state[revised.review_target_id].reviewDecision = decision;
      const update = deriveReviewSavePayload(review, state).target_updates![0];
      expect(update.review_decision).toBe(decision);
      expect(update.student_revision).toBeNull();
    }
  );

  it("is clean when unchanged or reverted and blocks only active invalid text", () => {
    const review = linked();
    const state = stateFor(review);
    expect(isLinkedReviewDirty(review, state)).toBe(false);
    state[review.review_targets[0].review_target_id].reviewDecision = "remove";
    expect(isLinkedReviewDirty(review, state)).toBe(true);
    state[review.review_targets[0].review_target_id].reviewDecision = "pending";
    expect(isLinkedReviewDirty(review, state)).toBe(false);
    expect(reviewFormBlocker(review, state)).toBeNull();
  });
});

describe("scoped linked Review drafts and stale invalidation", () => {
  it("keeps the server revision stable across equivalent response objects", () => {
    const review = linked();
    const cloned = structuredClone(review);

    expect(linkedReviewServerRevision(cloned)).toBe(linkedReviewServerRevision(review));

    cloned.review_targets[0].student_rationale = "A saved server-side note";
    expect(linkedReviewServerRevision(cloned)).not.toBe(linkedReviewServerRevision(review));
  });

  it("scopes by active project, phase, binding, and ordered target set", () => {
    const review = linked();
    const base = linkedReviewDraftSurface(1, review);
    expect(base).toMatch(/^linked_review:active-project:1:[0-9a-f]{8}$/);
    expect(linkedReviewDraftSurface(2, review)).not.toBe(base);
    expect(linkedReviewDraftSurface(1, linked(review.review_targets, {
      source_change_map_confirmed_at: "2026-07-13T11:30:00Z",
    }))).not.toBe(base);
    expect(linkedReviewDraftSurface(1, linked([
      ...review.review_targets,
      target({ review_target_id: "rv-000000000002", change_map_item_id: "cm-2" }),
    ]))).not.toBe(base);
  });

  it("restores compatible student-only state and rejects stale or incompatible drafts", () => {
    const review = linked();
    const state = stateFor(review);
    state[review.review_targets[0].review_target_id].reviewDecision = "uncertain";
    const draft = linkedReviewDraftValue(review, state);
    expect(restoreLinkedReviewDraft(review, draft)).toEqual(state);
    expect(restoreLinkedReviewDraft(linked(review.review_targets, { stale: true }), draft)).toBeNull();
    expect(restoreLinkedReviewDraft(review, { ...draft, fingerprint: "wrong" })).toBeNull();
    expect(JSON.stringify(draft)).not.toContain(review.review_targets[0].change_text);
  });

  it("reuses the existing secret guard and treats storage failure as non-fatal", () => {
    const review = linked();
    const state = stateFor(review);
    state[review.review_targets[0].review_target_id].studentRationale = "sb_secret_fake";
    const storage = {
      getItem: () => null,
      setItem: () => { throw new Error("blocked"); },
      removeItem: () => undefined,
    };
    expect(writeDraft(storage, "review", linkedReviewDraftValue(review, state))).toBe(false);
  });
});

describe("Build Loop Review status", () => {
  it("distinguishes not started, ready, in progress, complete, stale, and legacy", () => {
    expect(reviewStepStatus(null, null)).toEqual({ label: "not started", tone: "idle" });
    expect(reviewStepStatus(null, map())).toEqual({ label: "ready to start", tone: "draft" });
    expect(reviewStepStatus(linked(), map())).toEqual({ label: "in progress", tone: "draft" });
    expect(reviewStepStatus(linked([target({ review_decision: "uncertain" })]), map())).toEqual({
      label: "complete", tone: "done",
    });
    expect(reviewStepStatus(linked(undefined, { stale: true }), map())).toEqual({
      label: "stale", tone: "stale",
    });
    expect(reviewStepStatus({ files_changed: [] }, map())).toEqual({ label: "saved", tone: "done" });
  });
});
