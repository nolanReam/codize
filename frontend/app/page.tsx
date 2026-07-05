import Link from "next/link";

import Reveal from "@/components/Reveal";
import TrapTerminal from "@/components/TrapTerminal";

// Landing page — the 80% Trap. Static, no backend calls, no session needed.

const TRAP_LOG: { hash: string; kind: "feat" | "fix" | "warn" | "codize"; text: string }[] = [
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

const STAGES: { n: string; name: string; tag?: "codize" | "your-ai"; blurb: string }[] = [
  { n: "01", name: "Plan", blurb: "Decide the architecture before the AI writes a line." },
  { n: "02", name: "Prompt", blurb: "Scoped, constraint-driven asks — not “make it work.”" },
  { n: "03", name: "Generate", tag: "your-ai", blurb: "Your AI tool does this part. It always did." },
  { n: "04", name: "Review", tag: "codize", blurb: "Read the diff. Accept or reject with reasons." },
  { n: "05", name: "Verify", tag: "codize", blurb: "Prove it behaves — evidence, not vibes." },
  { n: "06", name: "Explain", tag: "codize", blurb: "Defend your implementation in a live gate." },
  { n: "07", name: "Commit / Reflect", blurb: "Ship it with a Defense Report behind it." },
];

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

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">{"// the 80% trap"}</p>
          <h1>
            AI built your first <span className="hl">80%</span>. Now you&rsquo;re stuck fixing the
            rest.
          </h1>
          <p className="sub">
            Generating code is easy. Understanding why it broke is the hard part. Codize helps
            student builders plan, prompt, review, verify, and defend AI-generated code — so you
            stay the engineer when the project starts breaking.
          </p>
          <div className="ctas">
            <Link href="/login" className="btn primary">
              Stop Debugging Blindly
            </Link>
            <a href="#workflow" className="btn">
              View the Project Defense Workflow
            </a>
          </div>
        </div>
        <TrapTerminal />
      </section>

      <section className="section">
        <p className="eyebrow">{"// git log --oneline"}</p>
        <h2>The 80% Trap</h2>
        <p className="lead">
          You know this history. Everyone building with AI knows this history.
        </p>
        <Reveal className="trap-log">
          {TRAP_LOG.map((line, i) => (
            <div
              key={line.hash}
              className={`log-line ${line.kind}`}
              style={{ "--i": i } as React.CSSProperties}
            >
              <span className="log-hash">{line.hash}</span>
              <span className="log-msg">{line.text}</span>
            </div>
          ))}
        </Reveal>
      </section>

      <section className="section" id="workflow">
        <p className="eyebrow">{"// the codize build loop"}</p>
        <h2>Review AI like a teammate, not a magic box.</h2>
        <p className="lead">
          Codize doesn&rsquo;t generate your code — your AI tool already does that. Codize trains
          the workflow around it, one phase at a time:
        </p>
        <ol className="pipeline">
          {STAGES.map((stage) => (
            <li key={stage.n} className={stage.tag === "codize" ? "codize" : stage.tag === "your-ai" ? "your-ai" : ""}>
              <span className="node-dot" aria-hidden="true" />
              <span className="node-n">{stage.n}</span>
              <span className="node-name">{stage.name}</span>
              {stage.tag && (
                <span className="node-tag">{stage.tag === "codize" ? "codize" : "your AI tool"}</span>
              )}
              <span className="node-blurb">{stage.blurb}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="section">
        <p className="eyebrow">{"// project defense"}</p>
        <h2>Be ready to defend what you shipped.</h2>
        <p className="lead">
          Every phase ends at the Project Defense gate — and every project leaves with a report
          you can stand behind in the demo, the interview, or the judging room.
        </p>
        <div className="card-grid" style={{ marginTop: 24 }}>
          <div className="card">
            <h3>The Defense Gate</h3>
            <p>
              Three live questions about <em>your</em> implementation — anchored to what you
              actually built, not textbook trivia. Pass it, and the next phase unlocks.
            </p>
          </div>
          <div className="card">
            <h3>The Defense Report</h3>
            <p>
              A Markdown record of what you planned, prompted, reviewed, and verified — with the
              evidence attached. Export it and take it anywhere.
            </p>
          </div>
        </div>
      </section>

      <section className="closing">
        <h2>
          Your workflow is incomplete.
          <br />
          <span className="hl">Codize helps you fix it.</span>
        </h2>
        <p className="lead">
          AI can get you to the first 80% fast. Codize is how you stay in control of the rest.
        </p>
        <div className="ctas" style={{ justifyContent: "center", marginTop: 28 }}>
          <Link href="/login" className="btn primary">
            Stop Debugging Blindly
          </Link>
        </div>
      </section>

      <footer className="landing-footer muted">
        Codize — an AI coding workflow trainer for student builders.
      </footer>
    </div>
  );
}
