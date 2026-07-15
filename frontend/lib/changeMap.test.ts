import { describe, expect, it } from "vitest";

import {
  aiUncertaintyLabel,
  categoryExplanation,
  categoryLabel,
  CHANGE_MAP_AI_UNCERTAINTY_LABELS,
  CHANGE_MAP_CATEGORY_LABELS,
  CHANGE_MAP_CATEGORY_ORDER,
  CHANGE_MAP_DECISION_LABELS,
  CHANGE_MAP_GENERATION_FAILURE,
  CHANGE_MAP_HONESTY_LINE,
  CHANGE_MAP_PAGE_INTRO,
  CHANGE_MAP_PAGE_TITLE,
  CHANGE_MAP_SOURCE_FIELD_LABELS,
  changeMapCharacterCount,
  changeMapDraftSurface,
  changeMapStepStatus,
  confirmationReadiness,
  decisionLabel,
  derivePhaseNextStep,
  deriveChangeMapPageModel,
  deriveReviewProgress,
  deriveSavePayload,
  effectiveDisplayText,
  generationRequestBody,
  groupItemsByCategory,
  hasOnlyQuestionItems,
  humanSafeStatusCopy,
  isMapStale,
  isReviewDirty,
  pendingItemIds,
  restoreReviewDraft,
  reviewBlocker,
  reviewStateFromMap,
  sourceFieldLabel,
} from "./changeMap";
import type {
  ChangeMapCategory,
  ChangeMapItem,
  ChangeMapStudentDecision,
  LinkedReviewBoardArtifact,
  LinkedEvidenceArtifact,
  LinkedVerificationArtifact,
  StoredChangeMap,
  WorkflowSections,
} from "./types";

function aiItem(
  item_id: string,
  category: ChangeMapCategory,
  student_decision: ChangeMapStudentDecision = "pending_review"
): ChangeMapItem {
  return {
    item_id,
    origin: "ai_inferred",
    category,
    draft_text: `${item_id} appears to have changed.`,
    ai_uncertainty: "supported",
    uncertainty_reason: null,
    source_references: [
      {
        source_field: "content",
        source_kind: "git_diff",
        file_path: "app/tasks.py",
        supporting_excerpt: "+ changed = True",
      },
    ],
    student_decision,
    student_text: student_decision === "edited" ? `${item_id} corrected by me.` : null,
    student_note: null,
  };
}

function studentItem(
  item_id: string,
  category: ChangeMapCategory = "implementation_decision"
): ChangeMapItem {
  return {
    item_id,
    origin: "student_added",
    category,
    draft_text: null,
    ai_uncertainty: null,
    uncertainty_reason: null,
    source_references: [],
    student_decision: "uncertain",
    student_text: "I added this missing decision.",
    student_note: "I still need to inspect it.",
  };
}

function map(overrides: Partial<StoredChangeMap> = {}): StoredChangeMap {
  return {
    schema_version: "1.0",
    status: "draft",
    source_import_saved_at: "2026-07-13T10:00:00Z",
    generated_at: "2026-07-13T10:01:00Z",
    confirmed_at: null,
    source_redacted: false,
    source_truncated: false,
    stale: false,
    items: [
      aiItem("cm-file", "changed_file"),
      aiItem("cm-behavior", "behavior_change"),
    ],
    ...overrides,
  };
}

function sections(overrides: Partial<WorkflowSections> = {}): WorkflowSections {
  return {
    prompt_builder: { inputs: {}, generated_prompt: "Build the route." },
    implementation_import: {
      source_kind: "git_diff",
      content: "+ changed = True",
      changed_files: ["app/tasks.py"],
    },
    review_board: null,
    evidence: null,
    verification: null,
    ...overrides,
  };
}

function linkedReview(
  decision: "pending" | "keep" | "uncertain" = "pending",
  stale = false
): LinkedReviewBoardArtifact {
  return {
    files_changed: [],
    source_change_map_generated_at: "2026-07-13T10:01:00Z",
    source_change_map_confirmed_at: "2026-07-13T11:00:00Z",
    initialized_from_change_map: true,
    stale,
    review_targets: [{
      review_target_id: "rv-0123456789ab",
      change_map_item_id: "cm-behavior",
      change_map_category: "behavior_change",
      change_map_origin: "ai_inferred",
      change_map_student_decision: "confirmed",
      change_text: "The route behavior changed.",
      source_resolution: "confirmed",
      review_decision: decision,
      student_rationale: null,
      student_revision: null,
    }],
  };
}

function linkedVerification(
  result: "pass" | "fail" | "skipped" | "not_applicable" | null = null,
  stale = false,
  zeroTargets = false
): LinkedVerificationArtifact {
  return {
    checks: [],
    initialized_at: "2026-07-13T12:01:00Z",
    source_review_binding: {
      source_change_map_generated_at: "2026-07-13T10:01:00Z",
      source_change_map_confirmed_at: "2026-07-13T11:00:00Z",
      review_saved_at: "2026-07-13T12:00:00Z",
      review_target_fingerprint: "a".repeat(64),
    },
    initialized_from_review: true,
    stale,
    verification_targets: zeroTargets ? [] : [{
      verification_target_id: "vt-0123456789ab",
      review_target_id: "rv-0123456789ab",
      change_map_item_id: "cm-behavior",
      category: "behavior_change",
      source_text: "The route behavior changed.",
      source_rationale: null,
      suggested_check: "Perform the route flow.",
      student_check: null,
      result,
      result_notes: null,
    }],
  };
}

function linkedEvidence(
  complete = false,
  stale = false
): LinkedEvidenceArtifact {
  return {
    entries: [],
    summary: null,
    saved_at: "2026-07-14T12:00:00Z",
    initialized_from_verification: true,
    stale,
    evidence_record_complete: complete,
    evidence_targets: [{
      evidence_target_id: "ev-0123456789ab",
      source_verification_target_id: "vt-0123456789ab",
      category: "behavior_change",
      check_snapshot: "Perform the route flow.",
      verification_result_snapshot: "pass",
      verification_result_notes_snapshot: "The route worked.",
      evidence_status: complete ? "evidence_recorded" : "not_addressed",
      entries: complete ? [{ kind: "test_output", content: "1 passed" }] : [],
      explanation: complete ? "The route test passed." : null,
      unavailable_reason: null,
    }],
  };
}

describe("human-facing mappings", () => {
  it("keeps the exact eight categories in fixed Build Loop review order", () => {
    expect(CHANGE_MAP_CATEGORY_ORDER).toEqual([
      "changed_file",
      "behavior_change",
      "implementation_decision",
      "out_of_scope_change",
      "security_sensitive_area",
      "unresolved_risk",
      "unverified_behavior",
      "question_to_understand",
    ]);
    expect(Object.keys(CHANGE_MAP_CATEGORY_LABELS)).toHaveLength(8);
    for (const category of CHANGE_MAP_CATEGORY_ORDER) {
      expect(categoryLabel(category)).not.toContain("_");
      expect(categoryExplanation(category).length).toBeGreaterThan(25);
    }
  });

  it("uses the required non-accusatory category labels", () => {
    expect(categoryLabel("security_sensitive_area")).toBe("Areas to review carefully");
    expect(categoryLabel("unresolved_risk")).toBe("Unresolved risks");
    expect(categoryLabel("unverified_behavior")).toBe("Behavior still needing testing");
    expect(categoryLabel("security_sensitive_area")).not.toMatch(/problem|vulnerability/i);
  });

  it("maps every decision without exposing an enum", () => {
    expect(CHANGE_MAP_DECISION_LABELS).toEqual({
      pending_review: "Not reviewed yet",
      confirmed: "Looks right",
      edited: "I need to correct it",
      rejected: "Not accurate or not relevant",
      uncertain: "I’m not sure",
      needs_inspection: "I need to inspect this",
    });
    for (const key of Object.keys(CHANGE_MAP_DECISION_LABELS) as ChangeMapStudentDecision[]) {
      expect(decisionLabel(key)).not.toContain("_");
    }
  });

  it("shows uncertainty honestly without confidence, scores, or verification claims", () => {
    expect(CHANGE_MAP_AI_UNCERTAINTY_LABELS).toEqual({
      supported: "Clearly supported by the imported material",
      ambiguous: "The imported material is unclear",
      needs_inspection: "Needs a closer look",
    });
    for (const value of Object.values(CHANGE_MAP_AI_UNCERTAINTY_LABELS)) {
      expect(value).not.toMatch(/verified|confidence|\d+%/i);
    }
    expect(aiUncertaintyLabel("ambiguous")).toContain("unclear");
  });

  it("maps source fields to plain-language labels", () => {
    expect(CHANGE_MAP_SOURCE_FIELD_LABELS).toEqual({
      content: "Imported material",
      changed_files: "Changed-file list",
      student_summary: "Your summary",
    });
    expect(sourceFieldLabel("student_summary")).not.toContain("_");
  });
});

describe("category grouping", () => {
  it("omits empty categories, keeps fixed category order, and preserves item order", () => {
    const items = [
      aiItem("b-1", "behavior_change"),
      aiItem("f-1", "changed_file"),
      aiItem("b-2", "behavior_change"),
      aiItem("q-1", "question_to_understand"),
    ];
    const grouped = groupItemsByCategory(items);
    expect(grouped.map((group) => group.category)).toEqual([
      "changed_file",
      "behavior_change",
      "question_to_understand",
    ]);
    expect(grouped[1].items.map((item) => item.item_id)).toEqual(["b-1", "b-2"]);
  });
});

describe("review progress and effective display", () => {
  it.each([
    "confirmed",
    "edited",
    "rejected",
    "uncertain",
    "needs_inspection",
  ] as const)("counts %s as reviewed", (decision) => {
    const stored = map({ items: [aiItem("one", "behavior_change", decision)] });
    expect(deriveReviewProgress(stored, reviewStateFromMap(stored))).toEqual({
      reviewed: 1,
      total: 1,
      pending: 0,
    });
  });

  it("does not count pending or missing local decisions as reviewed", () => {
    const stored = map({ items: [aiItem("one", "behavior_change")] });
    const state = reviewStateFromMap(stored);
    expect(deriveReviewProgress(stored, state).pending).toBe(1);
    delete state.itemDecisions.one;
    expect(deriveReviewProgress(stored, state).reviewed).toBe(0);
    expect(pendingItemIds(stored, state)).toEqual(["one"]);
  });

  it("counts student-added items consistently as reviewed", () => {
    const stored = map({ items: [aiItem("one", "behavior_change", "confirmed"), studentItem("sa-one")] });
    expect(deriveReviewProgress(stored, reviewStateFromMap(stored))).toEqual({
      reviewed: 2,
      total: 2,
      pending: 0,
    });
  });

  it("does not report an incomplete student-added row as reviewed", () => {
    const stored = map({ items: [aiItem("one", "behavior_change", "confirmed")] });
    const state = reviewStateFromMap(stored);
    state.studentAddedItems.push({
      localId: "local-empty",
      category: "changed_file",
      studentText: "   ",
      studentNote: "",
      studentDecision: "confirmed",
    });
    expect(deriveReviewProgress(stored, state)).toEqual({ reviewed: 1, total: 2, pending: 1 });
  });

  it("uses the AI draft for accepted, pending, rejected, and unresolved records", () => {
    for (const decision of ["confirmed", "pending_review", "rejected", "uncertain", "needs_inspection"] as const) {
      const item = aiItem("one", "behavior_change", decision);
      expect(effectiveDisplayText(item)).toBe(item.draft_text);
    }
  });

  it("uses student text for corrected and student-added records", () => {
    expect(effectiveDisplayText(aiItem("one", "behavior_change", "edited"))).toContain(
      "corrected by me"
    );
    expect(effectiveDisplayText(studentItem("sa-one"))).toBe("I added this missing decision.");
  });
});

describe("student-only update payload", () => {
  it("sends only allowed fields for AI decisions and the full student-added replacement set", () => {
    const stored = map({
      items: [
        aiItem("confirmed", "changed_file", "confirmed"),
        aiItem("edited", "behavior_change", "edited"),
        aiItem("rejected", "unresolved_risk", "rejected"),
        aiItem("uncertain", "unverified_behavior", "uncertain"),
        aiItem("inspect", "security_sensitive_area", "needs_inspection"),
        studentItem("sa-one"),
      ],
    });
    const state = reviewStateFromMap(stored);
    state.itemDecisions.edited.studentNote = "My note";
    const payload = deriveSavePayload(stored, state);

    expect(payload.updates).toHaveLength(5);
    expect(payload.updates.find((item) => item.item_id === "edited")).toEqual({
      item_id: "edited",
      student_decision: "edited",
      student_text: "edited corrected by me.",
      student_note: "My note",
    });
    expect(payload.updates.find((item) => item.item_id === "rejected")?.student_text).toBeNull();
    expect(payload.student_added_items).toEqual([
      {
        category: "implementation_decision",
        student_text: "I added this missing decision.",
        student_note: "I still need to inspect it.",
        student_decision: "uncertain",
      },
    ]);
  });

  it("never includes server-owned provenance, drafts, references, origins, ids for added items, timestamps, or status", () => {
    const stored = map({ items: [aiItem("one", "behavior_change", "confirmed"), studentItem("sa-one")] });
    const serialized = JSON.stringify(deriveSavePayload(stored, reviewStateFromMap(stored)));
    for (const forbidden of [
      "origin",
      "draft_text",
      "ai_uncertainty",
      "source_references",
      "generated_at",
      "confirmed_at",
      "source_import_saved_at",
      "schema_version",
      '"status"',
      "sa-one",
    ]) {
      expect(serialized).not.toContain(forbidden);
    }
  });

  it("requires corrected text, validates student-added items, and never silently truncates", () => {
    const stored = map({ items: [aiItem("one", "behavior_change", "edited")] });
    const state = reviewStateFromMap(stored);
    state.itemDecisions.one.studentText = "   ";
    expect(reviewBlocker(stored, state)).toMatch(/correction/i);
    state.itemDecisions.one.studentText = "x".repeat(601);
    expect(reviewBlocker(stored, state)).toMatch(/600-character/i);
    expect(state.itemDecisions.one.studentText).toHaveLength(601);
    state.itemDecisions.one.studentText = "A real correction";
    state.studentAddedItems.push({
      localId: "local-1",
      category: "behavior_change",
      studentText: "",
      studentNote: "",
      studentDecision: "confirmed",
    });
    expect(reviewBlocker(stored, state)).toMatch(/describe each item/i);
  });
});

describe("dirty state and confirmation readiness", () => {
  it("detects real edits and reconciles cleanly to the server map", () => {
    const stored = map();
    const state = reviewStateFromMap(stored);
    expect(isReviewDirty(stored, state)).toBe(false);
    state.itemDecisions["cm-file"].studentDecision = "confirmed";
    expect(isReviewDirty(stored, state)).toBe(true);
  });

  it("ignores retained correction text after returning to the saved decision", () => {
    const stored = map({ items: [aiItem("one", "behavior_change", "confirmed")] });
    const state = reviewStateFromMap(stored);
    state.itemDecisions.one.studentDecision = "edited";
    state.itemDecisions.one.studentText = stored.items[0].draft_text ?? "";
    state.itemDecisions.one.studentDecision = "confirmed";
    expect(isReviewDirty(stored, state)).toBe(false);
  });

  it("matches backend Unicode code-point limits instead of UTF-16 units", () => {
    const stored = map({ items: [aiItem("one", "behavior_change", "edited")] });
    const state = reviewStateFromMap(stored);
    state.itemDecisions.one.studentText = "🚀".repeat(600);
    expect(changeMapCharacterCount(state.itemDecisions.one.studentText)).toBe(600);
    expect(reviewBlocker(stored, state)).toBeNull();
    state.itemDecisions.one.studentText += "🚀";
    expect(reviewBlocker(stored, state)).toMatch(/600-character/i);
  });

  it("blocks pending, unsaved, stale, and already-confirmed maps", () => {
    const pending = map();
    expect(confirmationReadiness(pending, reviewStateFromMap(pending), false).message).toMatch(
      /review every/i
    );

    const reviewed = map({ items: [aiItem("one", "behavior_change", "uncertain")] });
    expect(confirmationReadiness(reviewed, reviewStateFromMap(reviewed), true).message).toMatch(
      /save/i
    );
    expect(
      confirmationReadiness({ ...reviewed, stale: true }, reviewStateFromMap(reviewed), false)
        .message
    ).toMatch(/regenerate/i);
    expect(
      confirmationReadiness(
        { ...reviewed, status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" },
        reviewStateFromMap(reviewed),
        false
      ).message
    ).toMatch(/already/i);
  });

  it("allows honest unresolved outcomes once every AI item is reviewed and saved", () => {
    const stored = map({
      items: [
        aiItem("uncertain", "behavior_change", "uncertain"),
        aiItem("inspect", "unresolved_risk", "needs_inspection"),
        aiItem("rejected", "out_of_scope_change", "rejected"),
      ],
    });
    expect(confirmationReadiness(stored, reviewStateFromMap(stored), false)).toEqual({
      allowed: true,
      message: "Your map is ready to confirm.",
    });
  });
});

describe("generation, status, sparse, and stale helpers", () => {
  it("omits the normal generation body and sends replace_existing only deliberately", () => {
    expect(generationRequestBody(false)).toBeUndefined();
    expect(generationRequestBody(true)).toEqual({ replace_existing: true });
  });

  it("derives safe statuses without correctness claims", () => {
    expect(changeMapStepStatus(null)).toEqual({ label: "not created", tone: "idle" });
    expect(changeMapStepStatus(map())).toEqual({ label: "draft needs review", tone: "draft" });
    expect(changeMapStepStatus(map({ stale: true }))).toEqual({ label: "stale", tone: "stale" });
    expect(
      changeMapStepStatus(map({ status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" }))
    ).toEqual({ label: "reviewed", tone: "done" });
    expect(humanSafeStatusCopy(map())).not.toMatch(/verified|correct/i);
    expect(isMapStale(map({ stale: true }))).toBe(true);
  });

  it("recognizes a question-only sparse map without inventing filler", () => {
    expect(
      hasOnlyQuestionItems(map({ items: [aiItem("q", "question_to_understand")] }))
    ).toBe(true);
    expect(hasOnlyQuestionItems(map())).toBe(false);
  });

  it("derives every page state without triggering generation", () => {
    expect(deriveChangeMapPageModel(false, null, false, false).state).toBe("missing_import");
    expect(deriveChangeMapPageModel(true, null, false, false).state).toBe(
      "ready_to_generate"
    );
    expect(deriveChangeMapPageModel(true, null, true, false).state).toBe("generating");
    expect(deriveChangeMapPageModel(true, null, false, true).state).toBe(
      "generation_failed"
    );
    expect(deriveChangeMapPageModel(true, map(), false, false).state).toBe("draft");
    expect(
      deriveChangeMapPageModel(
        true,
        map({ status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" }),
        false,
        false
      ).state
    ).toBe("confirmed");
    expect(deriveChangeMapPageModel(true, map({ stale: true }), false, false).state).toBe(
      "stale"
    );
  });

  it("derives redaction and truncation notices from safe metadata only", () => {
    expect(
      deriveChangeMapPageModel(
        true,
        map({ source_redacted: true, source_truncated: true }),
        false,
        false
      )
    ).toMatchObject({ showRedactionNotice: true, showTruncationNotice: true });
  });

  it("holds prevention-first, non-blaming, non-verification page copy", () => {
    expect(CHANGE_MAP_PAGE_TITLE).toBe("Review Your Change Map");
    expect(CHANGE_MAP_PAGE_INTRO).toMatch(/review and correct/i);
    expect(CHANGE_MAP_HONESTY_LINE).toMatch(/draft—not proof/i);
    expect(CHANGE_MAP_GENERATION_FAILURE).toMatch(/safely grounded/i);
    const copy = [
      CHANGE_MAP_PAGE_INTRO,
      CHANGE_MAP_HONESTY_LINE,
      CHANGE_MAP_GENERATION_FAILURE,
    ].join(" ");
    expect(copy).not.toMatch(/you failed|your project is invalid|verified change|gemini|openrouter/i);
  });
});

describe("scoped local review drafts", () => {
  it("scopes the surface by phase and generated map version", () => {
    const stored = map();
    expect(changeMapDraftSurface(2, stored)).toBe(
      "change_map_review:2:2026-07-13T10:01:00Z"
    );
    expect(changeMapDraftSurface(2, stored)).not.toBe(changeMapDraftSurface(3, stored));
    expect(changeMapDraftSurface(2, stored)).not.toBe(
      changeMapDraftSurface(2, { ...stored, generated_at: "2026-07-13T12:00:00Z" })
    );
  });

  it("restores student-owned state for the exact server map", () => {
    const stored = map();
    const state = reviewStateFromMap(stored);
    state.itemDecisions["cm-file"].studentDecision = "rejected";
    state.itemDecisions["cm-file"].studentNote = "It was already there.";
    expect(restoreReviewDraft(stored, state)).toEqual(state);
  });

  it("invalidates drafts when the map changes, becomes stale, or is malformed", () => {
    const stored = map();
    const state = reviewStateFromMap(stored);
    expect(restoreReviewDraft({ ...stored, stale: true }, state)).toBeNull();
    expect(
      restoreReviewDraft(
        { ...stored, items: [...stored.items, aiItem("new", "unresolved_risk")] },
        state
      )
    ).toBeNull();
    expect(restoreReviewDraft(stored, { itemDecisions: {}, studentAddedItems: "bad" })).toBeNull();
  });

  it("stores no raw import, source reference, prompt, origin, timestamp, or server status fields", () => {
    const serialized = JSON.stringify(reviewStateFromMap(map()));
    for (const forbidden of [
      "source_references",
      "supporting_excerpt",
      "draft_text",
      "origin",
      "generated_at",
      "source_import_saved_at",
      "schema_version",
      '"status"',
      "provider",
      "prompt",
    ]) {
      expect(serialized).not.toContain(forbidden);
    }
  });
});

describe("phase next-step logic and N/5 preservation", () => {
  it("routes through import, Change Map creation, review, stale regeneration, then Review Board", () => {
    expect(
      derivePhaseNextStep(sections({ implementation_import: null }), null).label
    ).toBe("Bring Back What Changed");
    expect(derivePhaseNextStep(sections(), null).label).toBe("Continue Change Map");
    expect(derivePhaseNextStep(sections(), map()).label).toBe("Continue Change Map");
    expect(derivePhaseNextStep(sections(), map({ stale: true })).label).toBe(
      "Rebuild Change Map"
    );
    expect(
      derivePhaseNextStep(
        sections(),
        map({ status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" })
      )
    ).toMatchObject({ label: "Continue Review", href: "/app/phase/review" });
  });

  it("routes linked Review through in-progress, stale, complete, Verification, and Evidence", () => {
    const confirmed = map({ status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" });
    expect(derivePhaseNextStep(sections({ review_board: linkedReview() }), confirmed).label).toBe(
      "Continue Review"
    );
    expect(derivePhaseNextStep(sections({ review_board: linkedReview("pending", true) }), confirmed).label).toBe(
      "Rebuild Review"
    );
    expect(derivePhaseNextStep(sections({ review_board: linkedReview("uncertain") }), confirmed)).toMatchObject({
      label: "Continue Verification",
      href: "/app/phase/verify",
    });
    expect(derivePhaseNextStep(sections({
      review_board: linkedReview("keep"),
      verification: { checks: [] },
    }), confirmed).label).toBe("Continue Evidence");
  });

  it("routes linked Verification through in-progress, stale, recorded, and zero-target states", () => {
    const confirmed = map({ status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" });
    const base = { review_board: linkedReview("keep") };
    expect(derivePhaseNextStep(sections({
      ...base,
      verification: linkedVerification(),
    }), confirmed).label).toBe("Continue Verification");
    expect(derivePhaseNextStep(sections({
      ...base,
      verification: linkedVerification(null, true),
    }), confirmed).label).toBe("Rebuild Verification");
    expect(derivePhaseNextStep(sections({
      ...base,
      verification: linkedVerification("fail"),
    }), confirmed).label).toBe("Continue Evidence");
    expect(derivePhaseNextStep(sections({
      ...base,
      verification: linkedVerification(null, false, true),
    }), confirmed).label).toBe("Continue Evidence");
  });

  it("routes linked Evidence through in-progress, stale, and server-complete states", () => {
    const confirmed = map({ status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" });
    const base = {
      review_board: linkedReview("keep"),
      verification: linkedVerification("pass"),
    };
    expect(derivePhaseNextStep(sections({ ...base, evidence: linkedEvidence() }), confirmed).label).toBe("Continue Evidence");
    expect(derivePhaseNextStep(sections({ ...base, evidence: linkedEvidence(false, true) }), confirmed).label).toBe("Rebuild Evidence");
    expect(derivePhaseNextStep(sections({ ...base, evidence: linkedEvidence(true) }), confirmed)).toMatchObject({
      label: "Start Project Defense",
      href: "/app/gate",
    });
  });

  it("keeps Prompt first, preserves manual Review continuation, and preserves N/5", () => {
    expect(derivePhaseNextStep(sections({ prompt_builder: null }), null).label).toBe(
      "Continue Prompt Builder"
    );
    const confirmed = map({ status: "confirmed", confirmed_at: "2026-07-13T11:00:00Z" });
    expect(
      derivePhaseNextStep(sections({ review_board: { files_changed: [] } }), confirmed).label
    ).toBe("Continue Evidence");
    const allFive = sections({
      review_board: { files_changed: [] },
      evidence: { entries: [] },
      verification: { checks: [] },
    });
    expect(Object.values(allFive).filter(Boolean)).toHaveLength(5);
    expect(derivePhaseNextStep(allFive, confirmed).label).toBe("Start Project Defense");
  });
});
