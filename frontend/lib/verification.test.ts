import { describe, expect, it } from "vitest";

import {
  VERIFICATION_CATEGORY_ORDER,
  VERIFICATION_RESULT_LABELS,
  VERIFICATION_RESULTS,
  VERIFICATION_TEXT_MAX,
  canReplaceVerificationFromReview,
  canonicalVerificationTargetUpdate,
  changeVerificationResult,
  deriveVerificationSavePayload,
  effectiveCheckWording,
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
  showFullVerificationInitializationState,
  targetFormFromVerification,
  validateVerificationTarget,
  verificationArtifactMode,
  verificationCategoryLabel,
  verificationCharacterCount,
  verificationFormBlocker,
  verificationInitializationBody,
  verificationPrerequisiteState,
  verificationResultDescription,
  verificationResultLabel,
  verificationStepStatus,
  type LinkedVerificationFormState,
} from "./verification";
import type {
  LinkedReviewBoardArtifact,
  LinkedVerificationArtifact,
  LinkedVerificationTarget,
  ReviewDecision,
  VerificationResult,
  VerificationSourceCategory,
} from "./types";

function review(
  decision: ReviewDecision = "needs_verification",
  overrides: Partial<LinkedReviewBoardArtifact> = {}
): LinkedReviewBoardArtifact {
  return {
    files_changed: [],
    initialized_from_change_map: true,
    stale: false,
    source_change_map_generated_at: "2026-07-13T10:00:00Z",
    source_change_map_confirmed_at: "2026-07-13T11:00:00Z",
    saved_at: "2026-07-13T12:00:00Z",
    review_targets: [
      {
        review_target_id: "rv-0123456789ab",
        change_map_item_id: "cm-0123456789ab",
        change_map_category: "behavior_change",
        change_map_origin: "ai_inferred",
        change_map_student_decision: "confirmed",
        change_text: "Tasks are filtered by owner.",
        source_resolution: "confirmed",
        review_decision: decision,
        student_rationale: "Check the ownership boundary.",
        student_revision: null,
      },
    ],
    ...overrides,
  };
}

function target(
  id: string,
  category: VerificationSourceCategory = "behavior_change",
  overrides: Partial<LinkedVerificationTarget> = {}
): LinkedVerificationTarget {
  return {
    verification_target_id: id,
    review_target_id: `rv-${id.slice(3)}`,
    change_map_item_id: `cm-${id.slice(3)}`,
    category,
    source_text: "Tasks are filtered by owner.",
    source_rationale: "Check the ownership boundary.",
    suggested_check: "Sign in as two users and compare the visible tasks.",
    student_check: null,
    result: null,
    result_notes: null,
    ...overrides,
  };
}

function verification(
  overrides: Partial<LinkedVerificationArtifact> = {}
): LinkedVerificationArtifact {
  return {
    checks: [],
    explanation: null,
    saved_at: "2026-07-13T12:05:00Z",
    initialized_at: "2026-07-13T12:01:00Z",
    source_review_binding: {
      source_change_map_generated_at: "2026-07-13T10:00:00Z",
      source_change_map_confirmed_at: "2026-07-13T11:00:00Z",
      review_saved_at: "2026-07-13T12:00:00Z",
      review_target_fingerprint: "a".repeat(64),
    },
    initialized_from_review: true,
    stale: false,
    verification_targets: [target("vt-0123456789ab")],
    ...overrides,
  };
}

describe("linked/manual Verification modes and exact labels", () => {
  it("distinguishes missing, linked, and legacy artifacts", () => {
    expect(verificationArtifactMode(null)).toBe("none");
    expect(verificationArtifactMode(verification())).toBe("linked");
    expect(verificationArtifactMode({ checks: [], explanation: null })).toBe("legacy");
    expect(isLinkedVerificationArtifact(verification())).toBe(true);
  });

  it("fails safely when an optional linked field is malformed", () => {
    const malformed = verification({
      verification_targets: [
        { ...target("vt-0123456789ab"), source_rationale: 7 as unknown as string },
      ],
    });
    expect(isLinkedVerificationArtifact(malformed)).toBe(false);
    expect(verificationArtifactMode(malformed)).toBe("legacy");
  });

  it("keeps exact result values, labels, and honest meanings", () => {
    expect(VERIFICATION_RESULTS).toEqual([
      null,
      "pass",
      "fail",
      "skipped",
      "not_applicable",
    ]);
    expect(VERIFICATION_RESULT_LABELS).toEqual({
      pass: "Passed",
      fail: "Failed",
      skipped: "Skipped",
      not_applicable: "Not applicable",
    });
    expect(verificationResultLabel(null)).toBe("Not recorded yet");
    expect(verificationResultDescription("pass")).toContain("expected behavior");
    expect(verificationResultDescription("pass")).not.toMatch(/entire project|verified/i);
    expect(verificationResultDescription("skipped")).toContain("does not count as passed");
    expect(verificationResultDescription("not_applicable")).toContain("does not count as passed");
  });
});

describe("category grouping", () => {
  it("uses the exact backend category order and human labels", () => {
    expect(VERIFICATION_CATEGORY_ORDER).toEqual([
      "behavior_change",
      "implementation_decision",
      "out_of_scope_change",
      "security_sensitive_area",
      "unresolved_risk",
      "unverified_behavior",
    ]);
    expect(verificationCategoryLabel("security_sensitive_area")).toBe(
      "Areas to review carefully"
    );
  });

  it("omits empty groups and preserves backend order inside a group", () => {
    const targets = [
      target("vt-bbbbbbbbbbbb", "unresolved_risk"),
      target("vt-111111111111", "behavior_change"),
      target("vt-222222222222", "behavior_change"),
    ];
    const groups = groupVerificationTargets(targets);
    expect(groups.map((group) => group.category)).toEqual([
      "behavior_change",
      "unresolved_risk",
    ]);
    expect(groups[0].targets.map((item) => item.verification_target_id)).toEqual([
      "vt-111111111111",
      "vt-222222222222",
    ]);
  });
});

describe("student check, validation, and result transitions", () => {
  it("starts from saved student fields and falls back to the server suggestion", () => {
    const artifact = verification();
    const form = targetFormFromVerification(artifact);
    const first = form["vt-0123456789ab"];
    expect(first).toEqual({ studentCheck: "", result: null, resultNotes: "" });
    expect(effectiveCheckWording(artifact.verification_targets[0], first)).toBe(
      artifact.verification_targets[0].suggested_check
    );
    first.studentCheck = "Use the browser flow.";
    expect(effectiveCheckWording(artifact.verification_targets[0], first)).toBe(
      "Use the browser flow."
    );
  });

  it("uses Python-compatible Unicode code-point counts and never truncates", () => {
    expect(verificationCharacterCount("a😀b")).toBe(3);
    const tooLong = "😀".repeat(VERIFICATION_TEXT_MAX + 1);
    expect(validateVerificationTarget({
      studentCheck: tooLong,
      result: null,
      resultNotes: "",
    }).studentCheck).toContain("2,000");
    expect(tooLong).toHaveLength((VERIFICATION_TEXT_MAX + 1) * 2);
  });

  it.each<[VerificationResult, VerificationResult | null]>([
    ["fail", "pass"],
    ["fail", "skipped"],
    ["fail", "not_applicable"],
    ["skipped", "pass"],
    ["not_applicable", "pass"],
  ])("clears result-specific notes when changing %s to %s", (from, to) => {
    expect(changeVerificationResult({
      studentCheck: "",
      result: from,
      resultNotes: "Notes for the old result",
    }, to)).toEqual({ studentCheck: "", result: to, resultNotes: "" });
  });

  it("ignores hidden notes when no result is active", () => {
    const artifact = verification();
    const source = artifact.verification_targets[0];
    const update = canonicalVerificationTargetUpdate(source, {
      studentCheck: "",
      result: null,
      resultNotes: "hidden local note",
    });
    expect(update.result_notes).toBeNull();
    expect(isLinkedVerificationDirty(artifact, {
      [source.verification_target_id]: {
        studentCheck: "",
        result: null,
        resultNotes: "hidden local note",
      },
    })).toBe(false);
  });
});

describe("student-only payload and canonical dirty state", () => {
  it("sends only changed student-owned fields and the server target identifier", () => {
    const artifact = verification();
    const state = targetFormFromVerification(artifact);
    state["vt-0123456789ab"] = {
      studentCheck: "  Run the owner-isolation flow.  ",
      result: "fail",
      resultNotes: "  User B saw User A's task.  ",
    };
    const payload = deriveVerificationSavePayload(artifact, state);
    expect(payload).toEqual({
      target_updates: [{
        verification_target_id: "vt-0123456789ab",
        student_check: "Run the owner-isolation flow.",
        result: "fail",
        result_notes: "User B saw User A's task.",
      }],
    });
    const serialized = JSON.stringify(payload);
    for (const forbidden of [
      "review_target_id",
      "change_map_item_id",
      "source_text",
      "source_rationale",
      "category",
      "suggested_check",
      "source_review_binding",
      "initialized_at",
      "stale",
      "review_target_fingerprint",
    ]) {
      expect(serialized).not.toContain(forbidden);
    }
  });

  it("is clean unchanged, dirty when changed, and clean after reverting", () => {
    const artifact = verification();
    const state = targetFormFromVerification(artifact);
    expect(isLinkedVerificationDirty(artifact, state)).toBe(false);
    state["vt-0123456789ab"].result = "pass";
    expect(isLinkedVerificationDirty(artifact, state)).toBe(true);
    state["vt-0123456789ab"].result = null;
    expect(isLinkedVerificationDirty(artifact, state)).toBe(false);
    expect(deriveVerificationSavePayload(artifact, state)).toEqual({ target_updates: [] });
  });

  it("blocks only active over-limit fields", () => {
    const artifact = verification();
    const state = targetFormFromVerification(artifact);
    state["vt-0123456789ab"].resultNotes = "x".repeat(VERIFICATION_TEXT_MAX + 1);
    expect(verificationFormBlocker(artifact, state)).toBeNull();
    state["vt-0123456789ab"].result = "fail";
    expect(verificationFormBlocker(artifact, state)).toContain("notes");
  });
});

describe("recorded progress and honest result summary", () => {
  function mixedState(): {
    artifact: LinkedVerificationArtifact;
    state: LinkedVerificationFormState;
  } {
    const artifact = verification({
      verification_targets: [
        target("vt-111111111111"),
        target("vt-222222222222"),
        target("vt-333333333333"),
        target("vt-444444444444"),
        target("vt-555555555555"),
      ],
    });
    const state = targetFormFromVerification(artifact);
    state["vt-111111111111"].result = "pass";
    state["vt-222222222222"].result = "fail";
    state["vt-333333333333"].result = "skipped";
    state["vt-444444444444"].result = "not_applicable";
    return { artifact, state };
  }

  it("counts every explicit outcome as recorded but never as passed", () => {
    const { artifact, state } = mixedState();
    expect(linkedVerificationProgress(artifact, state)).toEqual({
      recorded: 4,
      total: 5,
      unperformed: 1,
    });
    expect(linkedVerificationResultSummary(artifact, state)).toEqual({
      recorded: 4,
      passed: 1,
      failed: 1,
      skipped: 1,
      notApplicable: 1,
      unperformed: 1,
    });
    expect(linkedVerificationRecorded(artifact, state)).toBe(false);
  });

  it("allows recorded completion with fail, skipped, and not-applicable results", () => {
    const { artifact, state } = mixedState();
    state["vt-555555555555"].result = "fail";
    expect(linkedVerificationRecorded(artifact, state)).toBe(true);
    expect(linkedVerificationResultSummary(artifact, state).passed).toBe(1);
  });

  it("keeps a zero-target artifact neutral rather than complete", () => {
    const artifact = verification({ verification_targets: [] });
    expect(isZeroTargetVerification(artifact)).toBe(true);
    expect(linkedVerificationRecorded(artifact, {})).toBe(false);
    expect(linkedVerificationProgress(artifact, {})).toEqual({
      recorded: 0,
      total: 0,
      unperformed: 0,
    });
  });
});

describe("Review prerequisites, initialization, and replacement readiness", () => {
  it("distinguishes no Review, incomplete, stale, and ready", () => {
    expect(verificationPrerequisiteState(null)).toBe("no_review");
    expect(verificationPrerequisiteState({ files_changed: [] })).toBe("no_review");
    expect(verificationPrerequisiteState(review("pending"))).toBe("incomplete_review");
    expect(verificationPrerequisiteState(review("needs_verification", { stale: true }))).toBe(
      "stale_review"
    );
    expect(verificationPrerequisiteState(review())).toBe("ready");
    expect(canReplaceVerificationFromReview(review())).toBe(true);
  });

  it("treats a current saved zero-target Review as ready", () => {
    expect(verificationPrerequisiteState(review("keep", { review_targets: [] }))).toBe("ready");
  });

  it("sends no body normally and the exact replacement flag deliberately", () => {
    expect(verificationInitializationBody(false)).toBeUndefined();
    expect(verificationInitializationBody(true)).toEqual({ replace_existing: true });
    expect(showFullVerificationInitializationState(true, false)).toBe(true);
    expect(showFullVerificationInitializationState(true, true)).toBe(false);
  });
});

describe("scoped linked Verification drafts and stale invalidation", () => {
  it("uses user-added project/phase/surface scoping without raw source text", () => {
    const artifact = verification();
    const surface = linkedVerificationDraftSurface(3, artifact);
    expect(surface).toMatch(/^linked_verification:active-project:3:[0-9a-f]{8}$/);
    expect(surface).not.toContain(artifact.verification_targets[0].source_text);
    expect(linkedVerificationDraftSurface(4, artifact)).not.toBe(surface);
  });

  it("stores only a safe fingerprint and student-owned target form fields", () => {
    const artifact = verification();
    const value = linkedVerificationDraftValue(artifact, targetFormFromVerification(artifact));
    const serialized = JSON.stringify(value);
    expect(serialized).toContain("vt-0123456789ab");
    expect(serialized).not.toContain("Tasks are filtered");
    expect(serialized).not.toContain("Sign in as two users");
    expect(serialized).not.toContain("review_saved_at");
  });

  it("restores only an exact compatible draft", () => {
    const artifact = verification();
    const state = targetFormFromVerification(artifact);
    state["vt-0123456789ab"].result = "fail";
    const value = linkedVerificationDraftValue(artifact, state);
    expect(restoreLinkedVerificationDraft(artifact, value)).toEqual(state);
    expect(restoreLinkedVerificationDraft(
      verification({ stale: true }),
      value
    )).toBeNull();
    expect(restoreLinkedVerificationDraft(
      verification({ initialized_at: "a different linked version" }),
      value
    )).toBeNull();
    expect(restoreLinkedVerificationDraft(artifact, {
      ...value,
      targets: { "vt-other": state["vt-0123456789ab"] },
    })).toBeNull();
  });

  it("changes server revision after save without including source text", () => {
    const before = verification();
    const after = verification({ saved_at: "2026-07-13T12:30:00Z" });
    expect(linkedVerificationServerRevision(before)).not.toBe(
      linkedVerificationServerRevision(after)
    );
    expect(linkedVerificationServerRevision(before)).not.toContain("Tasks are filtered");
  });
});

describe("Build Loop Verification status", () => {
  it("distinguishes unavailable, ready, manual, in-progress, recorded, stale, and zero", () => {
    expect(verificationStepStatus(null, null)).toEqual({
      label: "not available yet",
      tone: "idle",
    });
    expect(verificationStepStatus(null, review())).toEqual({
      label: "ready to start",
      tone: "draft",
    });
    expect(verificationStepStatus({ checks: [] }, review())).toEqual({
      label: "saved",
      tone: "done",
    });
    expect(verificationStepStatus(verification(), review()).label).toBe("in progress");
    expect(verificationStepStatus(verification({ stale: true }), review())).toEqual({
      label: "stale",
      tone: "stale",
    });
    expect(verificationStepStatus(verification({ verification_targets: [] }), review())).toEqual({
      label: "no checks requested",
      tone: "draft",
    });
    const recorded = verification({
      verification_targets: [target("vt-0123456789ab", "behavior_change", { result: "fail" })],
    });
    expect(verificationStepStatus(recorded, review())).toEqual({
      label: "results recorded",
      tone: "done",
    });
  });
});
