export const CODYBARA_IDLE_FRAMES = Array.from(
  { length: 7 },
  (_, index) =>
    `/characters/codybara/animations/idle/codybara_idle_${String(index + 1).padStart(2, "0")}.png`
) as readonly string[];

export const CODYBARA_DIALOGUE_BLIP =
  "/characters/codybara/audio/dialogue-blip.mp3";

export const CODYBARA_IDLE_FRAME_MS = 220;
