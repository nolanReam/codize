import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/intake/page.tsx"), "utf8");
const apiSource = readFileSync(resolve(process.cwd(), "lib/api.ts"), "utf8");

describe("M18A project classification truth", () => {
  it("renders the server-owned plain classification label", () => {
    expect(source).toContain("setArchetypeName(done.archetype_name)");
    expect(source).toContain("setArchetypeName(s.archetype_name)");
    expect(source).toContain("Your project classified as: ${archetypeName}.");
    expect(source).toContain("Browser App");
  });

  it("separates project capability answers from student experience", () => {
    expect(source).toContain("Your project answers tell Codize what you&rsquo;re building");
    expect(source).toContain("Your experience answer only adjusts how concepts are explained");
    expect(source).toContain("it never");
    expect(source).toContain("turns your project into an AI-powered app");
  });

  it("keeps intake writes on the authenticated backend contract", () => {
    expect(apiSource).toContain(
      'request<IntakeStatus>("/intake/answers", { method: "POST", body: { question, answer } })'
    );
    expect(apiSource).toContain(
      'request<IntakeCompleteResult>("/intake/complete", { method: "POST" })'
    );
    expect(apiSource).toContain("Authorization: `Bearer ${token}`");
  });
});
