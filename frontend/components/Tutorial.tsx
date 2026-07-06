"use client";

import { useEffect, useRef } from "react";

// "How Codize works" — the first-use tutorial (M13E.1). Unlike the
// reconnection modal (spec-locked to its button), this one is deliberately
// easy to leave: the button, Escape, or clicking the backdrop all close it.
// Whether it shows (localStorage first-visit flag) is the app shell's job;
// this component only renders the guide.

export const TUTORIAL_SEEN_KEY = "codize:tutorial-seen";

const STEPS: { title: string; body: string }[] = [
  { title: "Start with a project idea", body: "Codize asks five short questions about it. Plain language is perfect — no technical terms needed." },
  { title: "Codize turns it into phases", body: "You get a roadmap sized for your kind of project, one phase at a time." },
  { title: "Plan before you ask AI", body: "For each phase, use the Prompt Builder first. It helps you figure out what to ask — even if you don't know yet." },
  { title: "Generate in your own AI tool", body: "Paste the prompt into Claude, Cursor, ChatGPT, Copilot — whatever you use. Codize doesn't write your code." },
  { title: "Come back and review", body: "Note what the AI changed: what you accepted, rejected, or edited. This is where you stay in control." },
  { title: "Submit evidence", body: "A repo link, a commit, test output — small proof that the work is real." },
  { title: "Verify behavior", body: "Check it actually works, including one way it could fail. Trust what you proved, not what looked done." },
  { title: "Defend what you built", body: "At the end of each phase, explain your work in your own words. Pass the defense, unlock the next phase." },
  { title: "Export your Defense Report", body: "Everything above becomes a report you can bring to a demo, class, or interview." },
];

export default function Tutorial({ onClose }: { onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="How Codize works"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="pill accent">How Codize works</span>
        <p className="muted" style={{ marginTop: 14 }}>
          One loop, nine steps. You&rsquo;ll learn it by doing it — this is just the map. Reopen
          it anytime from the sidebar.
        </p>
        <ol className="tutorial-steps">
          {STEPS.map((s) => (
            <li key={s.title}>
              <span>
                <strong>{s.title}.</strong> {s.body}
              </span>
            </li>
          ))}
        </ol>
        <button
          ref={closeRef}
          className="btn primary"
          style={{ width: "100%", marginTop: 12 }}
          onClick={onClose}
        >
          Got it — let&rsquo;s build
        </button>
      </div>
    </div>
  );
}
