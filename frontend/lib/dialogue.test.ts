import { describe, expect, it, vi } from "vitest";

import { createDialogueRevealController, type DialogueAudio } from "./dialogue";

function harness() {
  const queue: Array<() => void> = [];
  const audio: DialogueAudio = {
    paused: true, ended: false, currentTime: 0,
    play: vi.fn(() => { audio.paused = false; }),
    pause: vi.fn(() => { audio.paused = true; }),
  };
  return { queue, audio, timers: {
    set(callback: () => void) { queue.push(callback); return callback; },
    clear(handle: unknown) { const index = queue.indexOf(handle as () => void); if (index >= 0) queue.splice(index, 1); },
  }};
}

describe("dialogue reveal controller", () => {
  it("reveals immediately without audio for reduced motion", () => {
    const { audio, timers } = harness();
    const update = vi.fn();
    createDialogueRevealController({ text: "Hello", soundEnabled: true,
      reducedMotion: true, onUpdate: update, audio, timers });
    expect(update).toHaveBeenLastCalledWith("Hello", true);
    expect(audio.play).not.toHaveBeenCalled();
  });

  it("uses one non-overlapping intermittent blip and stops on skip", () => {
    const { audio, queue, timers } = harness();
    const update = vi.fn();
    const controller = createDialogueRevealController({ text: "abcdefghi",
      soundEnabled: true, reducedMotion: false, onUpdate: update, audio, timers });
    for (let index = 0; index < 5; index += 1) queue.shift()?.();
    expect(audio.play).toHaveBeenCalledTimes(1);
    controller.skip();
    expect(update).toHaveBeenLastCalledWith("abcdefghi", true);
    expect(audio.pause).toHaveBeenCalled();
    expect(queue).toHaveLength(0);
  });

  it("cancels pending work and sound on dispose", () => {
    const { audio, queue, timers } = harness();
    const update = vi.fn();
    const controller = createDialogueRevealController({ text: "Still typing",
      soundEnabled: false, reducedMotion: false, onUpdate: update, audio, timers });
    controller.dispose();
    expect(queue).toHaveLength(0);
    expect(audio.pause).toHaveBeenCalled();
  });

  it("never requests playback when dialogue sound is disabled", () => {
    const { audio, queue, timers } = harness();
    createDialogueRevealController({ text: "abcdef", soundEnabled: false,
      reducedMotion: false, onUpdate: vi.fn(), audio, timers });
    while (queue.length) queue.shift()?.();
    expect(audio.play).not.toHaveBeenCalled();
  });
});
