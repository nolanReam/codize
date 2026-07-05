"use client";

import { useEffect, useRef, useState } from "react";

// The landing-page signature: a scripted simulation of the AI patch loop,
// interrupted by Codize. No real AI calls, no real code execution — just a
// timed transcript. With prefers-reduced-motion (or before hydration) it
// renders the finished frame statically instead of looping.

type LineKind = "user" | "ai" | "err" | "warn";

interface ScriptLine {
  kind: LineKind;
  text: string;
  delay: number; // ms before the NEXT line appears
}

const SCRIPT: ScriptLine[] = [
  { kind: "user", text: "make me a study planner app with login", delay: 1500 },
  { kind: "ai", text: "✓ generated 14 files — runs on the first try", delay: 1400 },
  { kind: "user", text: "add a dark mode toggle", delay: 1400 },
  { kind: "ai", text: "✓ rewrote 6 files (diff unread)", delay: 1400 },
  {
    kind: "err",
    text: "✗ TypeError: cannot read properties of undefined (reading 'user')",
    delay: 1500,
  },
  { kind: "user", text: "[pastes the error back in]", delay: 1400 },
  { kind: "ai", text: "✓ patched — 2 workarounds added, 3 new warnings", delay: 1400 },
  { kind: "err", text: "✗ login broken. it worked ten minutes ago.", delay: 1500 },
  { kind: "user", text: "please just make it work", delay: 1500 },
  { kind: "warn", text: "⚠ patch applied on top of a patch", delay: 1000 },
  { kind: "warn", text: "⚠ no clear mental model of this codebase", delay: 1000 },
];

const OVERLAY_DELAY = 1100; // pause after the last line before Codize interrupts
const OVERLAY_HOLD = 6000; // how long the intervention stays before the loop restarts

export default function TrapTerminal() {
  // null = not yet hydrated → render the full static frame (also the SSR/no-JS
  // and reduced-motion output). false = motion allowed → run the loop.
  const [reduced, setReduced] = useState<boolean | null>(null);
  const [count, setCount] = useState(0);
  const [overlay, setOverlay] = useState(false);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  useEffect(() => {
    if (reduced !== false) return;
    let alive = true;
    let timer: number;

    const run = () => {
      setCount(0);
      setOverlay(false);
      let i = 0;
      const step = () => {
        if (!alive) return;
        if (i < SCRIPT.length) {
          timer = window.setTimeout(() => {
            i += 1;
            setCount(i);
            step();
          }, SCRIPT[i].delay);
        } else {
          timer = window.setTimeout(() => {
            if (!alive) return;
            setOverlay(true);
            timer = window.setTimeout(run, OVERLAY_HOLD);
          }, OVERLAY_DELAY);
        }
      };
      // show the first line immediately, then pace the rest
      i = 1;
      setCount(1);
      step();
    };

    run();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [reduced]);

  // keep the newest line in view if wrapping makes the transcript overflow
  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [count]);

  const animated = reduced === false;
  const visible = animated ? SCRIPT.slice(0, count) : SCRIPT;
  const showOverlay = animated ? overlay : true;
  const lastIndex = visible.length - 1;

  return (
    <div
      className={`tt${animated ? "" : " tt-static"}`}
      role="img"
      aria-label="Simulation of an AI coding session collapsing into a patch loop: a vague prompt generates a working-looking app, errors appear, patches pile on patches, until Codize interrupts with “Review required — you're not building anymore, you're negotiating.”"
    >
      <div className="tt-bar" aria-hidden="true">
        <span className="tt-dot" />
        <span className="tt-dot" />
        <span className="tt-dot" />
        <span className="tt-title">ai-session — patch loop · attempt 7</span>
      </div>
      <div className="tt-body" ref={bodyRef} aria-hidden="true">
        {visible.map((line, i) => (
          <div
            key={`${line.text}-${i}`}
            className={`tt-line ${line.kind}${i === lastIndex && line.kind === "user" ? " tt-cursor" : ""}`}
          >
            {line.text}
          </div>
        ))}
      </div>
      {showOverlay && (
        <div className="tt-overlay" aria-hidden="true">
          <span className="tt-badge">Review required</span>
          <p className="tt-overlay-title">
            You&rsquo;re not building anymore.
            <br />
            You&rsquo;re negotiating.
          </p>
          <p className="tt-overlay-sub">Codize trains the workflow that prevents this loop.</p>
        </div>
      )}
    </div>
  );
}
