import Link from "next/link";

// Landing page — the 80% Trap. Static, no backend calls, no session needed.
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
        <h1>AI built your first 80%. Now you&rsquo;re stuck fixing the rest.</h1>
        <p className="sub">
          Generating code is easy. Understanding why it broke is the hard part. Codize helps
          student builders plan, prompt, review, verify, and defend AI-generated code before
          their projects collapse into patch loops.
        </p>
        <div className="ctas">
          <Link href="/login" className="btn primary">
            Stop Debugging Blindly
          </Link>
          <a href="#workflow" className="btn">
            View the Project Defense Workflow
          </a>
        </div>
      </section>

      <section className="section">
        <h2>The 80% Trap</h2>
        <p className="lead">You know this loop. Everyone building with AI knows this loop.</p>
        <ol className="trap-steps">
          <li>You give the AI a vague prompt. A working-looking app appears.</li>
          <li>You ask for one more feature.</li>
          <li>The AI rewrites files you never really read.</li>
          <li>Something breaks. You paste the error back in.</li>
          <li>The AI adds patches on top of patches.</li>
          <li>
            Now you&rsquo;re not building anymore — you&rsquo;re negotiating with a codebase you
            never learned.
          </li>
        </ol>
      </section>

      <section className="section" id="workflow">
        <h2>Review AI like a teammate, not a magic box.</h2>
        <p className="lead">
          Codize doesn&rsquo;t generate your code — your AI tool already does that. Codize trains
          the workflow around it:
        </p>
        <p className="loop-inline" style={{ margin: "18px 0" }}>
          Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect
        </p>
        <div className="card-grid">
          <div className="card">
            <h3>Plan &amp; Prompt</h3>
            <p>
              Decide the architecture before generating. Build scoped, constraint-driven prompts
              instead of &ldquo;make it work.&rdquo;
            </p>
          </div>
          <div className="card">
            <h3>Review &amp; Verify</h3>
            <p>
              Record what the AI changed, what you accepted or rejected, and prove the result
              behaves — with real evidence, not vibes.
            </p>
          </div>
          <div className="card">
            <h3>Explain &amp; Defend</h3>
            <p>
              Pass an interrogation gate about <em>your</em> implementation, and leave with a
              Project Defense Report you can stand behind in any interview.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Be ready to defend what you shipped.</h2>
        <p className="lead">
          AI can help you ship faster. Codize helps you stay in control when the code starts to
          matter — for the demo, the interview, the judging table, or the moment it breaks in
          production.
        </p>
        <div style={{ marginTop: 24 }}>
          <Link href="/login" className="btn primary">
            Stop Debugging Blindly
          </Link>
        </div>
      </section>

      <footer className="section muted">
        Codize — an AI coding workflow trainer for student builders. Your workflow is
        incomplete; Codize helps you fix it.
      </footer>
    </div>
  );
}
