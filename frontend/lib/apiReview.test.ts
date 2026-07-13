import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./supabase", () => ({ getAccessToken: vi.fn(async () => "test-token") }));

import { initializeReviewFromChangeMap } from "./api";

const responseBody = {
  phase: 2,
  section: "review_board",
  artifact: {
    files_changed: [],
    source_change_map_confirmed_at: "2026-07-13T11:00:00Z",
    source_change_map_generated_at: "2026-07-13T10:00:00Z",
    initialized_from_change_map: true,
    stale: false,
    review_targets: [],
    saved_at: "2026-07-13T12:00:00Z",
  },
};

describe("linked Review API initialization", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://codize.test";
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(responseBody), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("uses the reviewed route and sends no destructive body for normal initialization", async () => {
    await initializeReviewFromChangeMap(2);
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://codize.test/workflow/2/review/from-change-map");
    expect(init).toMatchObject({ method: "POST" });
    expect(init?.body).toBeUndefined();
  });

  it("sends replace_existing=true only for deliberate replacement", async () => {
    await initializeReviewFromChangeMap(2, true);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(JSON.parse(String(init?.body))).toEqual({ replace_existing: true });
  });
});
