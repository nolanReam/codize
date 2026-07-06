"use client";

import { useEffect, useRef, useState } from "react";

// Premium interactive card wrapper for the hero terminal: subtle pointer tilt
// that returns to neutral on leave, traveling edge light beams, and a
// pointer-following sheen. Behavior adapted from the sign-in card reference —
// pure CSS + direct style-var writes, no animation library. Tilt only runs on
// fine pointers with motion allowed; touch / reduced motion get the static card.

const MAX_TILT = 6; // degrees

export default function TiltCard({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const raf = useRef(0);
  const [interactive, setInteractive] = useState(false);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setInteractive(fine && !reduced);
    return () => cancelAnimationFrame(raf.current);
  }, []);

  const onMouseMove = (e: React.MouseEvent) => {
    if (!interactive) return;
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width; // 0..1
    const py = (e.clientY - rect.top) / rect.height;
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => {
      el.style.setProperty("--ry", `${((px - 0.5) * 2 * MAX_TILT).toFixed(2)}deg`);
      el.style.setProperty("--rx", `${((0.5 - py) * 2 * MAX_TILT).toFixed(2)}deg`);
      el.style.setProperty("--mx", `${(px * 100).toFixed(1)}%`);
      el.style.setProperty("--my", `${(py * 100).toFixed(1)}%`);
    });
  };

  const onMouseLeave = () => {
    const el = ref.current;
    if (!el) return;
    cancelAnimationFrame(raf.current);
    raf.current = 0;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
  };

  return (
    <div
      ref={ref}
      className={`tcard${interactive ? " tcard-live" : ""}`}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
    >
      <div className="tcard-inner">
        {children}
        <span className="tcard-edge" aria-hidden="true" />
        <span className="tcard-sheen" aria-hidden="true" />
      </div>
    </div>
  );
}
