import { describe, expect, it } from "vitest";

import {
  AI_CHANGE_CHOICES,
  CODING_CONFIDENCE_CHOICES,
  ENTRY_SITUATIONS,
  nextEntryStep,
  normalizeEntryProfile,
  QUICK_START_STEPS,
  recommendationFor,
} from "./entryProfile";
import type { EntryProfile } from "./types";

function profile(overrides: Partial<EntryProfile> = {}): EntryProfile {
  return {
    schema_version: "1.0",
    current_situation: "starting_fresh",
    coding_confidence: "know_basics",
    ai_changed_files: null,
    completed: true,
    recommended_start: "prompt_builder",
    guidance_depth: "standard",
    recovery_emphasis: false,
    updated_at: "2026-07-15T00:00:00Z",
    ...overrides,
  };
}

describe("adaptive entry profile", () => {
  it("uses the exact three self-selected situation and confidence values", () => {
    expect(ENTRY_SITUATIONS.map((choice) => choice.value)).toEqual([
      "starting_fresh",
      "already_building",
      "stuck",
    ]);
    expect(CODING_CONFIDENCE_CHOICES.map((choice) => choice.value)).toEqual([
      "new_to_code",
      "know_basics",
      "comfortable",
    ]);
    expect(AI_CHANGE_CHOICES.map((choice) => choice.value)).toEqual([
      "yes",
      "not_yet",
      "unsure",
    ]);
  });

  it("uses one conditional question only for already-building students", () => {
    expect(nextEntryStep(profile({ completed: false, coding_confidence: null }))).toBe("confidence");
    expect(
      nextEntryStep(
        profile({
          current_situation: "already_building",
          ai_changed_files: null,
          completed: false,
          recommended_start: null,
        })
      )
    ).toBe("ai_changes");
    expect(nextEntryStep(profile({ current_situation: "stuck" }))).toBe("recommendation");
  });

  it("maps fresh, existing, unsure, and stuck profiles to one deterministic start", () => {
    expect(recommendationFor(profile())?.id).toBe("prompt_builder");
    expect(
      recommendationFor(
        profile({
          current_situation: "already_building",
          ai_changed_files: "yes",
          recommended_start: "implementation_import",
        })
      )?.id
    ).toBe("implementation_import");
    expect(
      recommendationFor(
        profile({
          current_situation: "already_building",
          ai_changed_files: "unsure",
          recommended_start: "implementation_import",
        })
      )?.reason
    ).toContain("what still needs inspection");
    expect(
      recommendationFor(
        profile({
          current_situation: "stuck",
          recommended_start: "quick_start",
          recovery_emphasis: true,
        })
      )?.href
    ).toBe("/app?quick-start=1");
  });

  it("defines the five Quick Start steps without a duplicate input", () => {
    expect(QUICK_START_STEPS).toHaveLength(5);
    expect(QUICK_START_STEPS[1]).toContain("Bring back");
    expect(QUICK_START_STEPS.join(" ")).not.toMatch(/paste|textarea|upload/i);
  });

  it("fails malformed optional history closed while allowing partial profiles", () => {
    expect(normalizeEntryProfile(null)).toBeNull();
    expect(normalizeEntryProfile({ ...profile(), recommended_start: "report" })).toBeNull();
    expect(normalizeEntryProfile({ ...profile(), guidance_depth: "expert" })).toBeNull();
    expect(
      normalizeEntryProfile(
        profile({
          current_situation: null,
          coding_confidence: "new_to_code",
          completed: false,
          recommended_start: null,
          guidance_depth: "more",
        })
      )
    ).not.toBeNull();
  });
});
