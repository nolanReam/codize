"use client";

import { useEffect, useRef, useState } from "react";

// The 80% Trap as a scroll-driven scene: a sticky git-log panel where commits
// surface one at a time as the user scrolls, a "control" meter drains, and
// Codize interrupts at the bottom. With reduced motion (or before hydration /
// without JS) it renders as a normal static block with every line visible —
// no sticky track, no hidden content.

const LOG: { hash: string; kind: "feat" | "fix" | "warn" | "codize"; text: string }[] = [
  { hash: "a3f9c21", kind: "feat", text: "feat: generate the whole app from one prompt" },
  { hash: "b7e2d10", kind: "feat", text: "feat: ask for one more feature" },
  { hash: "c1d8e92", kind: "fix", text: "fix: paste the error back into the AI" },
  { hash: "d4a1f77", kind: "fix", text: "fix: patch the patch" },
  { hash: "e9c3b04", kind: "fix", text: "fix: why is auth broken now" },
  { hash: "f2e7a19", kind: "fix", text: "fix: pls work" },
  { hash: "warning", kind: "warn", text: "6 rewrites accepted without reading the diff" },
  {
    hash: "codize",
    kind: "codize",
    text: "review required — you're negotiating with a codebase you never learned",
  },
];

const CELLS = 8; // control-meter segments, one lost per surfaced line

export default function PatchLoopScene() {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [mode, setMode] = useState<"static" | "scroll">("static");
  const [shown, setShown] = useState(LOG.length);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    setMode("scroll");
    setShown(0);
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const el = trackRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const total = rect.height - window.innerHeight;
        const p = total > 0 ? Math.min(1, Math.max(0, -rect.top / total)) : 1;
        const next = Math.min(LOG.length, Math.floor(p * (LOG.length + 1)));
        setShown((prev) => (prev === next ? prev : next));
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  const finished = shown >= LOG.length;
  const control = Math.max(0, CELLS - shown);
  const meterState = finished ? "lost" : control <= 3 ? "low" : control <= 5 ? "mid" : "ok";

  return (
    <section
      ref={trackRef}
      className={mode === "scroll" ? "trap-track" : "trap-track trap-track-static"}
      aria-label="The 80% Trap"
    >
      <div className="trap-sticky">
        <div className="scene-head">
          <p className="eyebrow">{"// git log --oneline"}</p>
          <h2>
            The <em>80%</em> Trap
          </h2>
          <p className="lead">You know this history. Everyone building with AI knows it.</p>
        </div>
        <div className={`trap-panel glass${finished ? " trap-final" : ""}`}>
          <div className="trap-lines">
            {LOG.slice(0, shown).map((line) => (
              <div key={line.hash} className={`log-line ${line.kind}`}>
                <span className="log-hash">{line.hash}</span>
                <span className="log-msg">{line.text}</span>
              </div>
            ))}
            {!finished && mode === "scroll" && (
              <div className="log-line log-hint" aria-hidden="true">
                <span className="log-hash">·······</span>
                <span className="log-msg">keep scrolling</span>
              </div>
            )}
          </div>
          <div className={`trap-meter ${meterState}`} aria-hidden="true">
            <span className="meter-label">control</span>
            <span className="meter-bar">
              {Array.from({ length: CELLS }, (_, i) => (
                <span key={i} className={`meter-cell${i < control ? " on" : ""}`} />
              ))}
            </span>
            <span className="meter-value">{finished ? "review required" : `${Math.round((control / CELLS) * 100)}%`}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
