export interface DialogueAudio {
  paused: boolean;
  ended: boolean;
  currentTime: number;
  play(): Promise<void> | void;
  pause(): void;
}

interface DialogueTimers {
  set(callback: () => void, delay: number): unknown;
  clear(handle: unknown): void;
}

export function createDialogueRevealController(options: {
  text: string;
  soundEnabled: boolean;
  reducedMotion: boolean;
  onUpdate: (visibleText: string, complete: boolean) => void;
  audio: DialogueAudio | null;
  timers?: DialogueTimers;
}) {
  const timers = options.timers ?? {
    set: (callback, delay) => window.setTimeout(callback, delay),
    clear: (handle) => window.clearTimeout(handle as number),
  };
  let index = options.reducedMotion ? options.text.length : 0;
  let handle: unknown = null;
  let disposed = false;

  const stopSound = () => {
    options.audio?.pause();
    if (options.audio) options.audio.currentTime = 0;
  };
  const finish = () => {
    index = options.text.length;
    options.onUpdate(options.text, true);
    stopSound();
  };
  const tick = () => {
    if (disposed) return;
    index += 1;
    const character = options.text[index - 1] ?? "";
    options.onUpdate(options.text.slice(0, index), index >= options.text.length);
    if (options.soundEnabled && index % 3 === 0 && /[\p{L}\p{N}]/u.test(character)
        && options.audio && (options.audio.paused || options.audio.ended)) {
      options.audio.currentTime = 0;
      const playback = options.audio.play();
      if (playback instanceof Promise) void playback.catch(() => undefined);
    }
    if (index < options.text.length) handle = timers.set(tick, 24);
    else stopSound();
  };

  if (options.reducedMotion || options.text.length === 0) finish();
  else {
    options.onUpdate("", false);
    handle = timers.set(tick, 24);
  }

  return {
    skip: () => {
      if (handle !== null) timers.clear(handle);
      finish();
    },
    dispose: () => {
      disposed = true;
      if (handle !== null) timers.clear(handle);
      stopSound();
    },
  };
}
