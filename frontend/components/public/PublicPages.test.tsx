// @vitest-environment happy-dom

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import HowItWorksPage from "../../app/how-it-works/page";
import WhyCodizePage from "../../app/why-codize/page";

vi.mock("next/link", () => ({
  default: ({ prefetch: _prefetch, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { prefetch?: boolean }) => <a {...props} />,
}));

function render(page: React.ReactElement) {
  document.body.innerHTML = renderToStaticMarkup(page);
  return document.body;
}

describe("public document pages", () => {
  it("renders Why Codize with bounded, qualified evidence", () => {
    const page = render(<WhyCodizePage />);
    expect(page.querySelectorAll("h1")).toHaveLength(1);
    expect(page.querySelector("h1")?.textContent).toContain("AI changed how we code");
    expect(page.textContent).toContain("55%");
    expect(page.textContent).toContain("66%");
    expect(page.textContent).not.toMatch(/cannot understand their code|Codize.*learning gains|guaranteed/i);
    expect(page.querySelectorAll("details")).toHaveLength(2);
    expect(page.querySelector('a[href="https://survey.stackoverflow.co/2025/ai"]')).not.toBeNull();
    expect(page.querySelector('a[href^="https://github.blog/"]')).not.toBeNull();
  });

  it("renders the implemented manual workflow and its boundaries", () => {
    const page = render(<HowItWorksPage />);
    expect(page.querySelectorAll("h1")).toHaveLength(1);
    for (const step of ["PLAN", "PROMPT", "BUILD", "CHECK", "UNDERSTAND"]) {
      expect(page.textContent).toContain(step);
    }
    expect(page.textContent).toContain("static, fictional walkthrough");
    expect(page.textContent).toContain("Codize does not automatically write code or inspect your repository.");
    expect(page.textContent).toContain("Codize does not execute tests or verify that the behavior works.");
    expect(page.textContent).toContain("Save its finding as a suggestion, not a verified root cause.");
    expect(page.textContent).toContain("without claiming grades, mastery, or guaranteed outcomes");
    expect(page.textContent).not.toMatch(/certified correct|guarantees mastery/i);
  });

  it("provides semantic navigation with no unimplemented legal routes", () => {
    const page = render(<WhyCodizePage />);
    expect(page.querySelector('a[href="#main-content"]')).not.toBeNull();
    expect(page.querySelector('nav[aria-label="Public pages"] a[aria-current="page"]')?.getAttribute("href")).toBe("/why-codize");
    expect(page.querySelector('a[href="mailto:codizeapp@gmail.com"]')).not.toBeNull();
    for (const route of ["/privacy", "/terms", "/accessibility"]) {
      expect(page.querySelector(`a[href="${route}"]`)).toBeNull();
    }
  });
});
