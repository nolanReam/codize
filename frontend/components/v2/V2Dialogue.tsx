"use client";

import { useEffect, useRef, useState } from "react";

import { CODYBARA_DIALOGUE_BLIP } from "@/lib/codybara";
import { createDialogueRevealController } from "@/lib/dialogue";

export default function V2Dialogue({ text, soundEnabled }: { text: string; soundEnabled: boolean }) {
  const [visible, setVisible] = useState(text);
  const [complete, setComplete] = useState(true);
  const controller = useRef<ReturnType<typeof createDialogueRevealController> | null>(null);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const audio = typeof Audio === "undefined" ? null : new Audio(CODYBARA_DIALOGUE_BLIP);
    if (audio) audio.volume = 0.22;
    const next = createDialogueRevealController({
      text, soundEnabled, reducedMotion: reduced, audio,
      onUpdate: (value, done) => { setVisible(value); setComplete(done); },
    });
    controller.current = next;
    return () => { next.dispose(); controller.current = null; };
  }, [soundEnabled, text]);

  return (
    <div className="v2-dialogue">
      <p aria-live="polite">{visible}<span className="sr-only">{complete ? "" : " Message typing."}</span></p>
      {!complete && <button type="button" className="v2-inline-button" onClick={() => controller.current?.skip()}>
        Show full message
      </button>}
    </div>
  );
}
