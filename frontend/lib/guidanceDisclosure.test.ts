import { describe, expect, it } from "vitest";

import {
  guidanceStorageKey,
  readGuidanceOpen,
  writeGuidanceOpen,
} from "./guidanceDisclosure";

class MemoryStorage implements Storage {
  private data = new Map<string, string>();
  get length() { return this.data.size; }
  clear() { this.data.clear(); }
  getItem(key: string) { return this.data.get(key) ?? null; }
  key(index: number) { return Array.from(this.data.keys())[index] ?? null; }
  removeItem(key: string) { this.data.delete(key); }
  setItem(key: string, value: string) { this.data.set(key, value); }
}

describe("guidance disclosure preference", () => {
  it("scopes only a boolean by user, active project, and workflow stage", () => {
    const key = guidanceStorageKey("user-1", "verification");
    expect(key).toBe("codize:guide:user-1:active-project:verification");
    expect(key).not.toMatch(/prompt|evidence|report content/i);
  });

  it("round-trips open and closed without storing project content", () => {
    const storage = new MemoryStorage();
    const key = guidanceStorageKey("user-1", "prompt");
    writeGuidanceOpen(storage, key, true);
    expect(storage.getItem(key)).toBe("1");
    expect(readGuidanceOpen(storage, key)).toBe(true);
    writeGuidanceOpen(storage, key, false);
    expect(readGuidanceOpen(storage, key)).toBe(false);
  });

  it("fails safely when storage is unavailable", () => {
    const broken = {
      getItem: () => { throw new Error("blocked"); },
      setItem: () => { throw new Error("blocked"); },
    } as unknown as Storage;
    expect(readGuidanceOpen(broken, "key")).toBeNull();
    expect(() => writeGuidanceOpen(broken, "key", true)).not.toThrow();
  });
});
