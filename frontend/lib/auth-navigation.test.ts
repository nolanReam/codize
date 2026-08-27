import { describe, expect, it } from "vitest";

import { POST_AUTH_DESTINATION } from "./auth-navigation";

describe("auth navigation", () => {
  it("uses the V2 Project list as the sole post-auth landing", () => {
    expect(POST_AUTH_DESTINATION).toBe("/app/projects");
  });
});
