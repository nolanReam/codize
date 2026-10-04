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

  it("keeps research takeaways prominent and methodology in closed native disclosures", () => {
    const page = render(<WhyCodizePage />);
    const disclosures = Array.from(page.querySelectorAll("details"));
    expect(disclosures.every(details => !details.hasAttribute("open"))).toBe(true);
    expect(disclosures.map(details => details.querySelector("summary")?.textContent)).toEqual(["Where this comes from", "Where this comes from"]);
    const cards = disclosures.map(details => details.closest("article")!);
    expect(cards.map(card => card.querySelector("strong")?.parentElement?.textContent)).toEqual(["55%faster", "66%of surveyed devs"]);
    expect(cards.map(card => card.querySelector("h3")?.textContent)).toEqual(["With Copilot on one coding task.", 'Frustrated by AI\'s "almost right" answers.']);
    expect(disclosures[0].textContent).toContain("95 professional developers");
    expect(disclosures[0].textContent).toContain("1 hour 11 minutes");
    expect(disclosures[0].textContent).toContain("long-term productivity, learning, code quality, or maintainability");
    expect(disclosures[1].textContent).toContain("31,476 respondents");
    expect(disclosures[1].textContent).toContain("Select all that apply");
    expect(disclosures[1].textContent).toContain("not a measured rate of incorrect AI outputs");
  });

  it("renders the implemented manual workflow and its boundaries", () => {
    const page = render(<HowItWorksPage />);
    expect(page.querySelectorAll("h1")).toHaveLength(1);
    for (const step of ["PLAN", "PROMPT", "BUILD", "CHECK", "UNDERSTAND"]) {
      expect(page.textContent).toContain(step);
    }
    expect(page.textContent).toContain("fictional Volleyball Tracker example");
    expect(page.textContent).toContain("You copy the prompt into your coding AI and bring the result back.");
    expect(page.textContent).toContain("Codize does not automatically write code or inspect your repository.");
    expect(page.textContent).toContain("Codize does not execute tests or verify that the behavior works.");
    expect(page.textContent).toContain("Codize does not currently connect to GitHub.");
    expect(page.textContent).toContain("Save what it found as a suggestion, not a proven cause.");
    expect(page.textContent).toContain("not grades, proof of mastery, or guaranteed results");
    expect(page.textContent).not.toMatch(/certified correct|guarantees mastery/i);
  });

  it.each([
    ["/why-codize", <WhyCodizePage key="why" />],
    ["/how-it-works", <HowItWorksPage key="how" />],
  ])("provides centered-shell navigation and the active route for %s", (route, element) => {
    const page = render(element as React.ReactElement);
    expect(page.querySelector('a[href="#main-content"]')).not.toBeNull();
    expect(page.querySelector("#main-content")?.getAttribute("tabindex")).toBe("-1");
    const nav = page.querySelector('header nav[aria-label="Public pages"]')!;
    expect(Array.from(nav.querySelectorAll("a"), link => link.getAttribute("href"))).toEqual(["/why-codize", "/how-it-works"]);
    expect(nav.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
    expect(nav.querySelector('[aria-current="page"]')?.getAttribute("href")).toBe(route);
    expect(page.querySelector('header > a[href="/login"]')).not.toBeNull();
    expect(page.querySelector("footer > p")?.textContent).toBe("One project. One feature. One useful habit.");
    expect(page.querySelector('a[href="mailto:codizeapp@gmail.com"]')).not.toBeNull();
    for (const route of ["/privacy", "/terms", "/accessibility"]) {
      expect(page.querySelector(`a[href="${route}"]`)).toBeNull();
    }
  });
});
