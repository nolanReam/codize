import { describe, expect, it } from "vitest";

import {
  DEFENSE_TRUNCATION_EXPLANATION,
  DEFENSE_WORKFLOW_SOURCE_ORDER,
  orderedWorkflowSources,
  sourcePillClass,
  sourceStatePresentation,
} from "./defenseContext";
import type { DefenseContextSummary, WorkflowArtifactState } from "./types";

function summary(overrides: Partial<DefenseContextSummary> = {}): DefenseContextSummary {
  return {
    schema_version: "1.0",
    phase_number: 2,
    included_sources: [],
    missing_sources: [],
    workflow_sources: [
      { source_id: "evidence", label: "Evidence", state: "stale", truncated: true },
      { source_id: "change_map", label: "Change Map", state: "current", truncated: false },
      { source_id: "verification", label: "Verification", state: "incomplete", truncated: false },
      { source_id: "review", label: "Review", state: "manual", truncated: false },
    ],
    has_truncation: true,
    artifact_aware: true,
    ...overrides,
  };
}

describe("Defense workflow-source presentation", () => {
  it("orders the exact four M16C.1 workflow sources", () => {
    expect(orderedWorkflowSources(summary()).map((source) => source.source_id)).toEqual(
      DEFENSE_WORKFLOW_SOURCE_ORDER
    );
  });

  it.each<[WorkflowArtifactState, string, string]>([
    ["current", "Current", "available as context"],
    ["missing", "Not available", "No saved record"],
    ["incomplete", "Incomplete", "not fully completed"],
    ["stale", "Needs updating", "upstream workflow step changed"],
    ["manual", "Manual record", "earlier manual workflow format"],
    ["malformed", "Unavailable", "could not safely use"],
  ])("maps %s honestly", (state, label, description) => {
    expect(sourceStatePresentation(state)).toMatchObject({ label });
    expect(sourceStatePresentation(state).description).toContain(description);
  });

  it("uses text labels plus restrained semantic tones", () => {
    expect(sourcePillClass("current")).toBe("ok");
    expect(sourcePillClass("stale")).toBe("warn");
    expect(sourcePillClass("malformed")).toBe("danger");
    expect(sourcePillClass("missing")).toBe("");
  });

  it("explains truncation without claiming the source record changed", () => {
    expect(DEFENSE_TRUNCATION_EXPLANATION).toContain("shortened");
    expect(DEFENSE_TRUNCATION_EXPLANATION).toContain("was not changed");
    expect(DEFENSE_TRUNCATION_EXPLANATION).not.toMatch(/token|character budget|provider/i);
  });
});
