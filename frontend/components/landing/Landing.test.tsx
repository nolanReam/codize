// @vitest-environment happy-dom

import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import LandingPage from "../../app/page";
import LandingCharacter from "./LandingCharacter";

vi.mock("next/link", () => ({ default: ({ prefetch: _prefetch, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { prefetch?: boolean }) => <a {...props} /> }));
vi.mock("next/image", () => ({ default: ({ priority: _priority, unoptimized: _unoptimized, ...props }: React.ImgHTMLAttributes<HTMLImageElement> & { priority?: boolean; unoptimized?: boolean }) => React.createElement("img", props) }));
vi.mock("../v2/V2Character", () => ({ default: () => <span data-animated-character /> }));

afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function renderPage() {
  document.body.innerHTML = renderToStaticMarkup(<LandingPage />);
  return document.body;
}

describe("Scope the Storm public contract", () => {
  it("server-renders the complete narrative in semantic order without needing motion", () => {
    const page = renderPage();
    expect(page.querySelectorAll("h1")).toHaveLength(1);
    expect(page.querySelector("h1")?.textContent).toBe("BUILD WITH AI. STAY IN CONTROL.");
    expect(Array.from(page.querySelectorAll("[data-storm-act]"), element => element.getAttribute("data-storm-act"))).toEqual(["thesis", "speed", "gap", "silence", "scope", "proof"]);
    for (const section of page.querySelectorAll("section")) {
      expect(page.querySelector(`#${section.getAttribute("aria-labelledby")}`)).not.toBeNull();
    }
    const scope = page.querySelector("#scope")!;
    expect(scope.textContent).toContain("Add a player’s nameand jersey number.");
    expect(Array.from(scope.querySelectorAll("li"), item => item.firstElementChild?.textContent)).toEqual(["PLAN", "PROMPT", "BUILD", "CHECK", "UNDERSTAND"]);
    expect(page.querySelector("[data-motion]")).toBeNull();
    expect(page.textContent).not.toMatch(/80%|Project Defense|PASS\/FAIL|commit history|eight.stage|gate-controlled/i);
  });

  it("preserves real auth destinations and an accessible shortcut to product proof", () => {
    const page = renderPage();
    const authLinks = Array.from(page.querySelectorAll("a")).filter(link => /Start one change|Sign in/.test(link.textContent ?? ""));
    expect(authLinks).toHaveLength(4);
    expect(authLinks.every(link => link.getAttribute("href") === "/login")).toBe(true);
    expect(page.querySelector('a[href="#product-proof"]')).not.toBeNull();
    expect(page.querySelector("#product-proof")?.getAttribute("tabindex")).toBe("-1");
  });

  it("keeps decoration hidden from assistive technology and content outside Canvas", () => {
    const page = renderPage();
    expect(page.querySelectorAll("canvas")).toHaveLength(3);
    for (const canvas of page.querySelectorAll("canvas")) {
      expect(canvas.getAttribute("aria-hidden")).toBe("true");
      expect(canvas.parentElement?.getAttribute("aria-hidden")).toBe("true");
      expect(canvas.parentElement?.querySelector("pre")?.textContent?.length).toBeGreaterThan(100);
    }
    expect(page.querySelectorAll('[aria-live], [role="status"]')).toHaveLength(0);
    expect(page.querySelector("#scope")?.querySelector("h3")?.closest('[aria-hidden="true"]')).toBeNull();
  });

  it("labels the static specimen and renders only a lazy canonical character frame after resolution", () => {
    const page = renderPage();
    const proof = page.querySelector("#product-proof")!;
    expect(proof.querySelector("figcaption")?.textContent).toContain("static preview");
    expect(proof.querySelectorAll("button, input, textarea")).toHaveLength(0);
    expect(proof.textContent).toContain("AN EXAMPLE ANSWER");
    expect(page.querySelectorAll("img")).toHaveLength(1);
    expect(proof.querySelector("img")?.getAttribute("src")).toContain("codybara_idle_01.png");
    expect(proof.querySelector("img")?.getAttribute("loading")).toBe("lazy");
    expect(page.querySelector('link[rel="preload"][as="image"]')).toBeNull();
  });
});

describe("landing character activation", () => {
  it("mounts the existing animation only in view and stops it when hidden, offscreen, or unmounted", () => {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    let callback: IntersectionObserverCallback;
    const disconnect = vi.fn();
    vi.stubGlobal("IntersectionObserver", class {
      constructor(fn: IntersectionObserverCallback) { callback = fn; }
      observe() {}
      disconnect = disconnect;
    });
    let hidden = false;
    vi.spyOn(document, "hidden", "get").mockImplementation(() => hidden);
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    act(() => root.render(<LandingCharacter />));
    expect(container.querySelector("[data-animated-character]")).toBeNull();
    const intersect = (value: boolean) => callback([{ isIntersecting: value } as IntersectionObserverEntry], {} as IntersectionObserver);
    act(() => intersect(true));
    expect(container.querySelector("[data-animated-character]")).not.toBeNull();
    act(() => { hidden = true; document.dispatchEvent(new Event("visibilitychange")); });
    expect(container.querySelector("[data-animated-character]")).toBeNull();
    act(() => { hidden = false; document.dispatchEvent(new Event("visibilitychange")); });
    expect(container.querySelector("[data-animated-character]")).not.toBeNull();
    act(() => intersect(false));
    expect(container.querySelector("[data-animated-character]")).toBeNull();
    act(() => root.unmount());
    expect(disconnect).toHaveBeenCalledOnce();
    act(() => intersect(true));
    expect(container.childElementCount).toBe(0);
  });
});
