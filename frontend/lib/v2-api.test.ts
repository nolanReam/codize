import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./supabase", () => ({ getAccessToken: vi.fn(async () => "test-token") }));

import {
  createStudentCheckPlan,
  getBuildState,
  getProjectRefs,
  handoffPrompt,
  requestTeachingHelp,
  respondToTeaching,
  selectCodingAgent,
  selectEffort,
} from "./v2-api";

describe("V2 frontend API contract", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://codize.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ projects: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads the owner-scoped project reference envelope", async () => {
    await getProjectRefs();
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://codize.test/v2/project-refs");
    expect(init?.headers).toMatchObject({ Authorization: "Bearer test-token" });
  });

  it("uses explicit project and current-change IDs for build resume", async () => {
    await getBuildState("project-1", "change-2");
    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(
      "http://codize.test/v2/projects/project-1/current-change/change-2/build-state"
    );
  });

  it("sends optimistic versions when choosing a coding agent", async () => {
    await selectCodingAgent("project-1", "change-2", "codex", 7, 11);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.method).toBe("PUT");
    expect(JSON.parse(String(init?.body))).toEqual({
      workflow_version: "v2",
      expected_project_version: 7,
      expected_current_change_version: 11,
      choice: "codex",
    });
  });

  it("hands off one accepted prompt version with optimistic versions", async () => {
    await handoffPrompt("project-1", "change-2", "prompt-3", 11, 4);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe(
      "http://codize.test/v2/projects/project-1/current-change/change-2/handoff"
    );
    expect(JSON.parse(String(init?.body))).toMatchObject({
      workflow_version: "v2",
      prompt_version_id: "prompt-3",
      expected_current_change_version: 11,
      expected_prompt_version: 4,
    });
  });

  it("uses backend commands for teaching, effort, and student Check planning", async () => {
    await requestTeachingHelp("project-1", "change-2", 4, "verification", "help-command");
    await selectEffort("project-1", "change-2", "standard", 5, "effort-command");
    await respondToTeaching(
      "project-1", "change-2", 6, "prebuild", "Keep scoring unchanged", "answer-command"
    );
    await createStudentCheckPlan(
      "project-1", "change-2", 7, "Try the visible result", "check-command", "check-id"
    );

    const calls = vi.mocked(fetch).mock.calls;
    expect(calls[0][0]).toBe("http://codize.test/v2/projects/project-1/current-change/change-2/teaching/help");
    expect(calls[0][1]?.method).toBe("POST");
    expect(calls[1][0]).toBe("http://codize.test/v2/projects/project-1/current-change/change-2/effort-attempts");
    expect(calls[1][1]?.method).toBe("POST");
    expect(JSON.parse(String(calls[0][1]?.body))).toMatchObject({ command_id: "help-command" });
    expect(JSON.parse(String(calls[1][1]?.body))).toMatchObject({ command_id: "effort-command" });
    expect(JSON.parse(String(calls[2][1]?.body))).toMatchObject({ command_id: "answer-command" });
    expect(calls[3][0]).toBe("http://codize.test/v2/projects/project-1/current-change/change-2/checks");
    expect(calls[3][1]?.method).toBe("POST");
    expect(JSON.parse(String(calls[3][1]?.body))).toMatchObject({
      workflow_version: "v2",
      command_id: "check-command",
      check_id: "check-id",
      expected_current_change_version: 7,
      check_plan: "Try the visible result",
    });
  });
});
