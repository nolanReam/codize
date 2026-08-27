import { describe, expect, it } from "vitest";

import { resolveLoadedBuildStatus } from "./v2-build-view";

describe("V2 Build loaded state", () => {
  it("distinguishes active, completed-refresh, and empty outcomes", () => {
    expect(resolveLoadedBuildStatus(true, false)).toBe("active");
    expect(resolveLoadedBuildStatus(false, true)).toBe("completed");
    expect(resolveLoadedBuildStatus(false, false)).toBe("empty");
  });
});
