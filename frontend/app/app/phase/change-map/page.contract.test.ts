import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(process.cwd(), "app/app/phase/change-map/page.tsx"), "utf8");

describe("Change Map M18A recovery contract", () => {
  it("announces an exact correction, preserves retry, and offers explicit manual authorship", () => {
    expect(source).toContain('role="alert"');
    expect(source).toContain("CHANGE_MAP_GENERATION_CORRECTION");
    expect(source).toContain("Try again");
    expect(source).toContain("Create a Change Map manually");
    expect(source).toContain("createManualChangeMap");
  });

  it("moves focus to failure and never starts manual recovery in an effect", () => {
    expect(source).toContain("alertRef.current?.focus()");
    expect(source).toContain("onClick={onManual}");
    expect(source).not.toMatch(/useEffect\([^)]*createManualChangeMap/);
  });
});
