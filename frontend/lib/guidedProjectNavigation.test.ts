import { describe, expect, it } from "vitest";

import {
  buildGuidedProjectNavigation,
  GUIDED_JOURNEY,
  routeIsActive,
} from "./guidedProjectNavigation";
import type {
  Evaluation,
  GateCurrent,
  LinkedEvidenceArtifact,
  LinkedReviewBoardArtifact,
  LinkedVerificationArtifact,
  StoredChangeMap,
  WorkflowPhaseState,
  WorkflowSections,
} from "./types";

const evaluation = (patch: Partial<Evaluation> = {}): Evaluation => ({
  state: "gate_ready",
  project_status: "active",
  next_action: "Take the gate.",
  current_phase: 1,
  phase_title: "Foundation",
  total_phases: 7,
  completed_phases: 0,
  completed_task_count: 2,
  total_task_count: 2,
  incomplete_tasks: [],
  recent_gate: null,
  unlocks: [],
  ...patch,
});

const confirmedMap = (patch: Partial<StoredChangeMap> = {}): StoredChangeMap => ({
  schema_version: "1.0",
  status: "confirmed",
  source_import_saved_at: "2026-07-14T09:00:00Z",
  generated_at: "2026-07-14T09:05:00Z",
  confirmed_at: "2026-07-14T09:10:00Z",
  source_redacted: false,
  source_truncated: false,
  stale: false,
  items: [],
  ...patch,
});

const linkedReview = (
  decision: LinkedReviewBoardArtifact["review_targets"][number]["review_decision"] = "keep",
  stale = false
): LinkedReviewBoardArtifact => ({
  files_changed: [],
  initialized_from_change_map: true,
  source_change_map_generated_at: "2026-07-14T09:05:00Z",
  source_change_map_confirmed_at: "2026-07-14T09:10:00Z",
  saved_at: "2026-07-14T09:20:00Z",
  stale,
  review_targets: [
    {
      review_target_id: "rv-0123456789ab",
      change_map_item_id: "cm-0123456789ab",
      change_map_category: "behavior_change",
      change_map_origin: "ai_inferred",
      change_map_student_decision: "confirmed",
      change_text: "A route changed.",
      source_resolution: "confirmed",
      review_decision: decision,
      student_rationale: null,
      student_revision: null,
    },
  ],
});

const linkedVerification = (
  result: LinkedVerificationArtifact["verification_targets"][number]["result"] = "pass",
  stale = false,
  zero = false
): LinkedVerificationArtifact => ({
  checks: [],
  initialized_from_review: true,
  initialized_at: "2026-07-14T09:30:00Z",
  saved_at: "2026-07-14T09:40:00Z",
  source_review_binding: {
    source_change_map_generated_at: "2026-07-14T09:05:00Z",
    source_change_map_confirmed_at: "2026-07-14T09:10:00Z",
    review_saved_at: "2026-07-14T09:20:00Z",
    review_target_fingerprint: "a".repeat(64),
  },
  stale,
  verification_targets: zero
    ? []
    : [
        {
          verification_target_id: "vt-0123456789ab",
          review_target_id: "rv-0123456789ab",
          change_map_item_id: "cm-0123456789ab",
          category: "behavior_change",
          source_text: "A route changed.",
          source_rationale: null,
          suggested_check: "Call the route.",
          student_check: null,
          result,
          result_notes: result === "fail" ? "Returned 500." : null,
        },
      ],
});

const linkedEvidence = (complete = true, stale = false): LinkedEvidenceArtifact => ({
  entries: [],
  summary: null,
  saved_at: "2026-07-14T09:50:00Z",
  initialized_from_verification: true,
  stale,
  evidence_record_complete: complete,
  evidence_targets: [
    {
      evidence_target_id: "ev-0123456789ab",
      source_verification_target_id: "vt-0123456789ab",
      category: "behavior_change",
      check_snapshot: "Call the route.",
      verification_result_snapshot: "pass",
      verification_result_notes_snapshot: null,
      evidence_status: complete ? "evidence_unavailable" : "not_addressed",
      entries: [],
      explanation: null,
      unavailable_reason: complete ? "No capture was available." : null,
    },
  ],
});

const sections = (patch: Partial<WorkflowSections> = {}): WorkflowSections => ({
  prompt_builder: { inputs: {}, generated_prompt: "Build it", saved_at: "2026-07-14T08:00:00Z" },
  implementation_import: {
    source_kind: "manual_summary",
    changed_files: [],
    student_summary: "The route changed.",
    saved_at: "2026-07-14T09:00:00Z",
  },
  review_board: linkedReview(),
  verification: linkedVerification(),
  evidence: linkedEvidence(),
  ...patch,
});

const workflow = (
  sectionPatch: Partial<WorkflowSections> = {},
  map: StoredChangeMap | null = confirmedMap()
): WorkflowPhaseState => ({ phase: 1, sections: sections(sectionPatch), change_map: map });

const gate = (patch: Partial<GateCurrent> = {}): GateCurrent => ({
  phase: 1,
  phase_title: "Foundation",
  state: "not_started",
  anchor_prompt: "Name one thing.",
  ...patch,
});

const build = (
  sectionPatch: Partial<WorkflowSections> = {},
  map: StoredChangeMap | null = confirmedMap(),
  evaluationPatch: Partial<Evaluation> = {},
  gatePatch: Partial<GateCurrent> = {}
) =>
  buildGuidedProjectNavigation({
    evaluation: evaluation(evaluationPatch),
    workflow: workflow(sectionPatch, map),
    gate: gate(gatePatch),
    projectLabel: "A deliberately very long project name that still remains readable",
  });

describe("guided project navigation model", () => {
  it("uses the exact implemented order, stable routes, and no M17 stages", () => {
    expect(GUIDED_JOURNEY.map(({ id, label, href }) => ({ id, label, href }))).toEqual([
      { id: "prompt", label: "Prompt Builder", href: "/app/phase/prompt" },
      { id: "import", label: "Bring Back What Changed", href: "/app/phase/import" },
      { id: "change_map", label: "Change Map", href: "/app/phase/change-map" },
      { id: "review", label: "Review", href: "/app/phase/review" },
      { id: "verification", label: "Verification", href: "/app/phase/verify" },
      { id: "evidence", label: "Evidence", href: "/app/phase/evidence" },
      { id: "defense", label: "Project Defense", href: "/app/gate" },
      { id: "report", label: "Defense Report", href: "/app/report" },
    ]);
    expect(GUIDED_JOURNEY.map((item) => item.label)).not.toEqual(
      expect.arrayContaining(["Guided mode", "Builder mode", "Recovery mode", "80% Trap"])
    );
  });

  it("keeps Project Home and a safe setup action before an active workflow", () => {
    const model = buildGuidedProjectNavigation({
      evaluation: evaluation({ state: "not_started", current_phase: undefined }),
      workflow: null,
      gate: null,
    });
    expect(model.projectHome).toEqual({ label: "Project Home", href: "/app" });
    expect(model.continueAction).toMatchObject({ label: "Start with project intake", href: "/app/intake" });
    expect(model.journey.every((item) => item.state === "later")).toBe(true);
    expect(model.projectRecord).toEqual([]);
  });

  it("does not guess progress when required saved navigation state is missing", () => {
    const model = buildGuidedProjectNavigation({ evaluation: evaluation(), workflow: null, gate: null });
    expect(model.journey.every((item) => item.state === "later")).toBe(true);
    expect(model.projectRecord).toEqual([]);
  });

  it("continues Prompt Builder until a server-saved prompt exists", () => {
    const model = build({ prompt_builder: null, implementation_import: null, review_board: null, verification: null, evidence: null }, null);
    expect(model.continueAction).toMatchObject({ label: "Continue Prompt Builder", stageId: "prompt" });
    expect(model.journey[0].state).toBe("continue");
    expect(model.projectRecord).toEqual([]);
  });

  it("moves a saved Prompt to Project Record and continues Import", () => {
    const model = build({ implementation_import: null, review_board: null, verification: null, evidence: null }, null);
    expect(model.continueAction.label).toBe("Bring Back What Changed");
    expect(model.projectRecord.map((item) => item.stageId)).toEqual(["prompt"]);
    expect(model.journey[0].state).toBe("complete");
    expect(model.journey[1].state).toBe("continue");
  });

  it("does not call an Import a completed Change Map", () => {
    const model = build({ review_board: null, verification: null, evidence: null }, null);
    expect(model.continueAction).toMatchObject({ label: "Continue Change Map", stageId: "change_map" });
    expect(model.journey[2].state).toBe("ready");
    expect(model.projectRecord.some((item) => item.stageId === "change_map")).toBe(false);
  });

  it("continues a draft map and repairs a stale map before all downstream work", () => {
    expect(build({}, confirmedMap({ status: "draft", confirmed_at: null })).continueAction.label).toBe("Continue Change Map");
    const stale = build({}, confirmedMap({ stale: true }));
    expect(stale.continueAction.label).toBe("Rebuild Change Map");
    expect(stale.journey[2].state).toBe("needs_attention");
    expect(stale.projectRecord.find((item) => item.stageId === "change_map")).toMatchObject({ stateLabel: "Needs update" });
  });

  it("handles missing, incomplete, complete, and stale Review from saved decisions", () => {
    expect(build({ review_board: null, verification: null, evidence: null }).continueAction.label).toBe("Continue Review");
    expect(build({ review_board: linkedReview("pending"), verification: null, evidence: null }).continueAction.label).toBe("Continue Review");
    expect(build({ verification: null, evidence: null }).continueAction.label).toBe("Continue Verification");
    const stale = build({ review_board: linkedReview("keep", true) });
    expect(stale.continueAction.label).toBe("Rebuild Review");
    expect(stale.projectRecord.find((item) => item.stageId === "review")?.stateLabel).toBe("Needs update");
  });

  it("uses saved Verification completion, not pass rate or result correctness", () => {
    expect(build({ verification: linkedVerification(null), evidence: null }).continueAction.label).toBe("Continue Verification");
    expect(build({ verification: linkedVerification("fail"), evidence: null }).continueAction.label).toBe("Continue Evidence");
    expect(build({ verification: linkedVerification("pass", false, true), evidence: null }).continueAction.label).toBe("Continue Evidence");
    expect(build({ verification: linkedVerification("pass", true) }).continueAction.label).toBe("Rebuild Verification");
  });

  it("requires the server Evidence completion flag and never section presence alone", () => {
    const incomplete = build({ evidence: linkedEvidence(false) });
    expect(incomplete.continueAction.label).toBe("Continue Evidence");
    expect(incomplete.journey[5].state).toBe("continue");
    const stale = build({ evidence: linkedEvidence(false, true) });
    expect(stale.continueAction.label).toBe("Rebuild Evidence");
    expect(stale.projectRecord.find((item) => item.stageId === "evidence")?.stateLabel).toBe("Needs update");
  });

  it("fails malformed linked Evidence completion closed without breaking manual Evidence", () => {
    for (const completion of [undefined, null, "true"]) {
      const malformed = {
        ...linkedEvidence(true),
        evidence_record_complete: completion,
      } as unknown as LinkedEvidenceArtifact;
      const model = build({ evidence: malformed });
      expect(model.continueAction).toMatchObject({
        label: "Continue Evidence",
        stageId: "evidence",
      });
      expect(model.journey[5].state).toBe("continue");
      expect(model.journey[6].state).toBe("later");
    }

    const manual = build({
      evidence: { entries: [], summary: "Manual note", saved_at: "2026-07-14T10:05:00Z" },
    });
    expect(manual.continueAction.stageId).toBe("defense");
  });

  it("selects the earliest stale dependency when multiple records are stale", () => {
    const reviewFirst = build({
      review_board: linkedReview("keep", true),
      verification: linkedVerification("pass", true),
      evidence: linkedEvidence(false, true),
    });
    expect(reviewFirst.continueAction.label).toBe("Rebuild Review");
    expect(reviewFirst.journey.filter((item) => item.state === "needs_attention").map((item) => item.id)).toEqual([
      "review",
      "verification",
      "evidence",
    ]);
    const verificationFirst = build({
      verification: linkedVerification("pass", true),
      evidence: linkedEvidence(false, true),
    });
    expect(verificationFirst.continueAction.label).toBe("Rebuild Verification");
  });

  it("does not offer Defense while saved build tasks remain", () => {
    const model = build({}, confirmedMap(), {
      state: "in_progress",
      completed_task_count: 1,
      incomplete_tasks: [{ task_id: "human-1", description: "Inspect the route" }],
    });
    expect(model.continueAction).toMatchObject({ label: "Finish phase build tasks", href: "/app/phase", stageId: null });
    expect(model.journey[6].state).toBe("later");
  });

  it("preserves Defense not-started, active, retry, cooldown, and final states", () => {
    expect(build().continueAction.label).toBe("Start Project Defense");
    expect(build({}, confirmedMap(), {}, { state: "in_progress", gate_session_id: "gate-1", next_action: "turn2" }).continueAction.label).toBe("Continue Project Defense");
    expect(build({}, confirmedMap(), { recent_gate: { outcome: "failed", summary: "Try again" } }).continueAction.label).toBe("Try Project Defense again");
    const cooldown = build({}, confirmedMap(), { state: "cooldown", cooldown_seconds_remaining: 600 }, { state: "cooldown", cooldown_seconds_remaining: 600 });
    expect(cooldown.continueAction).toMatchObject({ label: "Project Defense cooldown", href: null, unavailable: true });
    const complete = build({}, confirmedMap(), { state: "complete", completed_phases: 7 }, { state: "passed" });
    expect(complete.continueAction).toMatchObject({ label: "View Defense Report", href: "/app/report?phase=1" });
    expect(complete.journey[6].state).toBe("complete");
    expect(complete.journey[7].state).toBe("continue");
  });

  it("keeps a failed Defense and its Report in Project Record without calling it complete", () => {
    const model = build({}, confirmedMap(), {
      state: "cooldown",
      recent_gate: { outcome: "failed", summary: "Needs specifics" },
      cooldown_seconds_remaining: 900,
    }, { state: "cooldown", reason: "Needs specifics", cooldown_seconds_remaining: 900 });
    expect(model.projectRecord.find((item) => item.stageId === "defense")).toMatchObject({ state: "needs_attention" });
    expect(model.projectRecord.find((item) => item.stageId === "report")?.href).toBe("/app/report?phase=1");
  });

  it("keeps the most recent completed phase Report available on a later phase", () => {
    const model = build({ prompt_builder: null, implementation_import: null, review_board: null, verification: null, evidence: null }, null, {
      current_phase: 2,
      completed_phases: 1,
    });
    expect(model.projectRecord.find((item) => item.id === "report-Phase 1")?.href).toBe("/app/report?phase=1");
    expect(model.continueAction.label).toBe("Continue Prompt Builder");
  });

  it("keeps original manual Review, Verification, and Evidence records usable", () => {
    const manualReview = { files_changed: ["app.py"], saved_at: "2026-07-14T10:00:00Z" };
    const evidenceFirst = build({ review_board: manualReview, verification: null, evidence: null });
    expect(evidenceFirst.continueAction).toMatchObject({ label: "Continue Evidence", stageId: "evidence" });
    const verificationNext = build({
      review_board: manualReview,
      verification: null,
      evidence: { entries: [], summary: "Manual note", saved_at: "2026-07-14T10:05:00Z" },
    });
    expect(verificationNext.continueAction.stageId).toBe("verification");
    const complete = build({
      review_board: manualReview,
      verification: { checks: [], explanation: "Manual checks", saved_at: "2026-07-14T10:10:00Z" },
      evidence: { entries: [], summary: "Manual note", saved_at: "2026-07-14T10:05:00Z" },
    });
    expect(complete.continueAction.stageId).toBe("defense");
    expect(complete.projectRecord.map((item) => item.stageId)).toEqual(expect.arrayContaining(["review", "verification", "evidence"]));
  });

  it("keeps active route identity independent from workflow state", () => {
    expect(routeIsActive("/app/phase/change-map", "/app/phase/change-map")).toBe(true);
    expect(routeIsActive("/app/phase/evidence", "/app/phase/change-map")).toBe(false);
    expect(routeIsActive("/app/phase/prompt", "/app/phase")).toBe(false);
    expect(routeIsActive("/app", "/app")).toBe(true);
    expect(routeIsActive("/app/report", "/app/report?phase=1")).toBe(true);
  });
});
