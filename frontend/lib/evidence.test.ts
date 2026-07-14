import { describe, expect, it } from "vitest";

import {
  EVIDENCE_CONTENT_MAX,
  EVIDENCE_KIND_OPTIONS,
  EVIDENCE_REQUEST_MAX,
  EVIDENCE_STATUSES,
  EVIDENCE_TEXT_MAX,
  canRebuildEvidenceFromPreview,
  canonicalEvidenceTargetUpdate,
  deriveEvidenceSavePayload,
  eligibleEvidenceTargets,
  evidenceArtifactMode,
  evidenceCharacterCount,
  evidenceCompletionSummary,
  evidenceFormBlocker,
  evidenceInitializationBody,
  evidencePreviewState,
  evidenceRequestCharacterCount,
  evidenceResultDescription,
  evidenceResultLabel,
  evidenceStatusLabel,
  evidenceStepStatus,
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
  safeEvidenceLink,
  shouldKeepEvidenceSaveNotice,
  targetFormFromEvidence,
  validateEvidenceEntry,
  validateEvidenceTarget,
  type LinkedEvidenceFormState,
} from "./evidence";
import type {
  EvidenceHandoffPreview,
  EvidenceHandoffTarget,
  LinkedEvidenceArtifact,
  LinkedEvidenceTarget,
  LinkedVerificationArtifact,
} from "./types";

function sourceTarget(
  id: string,
  result: EvidenceHandoffTarget["result"],
  eligibility: EvidenceHandoffTarget["eligibility"],
  overrides: Partial<EvidenceHandoffTarget> = {}
): EvidenceHandoffTarget {
  return {
    verification_target_id: id,
    category: "behavior_change",
    check: `Perform check ${id}.`,
    result,
    result_notes: result === "unrecorded" ? null : `Recorded ${result}.`,
    performed: result === "pass" || result === "fail",
    eligibility,
    ineligibility_reason: eligibility === "eligible" ? null : "not_performed",
    ...overrides,
  };
}

function preview(
  overrides: Partial<EvidenceHandoffPreview> = {}
): EvidenceHandoffPreview {
  const targets = [
    sourceTarget("vt-111111111111", "pass", "eligible"),
    sourceTarget("vt-222222222222", "fail", "eligible"),
    sourceTarget("vt-333333333333", "skipped", "ineligible"),
    sourceTarget("vt-444444444444", "not_applicable", "ineligible"),
  ];
  return {
    mode: "linked_verification",
    verification_state: "current",
    eligible_count: 2,
    targets,
    guidance: "Select performed results.",
    ...overrides,
  };
}

function evidenceTarget(
  id: string,
  overrides: Partial<LinkedEvidenceTarget> = {}
): LinkedEvidenceTarget {
  return {
    evidence_target_id: id,
    source_verification_target_id: `vt-${id.slice(3)}`,
    category: "behavior_change",
    check_snapshot: `Perform check ${id}.`,
    verification_result_snapshot: "pass",
    verification_result_notes_snapshot: "Expected behavior remained visible.",
    evidence_status: "not_addressed",
    entries: [],
    explanation: null,
    unavailable_reason: null,
    ...overrides,
  };
}

function evidence(
  overrides: Partial<LinkedEvidenceArtifact> = {}
): LinkedEvidenceArtifact {
  return {
    entries: [],
    summary: null,
    saved_at: "2026-07-14T12:00:00Z",
    initialized_from_verification: true,
    stale: false,
    evidence_record_complete: false,
    evidence_targets: [evidenceTarget("ev-111111111111")],
    ...overrides,
  };
}

function verification(result: "pass" | null = "pass"): LinkedVerificationArtifact {
  return {
    checks: [],
    explanation: null,
    saved_at: "2026-07-14T11:00:00Z",
    initialized_at: "2026-07-14T10:00:00Z",
    initialized_from_review: true,
    stale: false,
    source_review_binding: {
      source_change_map_generated_at: "2026-07-14T08:00:00Z",
      source_change_map_confirmed_at: "2026-07-14T09:00:00Z",
      review_saved_at: "2026-07-14T09:30:00Z",
      review_target_fingerprint: "a".repeat(64),
    },
    verification_targets: [{
      verification_target_id: "vt-111111111111",
      review_target_id: "rv-111111111111",
      change_map_item_id: "cm-1",
      category: "behavior_change",
      source_text: "A behavior changed.",
      source_rationale: null,
      suggested_check: "Perform the behavior check.",
      student_check: null,
      result,
      result_notes: result ? "Observed it." : null,
    }],
  };
}

describe("linked/manual Evidence modes and exact contracts", () => {
  it("distinguishes none, linked, manual, and malformed linked safely", () => {
    expect(evidenceArtifactMode(null)).toBe("none");
    expect(evidenceArtifactMode(evidence())).toBe("linked");
    expect(evidenceArtifactMode({ entries: [], summary: null })).toBe("legacy");
    const malformed = { ...evidence(), evidence_targets: [{ bad: true }] };
    expect(isLinkedEvidenceArtifact(malformed)).toBe(false);
    expect(evidenceArtifactMode(malformed)).toBe("invalid_linked");
  });

  it("keeps the exact three statuses and nine Evidence kinds", () => {
    expect(EVIDENCE_STATUSES).toEqual([
      "not_addressed",
      "evidence_recorded",
      "evidence_unavailable",
    ]);
    expect(EVIDENCE_KIND_OPTIONS.map((kind) => kind.value)).toEqual([
      "screenshot_note", "terminal_output", "test_output", "changed_files", "note",
      "repo_url", "commit_hash", "app_url", "api_response",
    ]);
    expect(evidenceStatusLabel("evidence_recorded")).toBe("Add supporting Evidence");
    expect(evidenceStatusLabel("evidence_unavailable")).not.toMatch(/recorded|verified/i);
  });
});

describe("server preview interpretation and explicit selection", () => {
  it("accepts exact preview shapes and fails malformed optional fields", () => {
    expect(isEvidenceHandoffPreview(preview())).toBe(true);
    expect(isEvidenceHandoffPreview({ ...preview(), targets: [{ ...preview().targets[0], result_notes: 7 }] })).toBe(false);
  });

  it("covers missing, manual, stale, incomplete, ready, and zero eligible states", () => {
    expect(evidencePreviewState(preview({ mode: "unavailable", verification_state: "verification_required", eligible_count: 0, targets: [] }))).toBe("verification_required");
    expect(evidencePreviewState(preview({ mode: "manual_verification", verification_state: "manual_verification", eligible_count: 0, targets: [] }))).toBe("manual_verification");
    expect(evidencePreviewState(preview({ verification_state: "stale", eligible_count: 0 }))).toBe("stale_verification");
    expect(evidencePreviewState(preview({ eligible_count: 0, targets: [sourceTarget("vt-555555555555", "unrecorded", "ineligible")] }))).toBe("incomplete_verification");
    expect(evidencePreviewState(preview())).toBe("ready");
    expect(evidencePreviewState(preview({ eligible_count: 0, targets: [sourceTarget("vt-333333333333", "skipped", "ineligible")] }))).toBe("zero_eligible");
  });

  it("trusts server eligibility, never preselects, and preserves pass/fail plus ineligible outcomes", () => {
    const value = preview();
    expect(eligibleEvidenceTargets(value).map((target) => target.result)).toEqual(["pass", "fail"]);
    expect(ineligibleEvidenceTargets(value).map((target) => target.result)).toEqual(["skipped", "not_applicable"]);
    expect(normalizeEvidenceSelection(value, [])).toEqual([]);
    expect(normalizeEvidenceSelection(value, [
      "vt-333333333333", "vt-222222222222", "vt-111111111111", "unknown",
    ])).toEqual(["vt-111111111111", "vt-222222222222"]);
  });

  it("keeps honest labels and meanings", () => {
    expect(evidenceResultLabel("pass")).toBe("Passed");
    expect(evidenceResultLabel("fail")).toBe("Failed");
    expect(evidenceResultLabel("unrecorded")).toBe("Not recorded yet");
    expect(evidenceResultDescription("fail")).toContain("problem or mismatch");
    expect(evidenceResultDescription("skipped")).toContain("not performed");
  });

  it("creates only the exact selected-id request and adds replacement deliberately", () => {
    expect(evidenceInitializationBody(["vt-111111111111"], false)).toEqual({
      selected_verification_target_ids: ["vt-111111111111"],
    });
    expect(evidenceInitializationBody(["vt-111111111111"], true)).toEqual({
      selected_verification_target_ids: ["vt-111111111111"],
      replace_existing: true,
    });
    expect(canRebuildEvidenceFromPreview(preview())).toBe(true);
    expect(canRebuildEvidenceFromPreview(preview({ verification_state: "stale" }))).toBe(false);
  });
});

describe("entry validation and Unicode-safe limits", () => {
  it("counts Unicode code points instead of UTF-16 units", () => {
    expect(evidenceCharacterCount("a😀b")).toBe(3);
    const tooLong = "😀".repeat(EVIDENCE_CONTENT_MAX + 1);
    expect(validateEvidenceEntry({ kind: "test_output", content: tooLong })).toContain("8,000");
    expect(tooLong).toHaveLength((EVIDENCE_CONTENT_MAX + 1) * 2);
  });

  it("validates empty, URL, commit, and unsafe-control content without truncation", () => {
    expect(validateEvidenceEntry({ kind: "note", content: "   " })).toContain("content");
    expect(validateEvidenceEntry({ kind: "repo_url", content: "ftp://example.com" })).toContain("http(s)");
    expect(validateEvidenceEntry({ kind: "commit_hash", content: "not-hex" })).toContain("hexadecimal");
    expect(validateEvidenceEntry({ kind: "terminal_output", content: "bad\u0000value" })).toContain("control");
    expect(validateEvidenceEntry({ kind: "terminal_output", content: "  indented\noutput" })).toBeNull();
  });

  it("renders only validated URL kinds as safe external links", () => {
    expect(safeEvidenceLink({ kind: "repo_url", content: "https://example.com/repo" })).toBe("https://example.com/repo");
    expect(safeEvidenceLink({ kind: "repo_url", content: "javascript:alert(1)" })).toBeNull();
    expect(safeEvidenceLink({ kind: "note", content: "https://example.com" })).toBeNull();
  });
});

describe("canonical active fields, safe payloads, and dirty state", () => {
  it("initializes forms from server fields without changing status", () => {
    expect(targetFormFromEvidence(evidence())["ev-111111111111"]).toEqual({
      status: "not_addressed", entries: [], explanation: "", unavailableReason: "",
    });
  });

  it("sends only status for not addressed and ignores every hidden field", () => {
    const target = evidence().evidence_targets[0];
    expect(canonicalEvidenceTargetUpdate(target, {
      status: "not_addressed",
      entries: [{ kind: "note", content: "hidden" }],
      explanation: "hidden",
      unavailableReason: "hidden",
    })).toEqual({ evidence_target_id: target.evidence_target_id, evidence_status: "not_addressed" });
  });

  it("sends entries/explanation only for recorded and reason only for unavailable", () => {
    const target = evidence().evidence_targets[0];
    expect(canonicalEvidenceTargetUpdate(target, {
      status: "evidence_recorded",
      entries: [{ kind: "test_output", content: "1 failed" }],
      explanation: "  This shows the observed failure.  ",
      unavailableReason: "hidden",
    })).toEqual({
      evidence_target_id: target.evidence_target_id,
      evidence_status: "evidence_recorded",
      entries: [{ kind: "test_output", content: "1 failed" }],
      explanation: "This shows the observed failure.",
    });
    expect(canonicalEvidenceTargetUpdate(target, {
      status: "evidence_unavailable", entries: [{ kind: "note", content: "hidden" }],
      explanation: "hidden", unavailableReason: "  Logs expired.  ",
    })).toEqual({
      evidence_target_id: target.evidence_target_id,
      evidence_status: "evidence_unavailable",
      unavailable_reason: "Logs expired.",
    });
  });

  it("sends changed updates only and never echoes provenance", () => {
    const artifact = evidence();
    const state = targetFormFromEvidence(artifact);
    state["ev-111111111111"] = {
      status: "evidence_recorded",
      entries: [{ kind: "test_output", content: "1 passed" }],
      explanation: "This supports the result.",
      unavailableReason: "",
    };
    const payload = deriveEvidenceSavePayload(artifact, state);
    expect(payload.target_updates).toHaveLength(1);
    const serialized = JSON.stringify(payload);
    for (const forbidden of [
      "source_verification_target_id", "review_target_id", "change_map_item_id",
      "check_snapshot", "verification_result_snapshot", "verification_result_notes_snapshot",
      "category", "binding", "fingerprint", "initialized", "stale", "complete",
    ]) expect(serialized).not.toContain(forbidden);
  });

  it("ignores inactive hidden edits in dirty comparison across all status transitions", () => {
    const recorded = evidence({ evidence_targets: [evidenceTarget("ev-111111111111", {
      evidence_status: "evidence_recorded",
      entries: [{ kind: "test_output", content: "1 passed" }],
      explanation: "Observed pass.",
    })] });
    const state = targetFormFromEvidence(recorded);
    expect(isLinkedEvidenceDirty(recorded, state)).toBe(false);
    state["ev-111111111111"].unavailableReason = "hidden";
    expect(isLinkedEvidenceDirty(recorded, state)).toBe(false);
    state["ev-111111111111"].status = "evidence_unavailable";
    expect(isLinkedEvidenceDirty(recorded, state)).toBe(true);
    state["ev-111111111111"].status = "evidence_recorded";
    expect(isLinkedEvidenceDirty(recorded, state)).toBe(false);
  });
});

describe("active validation, aggregate safety belt, and progress", () => {
  it("requires an entry only for recorded and a reason only for unavailable", () => {
    expect(validateEvidenceTarget({ status: "not_addressed", entries: [], explanation: "", unavailableReason: "" })).toEqual({});
    expect(validateEvidenceTarget({ status: "evidence_recorded", entries: [], explanation: "", unavailableReason: "" }).entries).toBeTruthy();
    expect(validateEvidenceTarget({ status: "evidence_unavailable", entries: [], explanation: "", unavailableReason: "" }).unavailableReason).toBeTruthy();
    expect(validateEvidenceTarget({ status: "evidence_unavailable", entries: [], explanation: "x".repeat(EVIDENCE_TEXT_MAX + 1), unavailableReason: "Reason" }).explanation).toBeUndefined();
  });

  it("rejects duplicate and aggregate-over-limit active entries", () => {
    const artifact = evidence();
    const state = targetFormFromEvidence(artifact);
    state["ev-111111111111"] = {
      status: "evidence_recorded",
      entries: [{ kind: "note", content: "same" }, { kind: "note", content: "same" }],
      explanation: "", unavailableReason: "",
    };
    expect(evidenceFormBlocker(artifact, state)).toContain("duplicate");
    state["ev-111111111111"].entries = Array.from({ length: 21 }, (_, index) => ({ kind: "note" as const, content: `entry ${index}` }));
    expect(evidenceFormBlocker(artifact, state)).toContain("at most 20");
  });

  it("counts the backend-style request belt in code points", () => {
    const small = { target_updates: [{ evidence_target_id: "ev-111111111111", evidence_status: "evidence_recorded" as const, entries: [{ kind: "note" as const, content: "😀" }], explanation: null }] };
    expect(evidenceRequestCharacterCount(small)).toBeLessThan(EVIDENCE_REQUEST_MAX);
    const large = { target_updates: [{ ...small.target_updates[0], entries: [{ kind: "note" as const, content: "x".repeat(EVIDENCE_REQUEST_MAX) }] }] };
    expect(evidenceRequestCharacterCount(large)).toBeGreaterThan(EVIDENCE_REQUEST_MAX);
  });

  it("keeps recorded, unavailable, unaddressed, entries, and addressed distinct", () => {
    const artifact = evidence({ evidence_targets: [
      evidenceTarget("ev-111111111111"),
      evidenceTarget("ev-222222222222"),
      evidenceTarget("ev-333333333333"),
    ] });
    const state = targetFormFromEvidence(artifact);
    state["ev-111111111111"] = { status: "evidence_recorded", entries: [{ kind: "test_output", content: "1 failed" }], explanation: "", unavailableReason: "" };
    state["ev-222222222222"] = { status: "evidence_unavailable", entries: [], explanation: "", unavailableReason: "Logs expired" };
    const progress = linkedEvidenceProgress(artifact, state);
    expect(progress).toEqual({ addressed: 2, recorded: 1, unavailable: 1, unaddressed: 1, entries: 1, total: 3 });
    expect(evidenceCompletionSummary(progress)).toBe("2 of 3 Evidence records addressed");
  });
});

describe("draft compatibility, stale behavior, completion, and navigation status", () => {
  it("scopes drafts by surface/phase/version without source context", () => {
    const artifact = evidence();
    const surface = linkedEvidenceDraftSurface(2, artifact);
    expect(surface).toMatch(/^linked_evidence:active-project:2:[0-9a-f]{8}$/);
    expect(surface).not.toContain(artifact.evidence_targets[0].check_snapshot);
    const value = linkedEvidenceDraftValue(artifact, targetFormFromEvidence(artifact));
    const serialized = JSON.stringify(value);
    expect(serialized).toContain("ev-111111111111");
    expect(serialized).not.toContain("Perform check");
    expect(serialized).not.toContain("Expected behavior");
  });

  it("restores exact compatible student fields and rejects stale/rebuilt drafts", () => {
    const artifact = evidence();
    const state = targetFormFromEvidence(artifact);
    state["ev-111111111111"].status = "evidence_unavailable";
    state["ev-111111111111"].unavailableReason = "No retained output";
    const value = linkedEvidenceDraftValue(artifact, state);
    expect(restoreLinkedEvidenceDraft(artifact, value)).toEqual(state);
    expect(restoreLinkedEvidenceDraft(evidence({ stale: true }), value)).toBeNull();
    expect(restoreLinkedEvidenceDraft(evidence({ saved_at: "new revision" }), value)).toBeNull();
  });

  it("keeps save acknowledgement only for the exact server revision", () => {
    const first = linkedEvidenceServerRevision(evidence());
    const second = linkedEvidenceServerRevision(evidence({ saved_at: "later" }));
    expect(shouldKeepEvidenceSaveNotice(first, first)).toBe(true);
    expect(shouldKeepEvidenceSaveNotice(first, second)).toBe(false);
  });

  it("uses the server completion field and distinguishes ready/in-progress/stale/manual", () => {
    expect(evidenceStepStatus(null, verification())).toEqual({ label: "ready to start", tone: "draft" });
    expect(evidenceStepStatus(null, verification(null))).toEqual({ label: "not available yet", tone: "idle" });
    expect(evidenceStepStatus({ entries: [], summary: null }, verification())).toEqual({ label: "saved", tone: "done" });
    expect(evidenceStepStatus(evidence(), verification())).toEqual({ label: "in progress", tone: "draft" });
    expect(evidenceStepStatus(evidence({ stale: true }), verification())).toEqual({ label: "stale", tone: "stale" });
    expect(evidenceStepStatus(evidence({ evidence_record_complete: true }), verification())).toEqual({ label: "record complete", tone: "done" });
  });
});
