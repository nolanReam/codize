import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import V2Character from "./V2Character";
import { CODYBARA_IDLE_FRAME_MS, CODYBARA_IDLE_FRAMES } from "../../lib/codybara";

describe("V2Character", () => {
  it("renders the canonical first frame immediately inside the approved footprint", () => {
    const markup = renderToStaticMarkup(<V2Character size="medium" />);

    expect(markup).toContain('data-character="codybara"');
    expect(markup).toContain("v2-character-medium");
    expect(markup.match(/<img/g)).toHaveLength(1);
    expect(markup).toContain("codybara_idle_01.png");
    expect(markup).not.toContain("codybara_idle_02.png");
    expect(markup).toContain('aria-hidden="true"');
  });

  it("uses the canonical frame order and 220ms timing", () => {
    expect(CODYBARA_IDLE_FRAME_MS).toBe(220);
    expect(CODYBARA_IDLE_FRAMES).toEqual([
      "/characters/codybara/animations/idle/codybara_idle_01.png",
      "/characters/codybara/animations/idle/codybara_idle_02.png",
      "/characters/codybara/animations/idle/codybara_idle_03.png",
      "/characters/codybara/animations/idle/codybara_idle_04.png",
      "/characters/codybara/animations/idle/codybara_idle_05.png",
      "/characters/codybara/animations/idle/codybara_idle_06.png",
      "/characters/codybara/animations/idle/codybara_idle_07.png",
    ]);
    expect(CODYBARA_IDLE_FRAME_MS * CODYBARA_IDLE_FRAMES.length).toBe(1540);
  });

  it("defers nonessential frames until motion is allowed and keeps them lazy", () => {
    const source = readFileSync(resolve(process.cwd(), "components/v2/V2Character.tsx"), "utf8");

    expect(source).toContain("CODYBARA_IDLE_FRAMES.slice(0, 1)");
    expect(source).toContain('loading={index === 0 ? "eager" : "lazy"}');
    expect(source).toContain('window.matchMedia("(prefers-reduced-motion: reduce)")');
  });
});
