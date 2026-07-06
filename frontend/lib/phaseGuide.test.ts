import { describe, expect, it } from "vitest";

import { phaseGuide } from "./phaseGuide";

// Every phase title from the three fixed archetype templates. The guide map
// must cover all of them without falling back to the generic entry.
const ALL_TEMPLATE_TITLES = [
  // Archetype 1 — AI-Powered App
  "Architecture & Scope",
  "Backend Foundation",
  "LLM Integration",
  "Frontend & Conversation UI",
  "Auth & User Accounts",
  "Persistence & Conversation History",
  "Pre-Deployment Security Checklist",
  // Archetype 2 — REST API Backend
  "API Design & Resource Modeling",
  "Server Foundation",
  "Database Schema & RLS",
  "Authentication & Authorization",
  "CRUD & Input Validation",
  "Error Handling, Testing & Documentation",
  // Archetype 3 — Full-Stack Web App
  "Architecture & Data Model",
  "Frontend Core",
  "Frontend–Backend Integration",
] as const;

const FALLBACK_MEANING = phaseGuide("Some Unrecognized Phase Title").meaning;

describe("phaseGuide", () => {
  it("returns a specific guide for every template phase title", () => {
    for (const title of ALL_TEMPLATE_TITLES) {
      const guide = phaseGuide(title);
      expect(guide.meaning.length, title).toBeGreaterThan(40);
      expect(guide.asks.length, title).toBeGreaterThanOrEqual(3);
      expect(guide.meaning, title).not.toBe(FALLBACK_MEANING);
    }
  });

  it("is case-insensitive", () => {
    expect(phaseGuide("DATABASE SCHEMA & RLS")).toEqual(phaseGuide("Database Schema & RLS"));
  });

  it("routes compound titles to the right guide", () => {
    // Integration wins over the generic frontend guide for the wiring phase…
    expect(phaseGuide("Frontend–Backend Integration").meaning).toContain("Wiring");
    // …but LLM Integration is its own thing, not generic integration.
    expect(phaseGuide("LLM Integration").meaning).toContain("backend");
    expect(phaseGuide("LLM Integration").meaning).toContain("API key");
    // Conversation history is persistence, not conversation UI.
    expect(phaseGuide("Persistence & Conversation History").meaning).toContain("Saving");
  });

  it("falls back to a usable generic guide for unknown titles", () => {
    const guide = phaseGuide("Totally Personalized Custom Phase");
    expect(guide.meaning.length).toBeGreaterThan(40);
    expect(guide.asks.length).toBeGreaterThanOrEqual(3);
  });

  it("never suggests jargon-only asks — every ask is a full sentence", () => {
    for (const title of ALL_TEMPLATE_TITLES) {
      for (const ask of phaseGuide(title).asks) {
        expect(ask.length, ask).toBeGreaterThan(20);
        expect(ask, ask).toMatch(/[.?]$/);
      }
    }
  });
});
