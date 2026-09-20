import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const login = readFileSync(resolve(process.cwd(), "app/login/page.tsx"), "utf8");
const layout = readFileSync(resolve(process.cwd(), "app/app/layout.tsx"), "utf8");

describe("post-auth V2 routing contract", () => {
  it("lands password login and session-bearing signup on the V2 project list", () => {
    expect(login).toContain("POST_AUTH_DESTINATION");
    expect(login).toContain("router.replace(POST_AUTH_DESTINATION)");
    expect(login).not.toContain('router.replace("/app")');
  });

  it("finishes confirmation callbacks and existing sessions at the same destination", () => {
    expect(login).toContain("supabase.auth.getSession()");
    expect(login).toContain("supabase.auth.onAuthStateChange");
    expect(login).toContain("if (active && session) router.replace(POST_AUTH_DESTINATION)");
  });

  it("preserves protected-route and logout/login behavior", () => {
    expect(layout).toContain('router.replace("/login")');
    expect(layout).toContain("await getSupabase().auth.signOut()");
    expect(layout).toContain("sessionStorage.removeItem(RECONNECT_FLAG)");
  });

  it("reserves signup-adjacent help without claiming legal acceptance", () => {
    expect(login).toContain("Questions about the upcoming pilot?");
    expect(login).toContain("mailto:codizeapp@gmail.com");
    expect(login).not.toMatch(/agree to (?:the )?terms|accept(?:ed|ance)?_?version|legal acceptance/i);
    expect(login).not.toContain('href="/terms"');
    expect(login).not.toContain('href="/privacy"');
  });
});
