import Link from "next/link";

import BuildLoopPanel from "@/components/BuildLoopPanel";
import PatchLoopScene from "@/components/PatchLoopScene";
import Reveal from "@/components/Reveal";
import TiltCard from "@/components/TiltCard";
import TrapTerminal from "@/components/TrapTerminal";

// Landing page — the 80% Trap, told as a sequence of centered scenes.
// Static, no backend calls, no session needed.

export default function LandingPage() {
  return (
    <div className="landing">
      <header>
        <div className="brand">
          CODIZE<span>_</span>
        </div>
        <nav className="row">
          <Link href="/login" className="btn small">
            Sign in
          </Link>
        </nav>
      </header>

      {/* Scene 1 — opening: the 80% trap, demonstrated */}
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">{"// the 80% trap"}</p>
          <h1>
            AI built your first <span className="hl">80%</span>.
            <br />
            Now you&rsquo;re stuck <em>fixing the rest</em>.
          </h1>
          <p className="sub">
            Codize trains student builders to plan, prompt, review, verify, and defend
            AI-generated code — so you stay the engineer when the project starts breaking.
          </p>
          <div className="ctas">
            <Link href="/login" className="btn primary">
              Stop Debugging Blindly
            </Link>
            <a href="#workflow" className="btn">
              See the workflow
            </a>
          </div>
        </div>
        <div className="hero-stage">
          <TiltCard>
            <TrapTerminal />
          </TiltCard>
        </div>
      </section>

      {/* Scene 2 — descending into the patch loop (scroll-driven) */}
      <PatchLoopScene />

      {/* Scene 3 — the Build Loop instrument panel (scroll-driven) */}
      <BuildLoopPanel />

      {/* Scene 4 — Project Defense */}
      <section className="scene">
        <Reveal className="scene-head">
          <p className="eyebrow" style={{ "--i": 0 } as React.CSSProperties}>
            {"// project defense"}
          </p>
          <h2 style={{ "--i": 1 } as React.CSSProperties}>
            Every phase ends at <em>the gate</em>.
          </h2>
          <p className="lead" style={{ "--i": 2 } as React.CSSProperties}>
            Three live questions about what you actually built. No textbook answers.
          </p>
        </Reveal>
        <Reveal className="defense-grid">
          <div className="glass panel" style={{ "--i": 0 } as React.CSSProperties}>
            <div className="panel-bar">
              <span className="panel-path">gate/current</span>
              <span className="pill accent">live</span>
            </div>
            <div className="panel-body mono">
              <p className="pl dim">anchor: &ldquo;JWT checks live in core/security.py&rdquo;</p>
              <p className="pl">turn_01 ▸ why JWKS instead of a shared secret?</p>
              <p className="pl">turn_02 ▸ what breaks if the key rotates?</p>
              <p className="pl">turn_03 ▸ suppose logins fail at midnight&hellip;</p>
              <p className="pl dim">format: implementation-specific · no retry spam</p>
            </div>
          </div>
          <div className="glass panel" style={{ "--i": 1 } as React.CSSProperties}>
            <div className="panel-bar">
              <span className="panel-path">defense_status</span>
              <span className="pill ok">ready</span>
            </div>
            <div className="panel-body mono">
              <p className="pl">phase: 3 / 7</p>
              <p className="pl">artifacts: 4 / 4 submitted</p>
              <p className="pl">verification: self-reported ✓</p>
              <p className="pl dim">evidence: 2 links · 1 commit</p>
              <p className="pl ok">ready to defend</p>
            </div>
          </div>
        </Reveal>
      </section>

      {/* Scene 5 — the payoff: the Defense Report */}
      <section className="scene">
        <Reveal className="scene-head">
          <p className="eyebrow" style={{ "--i": 0 } as React.CSSProperties}>
            {"// the payoff"}
          </p>
          <h2 style={{ "--i": 1 } as React.CSSProperties}>
            Leave with <em>proof of process</em>.
          </h2>
          <p className="lead" style={{ "--i": 2 } as React.CSSProperties}>
            Planned. Prompted. Reviewed. Verified. Defended. Exportable.
          </p>
        </Reveal>
        <Reveal className="report-stage">
          <div className="glass report-doc" style={{ "--i": 0 } as React.CSSProperties}>
            <div className="panel-bar">
              <span className="panel-path">defense_report.md</span>
              <span className="pill">markdown</span>
            </div>
            <div className="report-body mono">
              <p className="rl h"># Project Defense Report</p>
              <p className="rl dim">study planner · phase 3 · full-stack web app</p>
              <p className="rl">## What I planned <span className="ok">✓</span></p>
              <p className="rl">## What I prompted <span className="ok">✓</span> <span className="dim">2 scoped prompts</span></p>
              <p className="rl">## What I reviewed <span className="ok">✓</span> <span className="dim">accepted 5 · rejected 1</span></p>
              <p className="rl">## Submitted evidence <span className="dim">self-reported verification</span></p>
              <p className="rl">## Defense <span className="ok">PASS</span> <span className="dim">defended in 3 turns</span></p>
            </div>
          </div>
          <p className="report-note muted" style={{ "--i": 1 } as React.CSSProperties}>
            Built from your own workflow record — take it to the demo, the interview, the judging
            room.
          </p>
        </Reveal>
      </section>

      {/* Scene 6 — closing */}
      <section className="closing">
        <Reveal className="closing-inner">
          <h2 style={{ "--i": 0 } as React.CSSProperties}>
            Your workflow is <em>incomplete</em>.
            <br />
            <span className="hl">Codize helps you fix it.</span>
          </h2>
          <p className="lead" style={{ "--i": 1 } as React.CSSProperties}>
            AI gets you to 80% fast. Stay in control of the rest.
          </p>
          <div className="ctas" style={{ "--i": 2, marginTop: 32 } as React.CSSProperties}>
            <Link href="/login" className="btn primary">
              Stop Debugging Blindly
            </Link>
          </div>
        </Reveal>
      </section>

      <footer className="landing-footer muted">
        Codize — an AI coding workflow trainer for student builders.
      </footer>
    </div>
  );
}
