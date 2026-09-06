// @vitest-environment happy-dom

import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import V2Character from "./V2Character";
import { CODYBARA_IDLE_FRAME_MS, CODYBARA_IDLE_FRAMES } from "../../lib/codybara";

vi.mock("next/image", () => ({
  default: ({ priority: _priority, unoptimized: _unoptimized, ...props }: React.ImgHTMLAttributes<HTMLImageElement> & {
    priority?: boolean;
    unoptimized?: boolean;
  }) => React.createElement("img", props),
}));

function installMotionEnvironment(initialReducedMotion = false) {
  let reducedMotion = initialReducedMotion;
  let nextFrameId = 1;
  let nextIntervalId = 100;
  const mediaListeners = new Set<() => void>();
  const frameCallbacks = new Map<number, FrameRequestCallback>();
  const intervalCallbacks = new Map<number, () => void>();

  const mediaQuery = {
    get matches() { return reducedMotion; },
    media: "(prefers-reduced-motion: reduce)",
    onchange: null,
    addEventListener: vi.fn((_type: string, listener: () => void) => mediaListeners.add(listener)),
    removeEventListener: vi.fn((_type: string, listener: () => void) => mediaListeners.delete(listener)),
  } as unknown as MediaQueryList;
  const requestAnimationFrame = vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback: FrameRequestCallback) => {
    const id = nextFrameId++;
    frameCallbacks.set(id, callback);
    return id;
  });
  const cancelAnimationFrame = vi.spyOn(window, "cancelAnimationFrame").mockImplementation((id: number) => {
    frameCallbacks.delete(id);
  });
  const setInterval = vi.spyOn(window, "setInterval").mockImplementation((callback: Parameters<typeof window.setInterval>[0]) => {
    const id = nextIntervalId++;
    if (typeof callback === "function") intervalCallbacks.set(id, callback as () => void);
    return id as unknown as ReturnType<typeof window.setInterval>;
  });
  const clearInterval = vi.spyOn(window, "clearInterval").mockImplementation((id: Parameters<typeof window.clearInterval>[0]) => {
    if (typeof id === "number") intervalCallbacks.delete(id);
  });

  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.spyOn(window, "matchMedia").mockImplementation(() => mediaQuery);

  return {
    mediaQuery,
    frameCallbacks,
    intervalCallbacks,
    requestAnimationFrame,
    cancelAnimationFrame,
    setInterval,
    clearInterval,
    setReducedMotion(value: boolean) {
      reducedMotion = value;
      mediaListeners.forEach((listener) => listener());
    },
  };
}

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function createCharacterRoot() {
  const container = document.createElement("div");
  document.body.append(container);
  return { container, root: createRoot(container) };
}

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

  it("keeps one stable frame when reduced motion wins a pending frame-request race", async () => {
    const motion = installMotionEnvironment(false);
    const { container, root } = createCharacterRoot();

    await act(async () => {
      root.render(<V2Character size="medium" />);
    });

    expect(container.querySelectorAll("img")).toHaveLength(1);
    expect(motion.requestAnimationFrame).toHaveBeenCalledTimes(1);
    const pendingFrameId = [...motion.frameCallbacks.keys()][0];
    const staleFrameCallback = motion.frameCallbacks.get(pendingFrameId);
    expect(staleFrameCallback).toBeDefined();

    await act(async () => {
      motion.setReducedMotion(true);
    });

    expect(motion.cancelAnimationFrame).toHaveBeenCalledWith(pendingFrameId);
    expect(motion.frameCallbacks.size).toBe(0);

    await act(async () => {
      staleFrameCallback?.(16);
    });

    const images = container.querySelectorAll("img");
    expect(images).toHaveLength(1);
    expect(images[0].getAttribute("src")).toBe(CODYBARA_IDLE_FRAMES[0]);
    expect(images[0].classList).toContain("is-current");
    expect(motion.setInterval).not.toHaveBeenCalled();

    await act(async () => root.unmount());
  });

  it("never schedules animation when reduced motion is active at mount", async () => {
    const motion = installMotionEnvironment(true);
    const { container, root } = createCharacterRoot();

    await act(async () => {
      root.render(<V2Character />);
    });

    const images = container.querySelectorAll("img");
    expect(images).toHaveLength(1);
    expect(images[0].getAttribute("src")).toBe(CODYBARA_IDLE_FRAMES[0]);
    expect(images[0].classList).toContain("is-current");
    expect(motion.requestAnimationFrame).not.toHaveBeenCalled();
    expect(motion.setInterval).not.toHaveBeenCalled();

    await act(async () => root.unmount());
  });

  it("cancels a pending frame request when the character unmounts", async () => {
    const motion = installMotionEnvironment(false);
    const { root } = createCharacterRoot();

    await act(async () => {
      root.render(<V2Character />);
    });
    const pendingFrameId = [...motion.frameCallbacks.keys()][0];

    await act(async () => root.unmount());

    expect(motion.cancelAnimationFrame).toHaveBeenCalledWith(pendingFrameId);
    expect(motion.frameCallbacks.size).toBe(0);
    expect(motion.mediaQuery.removeEventListener).toHaveBeenCalledOnce();
  });

  it("loads allowed frames lazily, starts after every load, and stops for reduced motion", async () => {
    const motion = installMotionEnvironment(false);
    const { container, root } = createCharacterRoot();

    await act(async () => {
      root.render(<V2Character />);
    });
    const pendingFrame = [...motion.frameCallbacks.values()][0];
    expect(pendingFrame).toBeDefined();

    await act(async () => {
      pendingFrame?.(16);
    });

    let images = [...container.querySelectorAll("img")];
    expect(images).toHaveLength(CODYBARA_IDLE_FRAMES.length);
    expect(images[0].getAttribute("loading")).toBe("eager");
    expect(images.slice(1).every((image) => image.getAttribute("loading") === "lazy")).toBe(true);
    expect(motion.setInterval).not.toHaveBeenCalled();

    await act(async () => {
      images.slice(1, -1).forEach((image) => image.dispatchEvent(new Event("load")));
    });
    expect(motion.setInterval).not.toHaveBeenCalled();

    await act(async () => {
      images.at(-1)?.dispatchEvent(new Event("load"));
    });
    expect(motion.setInterval).toHaveBeenCalledOnce();
    expect(motion.setInterval).toHaveBeenCalledWith(expect.any(Function), CODYBARA_IDLE_FRAME_MS);

    const intervalCallback = [...motion.intervalCallbacks.values()][0];
    expect(intervalCallback).toBeDefined();
    await act(async () => intervalCallback?.());
    images = [...container.querySelectorAll("img")];
    expect(images.find((image) => image.classList.contains("is-current"))?.getAttribute("src"))
      .toBe(CODYBARA_IDLE_FRAMES[1]);

    await act(async () => {
      motion.setReducedMotion(true);
    });
    images = [...container.querySelectorAll("img")];
    expect(images).toHaveLength(1);
    expect(images[0].getAttribute("src")).toBe(CODYBARA_IDLE_FRAMES[0]);
    expect(images[0].classList).toContain("is-current");
    expect(motion.clearInterval).toHaveBeenCalledWith(100);
    expect(motion.intervalCallbacks.size).toBe(0);

    await act(async () => root.unmount());
    expect(motion.mediaQuery.removeEventListener).toHaveBeenCalledOnce();
  });
});
