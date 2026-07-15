import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");

function luminance(hex: string): number {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)!
    .map((channel) => Number.parseInt(channel, 16) / 255)
    .map((channel) =>
      channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
    );
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(foreground: string, background: string): number {
  const lighter = Math.max(luminance(foreground), luminance(background));
  const darker = Math.min(luminance(foreground), luminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

function token(name: string): string {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6})`, "i"));
  if (!match) throw new Error(`Missing CSS token --${name}`);
  return match[1];
}

describe("M16C.2 text contrast contract", () => {
  it("uses the readable secondary token for milestone-specific supporting text", () => {
    expect(css).toMatch(/\.defense-page-body \.muted,[\s\S]*?color: var\(--ink-2\)/);
    expect(css).toMatch(/\.defense-page-body \.defense-context-summary h3 \{ color: var\(--ink\)/);
    expect(css).toMatch(/\.report-kicker \{ color: var\(--ink-2\)/);
    expect(css).toMatch(/\.report-detail dt \{ color: var\(--ink-2\)/);
    expect(css).toMatch(/\.report-empty-source \{ color: var\(--ink-2\)/);
    expect(css).toMatch(/\.field-limit \{ color: var\(--ink-2\)/);
  });

  it("keeps secondary text above WCAG AA contrast on Codize surfaces", () => {
    expect(contrast(token("ink-2"), token("surface"))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token("ink-2"), token("bg"))).toBeGreaterThanOrEqual(4.5);
  });
});
