"use client";

import { useEffect, useRef, useState } from "react";

// The Project Defense gate as a scroll-driven simulation: one centered panel
// where a scripted exchange surfaces message by message as the user scrolls —
// gate question, your answer, deeper follow-up, implementation explanation,
// then a defense status and the report line that records it. This is a visual
// explanation only (labelled "simulated preview"): no real gate runs here, no
// scores, no evaluator reasoning. With reduced motion (or before hydration /
// without JS) every message renders statically — no sticky track.

type Side = "gate" | "you" | "status";

interface GateStep {
  side: Side;
  label: string;
  text: React.ReactNode;
}

const STEPS: GateStep[] = [
  {
    side: "gate",
    label: "turn_01",
    text: "You said auth lives in core/security.py. Why not just trust the client session?",
  },
  {
    side: "you",
    label: "your_answer",
    text: "Because anyone can edit the frontend. The backend re-checks the token signature before any query runs.",
  },
  {
    side: "gate",
    label: "follow_up",
    text: "Then what breaks if the signing key rotates tonight?",
  },
  {
    side: "you",
    label: "explain_implementation",
    text: "Verification looks keys up by ID over JWKS, so new logins pick up the new key automatically. Older cached tokens fail closed with a 401 — nothing gets through unverified.",
  },
  {
    side: "status",
    label: "defense_status",
    text: (
      <>
        <span className="ok">DEFENSE STATUS: READY</span>
        <span className="dim">answered from your implementation, not a textbook</span>
      </>
    ),
  },
  {
    side: "status",
    label: "recorded_in_report",
    text: (
      <>
        <span className="ok">✓</span>
        <span>defense_report.md updated — this defense is now part of your record</span>
      </>
    ),
  },
];

export default function GateScene() {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [mode, setMode] = useState<"static" | "scroll">("static");
  const [shown, setShown] = useState(STEPS.length);

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
        const next = Math.min(STEPS.length, Math.floor(p * (STEPS.length + 1)));
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

  const finished = shown >= STEPS.length;

  return (
    <section
      ref={trackRef}
      className={mode === "scroll" ? "gate-track" : "gate-track gate-track-static"}
      aria-label="Project Defense — how the gate works"
    >
      <div className="gate-sticky">
        <div className="scene-head">
          <p className="eyebrow">{"// project defense"}</p>
          <h2>
            Every phase ends at <em>the gate</em>.
          </h2>
          <p className="lead">
            You answer for what you built. Codize probes deeper. The result goes on record.
          </p>
        </div>
        <div className="glass gate-panel">
          <div className="panel-bar">
            <span className="panel-path">project_defense — simulated preview</span>
            <span className="pill accent">preview</span>
          </div>
          <div className="gate-body">
            {STEPS.slice(0, shown).map((step) => (
              <div key={step.label} className={`gm ${step.side}`}>
                <span className="gm-label">{step.label}</span>
                {step.side === "status" ? (
                  <span className="gm-status-line mono">{step.text}</span>
                ) : (
                  <span className="gm-bubble">{step.text}</span>
                )}
              </div>
            ))}
          </div>
        </div>
        {mode === "scroll" && (
          <p
            className="bl-hint"
            style={{ visibility: finished ? "hidden" : "visible" }}
            aria-hidden="true"
          >
            scroll to answer
          </p>
        )}
      </div>
    </section>
  );
}
