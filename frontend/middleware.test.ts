import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";
import { isLegacyAppPath, isV2AppPath } from "./lib/app-routes";

const legacy = ["/app", "/app/intake", "/app/phase", "/app/phase/prompt", "/app/phase/import",
  "/app/phase/change-map", "/app/phase/review", "/app/phase/verify", "/app/phase/evidence", "/app/gate", "/app/report"];
const retained = ["/", "/why-codize", "/how-it-works", "/login", "/character", "/settings",
  "/app/projects", "/app/project/id", "/app/project/id/plan", "/app/project/id/build",
  "/app/project/id/learning", "/app/project/id/history", "/app/character", "/app/settings"];

function modeFetch(mode: unknown) {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example/");
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(mode)));
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe("server-authoritative legacy frontend boundary", () => {
  it.each(legacy)("redirects %s and discards client overrides in pilot mode", async path => {
    const fetcher = modeFetch({ pilot_v2_only: true });
    const request = new NextRequest(`https://codize.example${path}?pilot_v2_only=false`, {
      headers: { "X-Pilot-V2-Only": "false", Cookie: "pilot_v2_only=false" },
    });
    const response = await middleware(request);
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://codize.example/app/projects");
    expect(fetcher).toHaveBeenCalledWith("https://api.example/deployment-mode", {
      cache: "no-store", signal: expect.any(AbortSignal),
    });
  });
  it.each(legacy)("preserves %s in ordinary mode", async path => {
    modeFetch({ pilot_v2_only: false });
    expect((await middleware(new NextRequest(`https://codize.example${path}`))).headers.get("x-middleware-next")).toBe("1");
  });
  it.each(retained)("keeps %s accessible without a mode lookup", async path => {
    const fetcher = modeFetch({ pilot_v2_only: true });
    expect((await middleware(new NextRequest(`https://codize.example${path}`))).headers.get("x-middleware-next")).toBe("1");
    expect(fetcher).not.toHaveBeenCalled();
  });
  it.each([{}, null, { pilot_v2_only: "false" }])("fails closed for malformed mode %j", async mode => {
    modeFetch(mode);
    expect((await middleware(new NextRequest("https://codize.example/app"))).status).toBe(503);
  });
  it("fails closed on missing origin, HTTP errors, and network failures", async () => {
    const fetcher = modeFetch({ pilot_v2_only: false });
    fetcher.mockResolvedValueOnce(new Response("unavailable", { status: 503 }));
    expect((await middleware(new NextRequest("https://codize.example/app"))).status).toBe(503);
    fetcher.mockRejectedValueOnce(new Error("network failure"));
    const response = await middleware(new NextRequest("https://codize.example/app"));
    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("no-store");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    expect((await middleware(new NextRequest("https://codize.example/app"))).status).toBe(503);
  });
  it("matches legacy segment boundaries and trailing slashes", () => {
    for (const path of legacy) expect(isLegacyAppPath(`${path}/`)).toBe(true);
    for (const path of ["/app/projects", "/app/phases", "/app/reporting", "/application"]) expect(isLegacyAppPath(path)).toBe(false);
    for (const path of retained.filter(path => path.startsWith("/app/"))) expect(isV2AppPath(path)).toBe(true);
  });
});
