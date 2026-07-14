import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./supabase", () => ({ getAccessToken: vi.fn(async () => "test-token") }));

import { initializeVerificationFromReview } from "./api";

const responseBody = {
  phase: 2,
  section: "verification",
  artifact: {
    checks: [],
    initialized_at: "2026-07-13T12:01:00Z",
    source_review_binding: {
      source_change_map_generated_at: "2026-07-13T10:00:00Z",
      source_change_map_confirmed_at: "2026-07-13T11:00:00Z",
      review_saved_at: "2026-07-13T12:00:00Z",
      review_target_fingerprint: "a".repeat(64),
    },
    verification_targets: [],
    initialized_from_review: true,
    stale: false,
    saved_at: "2026-07-13T12:01:00Z",
  },
};

describe("linked Verification API initialization", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://codize.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(responseBody), {
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

  it("uses the reviewed route and sends no destructive body for normal initialization", async () => {
    await initializeVerificationFromReview(2);
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://codize.test/workflow/2/verification/from-review");
    expect(init).toMatchObject({ method: "POST" });
    expect(init?.body).toBeUndefined();
  });

  it("sends replace_existing=true only for deliberate replacement", async () => {
    await initializeVerificationFromReview(2, true);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(JSON.parse(String(init?.body))).toEqual({ replace_existing: true });
  });
});
