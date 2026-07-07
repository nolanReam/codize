import { describe, expect, it } from "vitest";

import { clearDraft, containsSecretMarker, draftKey, readDraft, writeDraft } from "./drafts";

function fakeStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    map,
  };
}

describe("draftKey", () => {
  it("scopes by user id and surface so drafts never cross accounts or phases", () => {
    const a = draftKey("user-a", "review_board:2");
    const b = draftKey("user-b", "review_board:2");
    const c = draftKey("user-a", "review_board:3");
    expect(a).not.toBe(b);
    expect(a).not.toBe(c);
    expect(a).toBe("codize:draft:user-a:review_board:2");
  });
});

describe("write/read/clear round-trip", () => {
  it("round-trips a structured draft", () => {
    const s = fakeStorage();
    const key = draftKey("u", "prompt_builder:1");
    expect(writeDraft(s, key, { aiTask: "propose a schema", planFirst: true })).toBe(true);
    expect(readDraft(s, key)).toEqual({ aiTask: "propose a schema", planFirst: true });
    clearDraft(s, key);
    expect(readDraft(s, key)).toBeNull();
  });

  it("returns null for corrupt JSON instead of throwing", () => {
    const s = fakeStorage();
    s.map.set("k", "{not json");
    expect(readDraft(s, "k")).toBeNull();
  });

  it("returns null when nothing is stored", () => {
    expect(readDraft(fakeStorage(), "missing")).toBeNull();
  });
});

describe("secret-content guard (mirrors backend markers)", () => {
  it.each(["sb_secret_abc123", "sk-or-v1-xyz", "AIzaSyExample", "-----BEGIN PRIVATE KEY-----"])(
    "refuses to persist a draft containing %s",
    (secret) => {
      const s = fakeStorage();
      expect(writeDraft(s, "k", { note: `my key is ${secret}` })).toBe(false);
      expect(s.map.size).toBe(0);
    }
  );

  it("persists ordinary technical text", () => {
    const s = fakeStorage();
    expect(writeDraft(s, "k", { note: "curl POST /tasks returned 422" })).toBe(true);
  });

  it("flags markers anywhere in nested content", () => {
    expect(containsSecretMarker(JSON.stringify({ deep: { list: ["ok", "sb_secret_x"] } }))).toBe(
      true
    );
    expect(containsSecretMarker("plain text")).toBe(false);
  });
});
