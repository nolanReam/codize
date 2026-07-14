import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import DefenseContextSummary from "./DefenseContextSummary";
import type { DefenseContextSummary as Summary } from "@/lib/types";

const summary: Summary = {
  schema_version: "1.0",
  phase_number: 3,
  included_sources: [],
  missing_sources: [],
  workflow_sources: [
    { source_id: "change_map", label: "Change Map", state: "current", truncated: false },
    { source_id: "review", label: "Review", state: "missing", truncated: false },
    { source_id: "verification", label: "Verification", state: "incomplete", truncated: false },
    { source_id: "evidence", label: "Evidence", state: "stale", truncated: true },
  ],
  has_truncation: true,
  artifact_aware: true,
};

describe("DefenseContextSummary", () => {
  it("keeps hierarchy stable while loading and announces status", () => {
    const html = renderToStaticMarkup(
      <DefenseContextSummary summary={null} state="loading" onRetry={vi.fn()} />
    );
    expect(html).toContain("Project record for this Defense");
    expect(html).toContain("Checking your project record");
    expect(html).toContain('role="status"');
  });

  it("renders exact source labels, honest states, and truncation without raw ids", () => {
    const html = renderToStaticMarkup(
      <DefenseContextSummary summary={summary} state="ready" onRetry={vi.fn()} />
    );
    for (const text of [
      "Change Map",
      "Review",
      "Verification",
      "Evidence",
      "Current",
      "Not available",
      "Incomplete",
      "Needs updating",
      "Long details shortened",
    ]) {
      expect(html).toContain(text);
    }
    expect(html).not.toContain("change_map");
    expect(html).not.toContain("source_id");
    expect(html).not.toMatch(/binding|fingerprint|score|threshold|expected concept/i);
  });

  it("shows a safe retryable request failure without calling records missing", () => {
    const html = renderToStaticMarkup(
      <DefenseContextSummary summary={null} state="error" onRetry={vi.fn()} />
    );
    expect(html).toContain("temporarily unavailable");
    expect(html).toContain("Retry project record");
    expect(html).toContain("has not been changed");
    expect(html).not.toContain("No saved record");
    expect(html).toContain('role="alert"');
  });
});
