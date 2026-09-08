// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from "vitest";
import { createFragments, createStormController, followVisual, cue, readingHolds } from "./storm-controller";

function environment(enabled = true) {
  const root = document.createElement("div");
  root.innerHTML = '<section data-storm-act="scope" data-storm-pin><div data-storm-stage><div><pre>static storm</pre><canvas aria-hidden="true"></canvas></div><ol>' + Array.from({ length: 5 }, () => '<li data-storm-verb>verb</li>').join("") + '</ol></div></section>';
  const entrance = document.createElement("h2");
  entrance.dataset.stormEnter = "";
  entrance.textContent = "Your project. Your thinking.";
  root.append(entrance);
  document.body.append(root);
  const section = root.querySelector("section")!;
  const canvas = root.querySelector("canvas")!;
  const rect = vi.spyOn(section, "getBoundingClientRect").mockImplementation(() => ({ top: -window.scrollY, height: 2520 } as DOMRect));
  vi.spyOn(root.querySelector("[data-storm-stage]")!, "getBoundingClientRect").mockReturnValue({ height: 900 } as DOMRect);
  Object.defineProperty(canvas.parentElement, "clientWidth", { value: 1000 });
  Object.defineProperty(canvas.parentElement, "clientHeight", { value: 700 });
  Object.defineProperty(window, "innerWidth", { value: 1440, configurable: true });
  Object.defineProperty(window, "devicePixelRatio", { value: 3, configurable: true });
  vi.spyOn(window, "scrollY", "get").mockReturnValue(0);
  let hidden = false;
  vi.spyOn(document, "hidden", "get").mockImplementation(() => hidden);
  let io: IntersectionObserverCallback;
  let ro: ResizeObserverCallback;
  const disconnectIO = vi.fn();
  const disconnectRO = vi.fn();
  vi.stubGlobal("IntersectionObserver", class {
    constructor(fn: IntersectionObserverCallback) { io = fn; }
    observe() {}
    disconnect = disconnectIO;
  });
  vi.stubGlobal("ResizeObserver", class {
    constructor(fn: ResizeObserverCallback) { ro = fn; }
    observe() {}
    disconnect = disconnectRO;
  });
  const mediaListeners = new Set<() => void>();
  const media = { get matches() { return enabled; }, addEventListener: (_: string, fn: () => void) => mediaListeners.add(fn), removeEventListener: (_: string, fn: () => void) => mediaListeners.delete(fn) };
  vi.spyOn(window, "matchMedia").mockReturnValue(media as unknown as MediaQueryList);
  let id = 0; let time = 0;
  const pending = new Map<number, FrameRequestCallback>();
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(fn => { pending.set(++id, fn); return id; });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(key => { pending.delete(key); });
  const context = { setTransform: vi.fn(), clearRect: vi.fn(), fillText: vi.fn(), globalAlpha: 1, font: "", fillStyle: "" };
  const getContext = vi.spyOn(canvas, "getContext").mockReturnValue(context as unknown as CanvasRenderingContext2D);
  return {
    root, section, canvas, rect, pending, context, getContext, disconnectIO, disconnectRO, mediaListeners,
    entrance,
    enterText(value = true) { io([{ target: entrance, isIntersecting: value } as unknown as IntersectionObserverEntry], {} as IntersectionObserver); },
    enter(value = true) { io([{ target: section, isIntersecting: value } as unknown as IntersectionObserverEntry], {} as IntersectionObserver); },
    resize() { ro([], {} as ResizeObserver); },
    motion(value: boolean) { enabled = value; mediaListeners.forEach(fn => fn()); },
    hidden(value: boolean) { hidden = value; document.dispatchEvent(new Event("visibilitychange")); },
    scroll(value: number) { vi.spyOn(window, "scrollY", "get").mockReturnValue(value); window.dispatchEvent(new Event("scroll")); },
    flush() { const callbacks = [...pending.values()]; pending.clear(); time += 16.67; callbacks.forEach(fn => fn(time)); },
  };
}

afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("storm motion ownership", () => {
  it("enhances readable text once without replaying on scroll or retaining state after cleanup", () => {
    const env = environment();
    const dispose = createStormController(env.root);
    expect(env.entrance.textContent).toBe("Your project. Your thinking.");
    expect(env.entrance.hasAttribute("data-entered")).toBe(false);
    env.enterText();
    expect(env.entrance.dataset.entered).toBe("true");
    env.enterText(false);
    expect(env.entrance.dataset.entered).toBe("true");
    env.motion(false);
    expect(env.root.hasAttribute("data-motion")).toBe(false);
    expect(env.entrance.hasAttribute("hidden")).toBe(false);
    dispose();
    env.enterText();
    expect(env.entrance.hasAttribute("data-entered")).toBe(false);
  });
  it("does no Canvas or RAF work before activation, coalesces scroll, and has no idle loop", () => {
    const env = environment();
    const dispose = createStormController(env.root);
    expect(env.getContext).not.toHaveBeenCalled();
    expect(env.pending.size).toBe(0);
    env.enter();
    env.scroll(100); env.scroll(200); env.scroll(300);
    expect(env.pending.size).toBe(1);
    env.flush();
    expect(env.context.fillText).toHaveBeenCalled();
    expect(env.pending.size).toBe(0);
    expect(env.canvas.width).toBe(2000);
    expect(env.canvas.height).toBe(1400);
    const measurements = env.rect.mock.calls.length;
    env.scroll(400); env.flush();
    expect(env.rect).toHaveBeenCalledTimes(measurements);
    dispose();
  });

  it("keeps the static posters under reduced motion and supports live preference changes", () => {
    const env = environment(false);
    const dispose = createStormController(env.root);
    env.enter(); env.scroll(400);
    expect(env.root.hasAttribute("data-motion")).toBe(false);
    expect(env.pending.size).toBe(0);
    expect(env.getContext).not.toHaveBeenCalled();
    env.motion(true); env.flush();
    expect(env.root.dataset.motion).toBe("on");
    expect(env.canvas.parentElement?.hasAttribute("data-canvas-ready")).toBe(true);
    env.scroll(500);
    env.motion(false);
    expect(env.pending.size).toBe(0);
    expect(env.canvas.parentElement?.hasAttribute("data-canvas-ready")).toBe(false);
    expect(env.root.querySelector("pre")?.textContent).toBe("static storm");
    expect(env.root.querySelectorAll("li")).toHaveLength(5);
    dispose();
  });

  it("freezes on hidden/offscreen documents and ignores cancelled callbacks after unmount", () => {
    const env = environment();
    const dispose = createStormController(env.root);
    env.enter();
    const stale = [...env.pending.values()][0];
    env.hidden(true);
    stale(0);
    expect(env.getContext).not.toHaveBeenCalled();
    env.hidden(false); env.flush();
    env.enter(false); env.scroll(800);
    expect(env.pending.size).toBe(0);
    env.enter();
    const afterUnmount = [...env.pending.values()][0];
    dispose();
    const paints = env.context.clearRect.mock.calls.length;
    afterUnmount(0); env.enter(); env.resize(); env.scroll(1000);
    expect(env.context.clearRect).toHaveBeenCalledTimes(paints);
    expect(env.pending.size).toBe(0);
    expect(env.disconnectIO).toHaveBeenCalledOnce();
    expect(env.disconnectRO).toHaveBeenCalledOnce();
    expect(env.mediaListeners.size).toBe(0);
    expect(env.root.hasAttribute("data-motion")).toBe(false);
  });

  it("protects new RAF ownership when a cancelled callback arrives after reactivation", () => {
    const env = environment();
    const dispose = createStormController(env.root);
    env.enter();
    const stale = [...env.pending.values()][0];
    env.motion(false); env.motion(true);
    const current = [...env.pending.values()][0];
    stale(0);
    expect(env.context.clearRect).not.toHaveBeenCalled();
    expect(env.pending.size).toBe(1);
    current(0);
    expect(env.context.clearRect).toHaveBeenCalledOnce();
    dispose();
  });

  it("resolves the meaningful change into five ordered verbs and caps mobile Canvas DPR", () => {
    const env = environment();
    Object.defineProperty(window, "innerWidth", { value: 390, configurable: true });
    const dispose = createStormController(env.root);
    env.enter(); env.scroll(486); env.flush();
    expect(env.section.style.getPropertyValue("--focus-opacity")).toBe("1");
    expect(env.section.style.getPropertyValue("--focus-opacity")).toBe("1");
    env.scroll(1620); for (let frame = 0; frame < 90 && env.pending.size; frame++) env.flush();
    expect(env.section.style.getPropertyValue("--peak-opacity")).toBe("1");
    expect(env.section.style.getPropertyValue("--details-opacity")).toBe("1");
    expect(env.section.style.getPropertyValue("--focus-opacity")).toBe("0");
    expect([...env.root.querySelectorAll<HTMLElement>("li")].every(item => item.style.getPropertyValue("--verb-x") === "0px")).toBe(true);
    expect(env.canvas.width).toBe(1500);
    dispose();
  });

  it("preserves the illustration if Canvas is unavailable", () => {
    const env = environment();
    env.getContext.mockReturnValue(null);
    const dispose = createStormController(env.root);
    env.enter(); env.flush();
    expect(env.canvas.parentElement?.hasAttribute("data-canvas-ready")).toBe(false);
    expect(env.root.querySelector("pre")).not.toBeNull();
    dispose();
  });

  it.each([[390, 342], [360, 312], [768, 650]])("keeps the expanding lens inside a %ipx viewport", (width, focusWidth) => {
    const env = environment();
    Object.defineProperty(window, "innerWidth", { value: width, configurable: true });
    const focus = document.createElement("div");
    focus.dataset.stormFocus = "";
    Object.defineProperty(focus, "clientWidth", { value: focusWidth });
    env.section.append(focus);
    const dispose = createStormController(env.root);
    env.enter();
    env.flush();
    const initialScale = Number(env.section.style.getPropertyValue("--lens-scale"));
    const initialX = 0;
    expect((width - focusWidth * initialScale) / 2 + initialX).toBeGreaterThanOrEqual(16);
    for (const progress of [0.35, 0.45, 0.5, 0.55, 0.6]) {
      env.scroll(1620 * progress); env.flush();
      const scale = Number(env.section.style.getPropertyValue("--lens-scale"));
      expect(focusWidth * scale).toBeLessThanOrEqual(width - 32);
    }
    dispose();
  });
});

describe("ASCII quality tiers", () => {
  it.each([false, true])("uses deterministic bounded fragments (mobile: %s)", mobile => {
    const fragments = createFragments(mobile);
    expect(fragments).toEqual(createFragments(mobile));
    expect(fragments.reduce((count, part) => count + part.text.length, 0)).toBeLessThanOrEqual(mobile ? 330 : 850);
    expect(fragments.length).toBeGreaterThan(20);
  });
});

describe("continuous visual pacing", () => {
  it("shows partial motion after a native burst, converges, and stops owning RAF", () => {
    const env = environment();
    const dispose = createStormController(env.root);
    env.enter(); env.flush();
    env.scroll(120); env.flush();
    const first = Number(env.section.dataset.visualProgress);
    expect(first).toBeGreaterThan(0);
    expect(first).toBeLessThan(120 / 1620);
    expect(env.pending.size).toBe(1);
    env.flush();
    expect(Number(env.section.dataset.visualProgress)).toBeGreaterThan(first);
    for (let frame = 0; frame < 90 && env.pending.size; frame++) env.flush();
    expect(env.pending.size).toBe(0);
    expect(Number(env.section.dataset.visualProgress)).toBeCloseTo(120 / 1620, 4);
    const measurements = env.rect.mock.calls.length;
    env.scroll(60); env.flush();
    expect(Number(env.section.dataset.visualProgress)).toBeGreaterThan(60 / 1620);
    expect(Number(env.section.dataset.visualProgress)).toBeLessThan(120 / 1620);
    expect(env.rect).toHaveBeenCalledTimes(measurements);
    dispose();
  });

  it("is refresh-rate independent, bounded on large jumps, and exact at rest", () => {
    const one = followVisual(0, 100, 32);
    const two = followVisual(followVisual(0, 100, 16), 100, 16);
    expect(one).toBeCloseTo(two, 8);
    expect(10000 - followVisual(0, 10000, 16)).toBeLessThan(160);
    expect(followVisual(100, 0, 16)).toBeLessThan(100);
    expect(followVisual(99.9, 100, 16)).toBe(100);
  });

  it("holds major text fully opaque and gives the completed method the most reading travel", () => {
    for (const p of [0.405, 0.43, 0.46, 0.48]) expect(cue(p, 0.38, 0.405, 0.48, 0.5)).toBe(1);
    for (const p of [0.715, 0.74, 0.77, 0.79]) expect(cue(p, 0.69, 0.715, 0.79, 0.815)).toBe(1);
    const methodTravel = (readingHolds.method[1] - readingHolds.method[0]) * 5.5;
    for (const hold of [readingHolds.idea, readingHolds.growth, readingHolds.lost, readingHolds.questions]) {
      expect(methodTravel).toBeGreaterThan((hold[1] - hold[0]) * 9);
    }
  });

  it("restores full typing text when motion changes and after disposal", () => {
    const env = environment();
    env.section.dataset.stormAct = "journey";
    const text = document.createElement("span"); text.dataset.promptText = "";
    text.textContent = "Build me a volleyball stats tracker for my team."; env.section.append(text);
    const dispose = createStormController(env.root);
    env.enter(); env.scroll(1620 * 0.14); env.flush();
    expect(text.textContent?.length).toBeGreaterThan(0);
    expect(text.textContent?.length).toBeLessThan(47);
    env.motion(false);
    expect(text.textContent).toBe("Build me a volleyball stats tracker for my team.");
    expect(env.pending.size).toBe(0);
    env.motion(true); env.flush(); dispose();
    expect(text.textContent).toBe("Build me a volleyball stats tracker for my team.");
  });
});
