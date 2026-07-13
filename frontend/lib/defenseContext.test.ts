import { describe, expect, it } from "vitest";

import {
  SPARSE_PREPARATION_TIP,
  WORKFLOW_PAGE_LINKS,
  WORKFLOW_SOURCE_ORDER,
  groupSummary,
  missingNote,
  preparationTips,
} from "./defenseContext";
import type { DefenseContextSummary } from "./types";

function summary(overrides: Partial<DefenseContextSummary> = {}): DefenseContextSummary {
  return {
    schema_version: "1.0",
    phase_number: 2,
    included_sources: [
      { source_id: "project", label: "Project", source_type: "system_project", truncated: false },
      { source_id: "phase", label: "Current phase", source_type: "system_roadmap", truncated: false },
      { source_id: "progress", label: "Build progress", source_type: "system_progress", truncated: false },
      { source_id: "intake", label: "Project intake", source_type: "student_intake", truncated: false },
      // deliberately out of Build Loop order — grouping must fix it
      { source_id: "workflow.verification", label: "Verification", source_type: "student_recorded_verification", truncated: false },
      { source_id: "workflow.prompt_builder", label: "Prompt", source_type: "student_artifact", truncated: false },
    ],
    missing_sources: [
      { source_id: "workflow.review_board", label: "Review Notes" },
      { source_id: "workflow.evidence", label: "Evidence" },
    ],
    has_truncation: false,
    artifact_aware: true,
    ...overrides,
  };
}

describe("groupSummary", () => {
  it("orders present workflow sources in Build Loop order", () => {
    const g = groupSummary(summary());
    expect(g.workflow.map((s) => s.source_id)).toEqual([
      "workflow.prompt_builder",
      "workflow.verification",
    ]);
    expect(g.hasWorkflowContext).toBe(true);
  });

  it("groups system sources instead of exposing individual chips", () => {
    const g = groupSummary(summary());
    expect(g.hasSystemContext).toBe(true);
    // system sources never appear in the workflow chip list
    expect(g.workflow.every((s) => s.source_id.startsWith("workflow."))).toBe(true);
  });

  it("lists missing workflow sources with human labels, in order", () => {
    const g = groupSummary(summary());
    expect(g.missingWorkflow.map((m) => m.label)).toEqual(["Review Notes", "Evidence"]);
  });

  it("handles the no-artifacts case as sparse, not broken", () => {
    const g = groupSummary(
      summary({
        included_sources: summary().included_sources.filter(
          (s) => !s.source_id.startsWith("workflow.")
        ),
        missing_sources: WORKFLOW_SOURCE_ORDER.map((id) => ({
          source_id: id,
          label: id,
        })),
      })
    );
    expect(g.hasWorkflowContext).toBe(false);
    expect(g.hasSystemContext).toBe(true);
    expect(g.missingWorkflow).toHaveLength(4);
  });
});

describe("preparationTips", () => {
  it("emits one deterministic tip per recorded source, in Build Loop order", () => {
    const tips = preparationTips(summary());
    expect(tips).toEqual([
      "Be ready to explain why you asked AI for this implementation.",
      "Be ready to explain how you checked behavior.",
    ]);
  });

  it("falls back to the anchor-and-phase line when nothing is recorded", () => {
    const tips = preparationTips(
      summary({
        included_sources: summary().included_sources.filter(
          (s) => !s.source_id.startsWith("workflow.")
        ),
      })
    );
    expect(tips).toEqual([SPARSE_PREPARATION_TIP]);
  });

  it("never leaks internal source ids into display text", () => {
    for (const tip of preparationTips(summary())) {
      expect(tip).not.toContain("workflow.");
      expect(tip).not.toContain("_");
    }
  });
});

describe("missingNote", () => {
  it("is null when nothing is missing", () => {
    expect(missingNote([])).toBeNull();
  });

  it("phrases a single missing source as optional, never as failure", () => {
    const note = missingNote([{ source_id: "workflow.evidence", label: "Evidence" }]);
    expect(note).toBe("Evidence not added yet — optional, you can still continue.");
    expect(note).not.toMatch(/incomplete|failed|not ready/i);
  });

  it("joins several labels readably without internal ids", () => {
    const note = missingNote([
      { source_id: "workflow.review_board", label: "Review Notes" },
      { source_id: "workflow.evidence", label: "Evidence" },
      { source_id: "workflow.verification", label: "Verification" },
    ]);
    expect(note).toBe(
      "Review Notes, Evidence and Verification not added yet — optional, you can still continue."
    );
    expect(note).not.toContain("workflow.");
  });
});

describe("WORKFLOW_PAGE_LINKS", () => {
  it("covers every workflow source with an app route", () => {
    for (const id of WORKFLOW_SOURCE_ORDER) {
      expect(WORKFLOW_PAGE_LINKS[id]).toMatch(/^\/app\/phase\//);
    }
  });
});
