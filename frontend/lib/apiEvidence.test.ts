import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./supabase", () => ({ getAccessToken: vi.fn(async () => "test-token") }));

import { getEvidenceHandoffPreview, initializeEvidenceFromVerification } from "./api";

const preview = {
  mode: "linked_verification",
  verification_state: "current",
  eligible_count: 1,
  targets: [],
  guidance: "Select performed results.",
};

describe("Verification to Evidence API integration", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://codize.test";
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(preview), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads the pure preview with GET and no request body", async () => {
    await getEvidenceHandoffPreview(3);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://codize.test/workflow/3/evidence/from-verification");
    expect(init).toMatchObject({ method: "GET" });
    expect(init?.body).toBeUndefined();
  });

  it("sends only exact selected target ids for explicit initialization", async () => {
    await initializeEvidenceFromVerification(3, ["vt-111111111111", "vt-222222222222"]);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init).toMatchObject({ method: "POST" });
    expect(JSON.parse(String(init?.body))).toEqual({
      selected_verification_target_ids: ["vt-111111111111", "vt-222222222222"],
    });
  });

  it("sends replace_existing only for deliberate rebuild", async () => {
    await initializeEvidenceFromVerification(3, ["vt-111111111111"], true);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(JSON.parse(String(init?.body))).toEqual({
      selected_verification_target_ids: ["vt-111111111111"],
      replace_existing: true,
    });
  });
});
