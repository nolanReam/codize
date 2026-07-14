import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./supabase", () => ({ getAccessToken: vi.fn(async () => "test-token") }));

import { getDefenseContextSummary, getDefenseReport, startGate } from "./api";

describe("artifact-aware Defense and Report API integration", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://codize.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string | URL | Request) => {
        const path = String(url);
        const body = path.endsWith("/gate/context-summary")
          ? {
              schema_version: "1.0",
              phase_number: 2,
              included_sources: [],
              missing_sources: [],
              workflow_sources: [
                { source_id: "change_map", label: "Change Map", state: "current", truncated: false },
              ],
              has_truncation: false,
              artifact_aware: true,
            }
          : path.endsWith("/gate/start")
            ? { gate_session_id: "gate-1", phase: 2, phase_title: "Data", anchor_prompt: "Name one thing." }
            : {
                schema_version: "1.0",
                phase_number: 2,
                phase_title: "Data",
                workflow_context_source: "defense_attempt",
                workflow_context: {},
                defense: { state: "passed", turns: [], evaluator_outcome: "PASS", evaluator_reason: null },
                truth_notice: "Student-safe truth notice.",
              };
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads the exact metadata-only context summary with GET and no body", async () => {
    const summary = await getDefenseContextSummary();
    expect(summary.workflow_sources[0]).toEqual({
      source_id: "change_map",
      label: "Change Map",
      state: "current",
      truncated: false,
    });
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://codize.test/gate/context-summary");
    expect(init).toMatchObject({ method: "GET" });
    expect(init?.body).toBeUndefined();
  });

  it("loads the authoritative phase Report with GET and no browser-supplied context", async () => {
    const report = await getDefenseReport(2);
    expect(report.workflow_context_source).toBe("defense_attempt");
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://codize.test/report/2");
    expect(init).toMatchObject({ method: "GET" });
    expect(init?.body).toBeUndefined();
  });

  it("preserves the existing start request with no snapshot or workflow authority", async () => {
    await startGate();
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://codize.test/gate/start");
    expect(init).toMatchObject({ method: "POST" });
    expect(init?.body).toBeUndefined();
  });
});
