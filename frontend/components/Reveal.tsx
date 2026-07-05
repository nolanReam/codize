"use client";

import { useEffect, useRef, useState } from "react";

// Scroll-triggered reveal wrapper. Content is fully visible by default (SSR,
// no-JS, reduced motion, already-on-screen); only after hydration — and only
// when motion is allowed and the block is still below the fold — does it hide
// children and fade them in on first intersection.

type Phase = "visible" | "pre" | "in";

export default function Reveal({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [phase, setPhase] = useState<Phase>("visible");

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.9) return;

    setPhase("pre");
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setPhase("in");
          io.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const phaseClass = phase === "pre" ? " reveal-pre" : phase === "in" ? " reveal-in" : "";
  return (
    <div ref={ref} className={`${className}${phaseClass}`.trim()}>
      {children}
    </div>
  );
}
