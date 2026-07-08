// "What you are about to do" — the whole Codize loop in eight plain lines
// (M13E.3, pilot feedback: the most confusing part was not knowing what the
// workflow would be before starting). Collapsed by default so it costs one
// line of screen space; no backend calls, no tutorial takeover.
export default function LoopOverview({ defaultOpen = false }: { defaultOpen?: boolean }) {
  return (
    <details className="help" open={defaultOpen}>
      <summary>What you&rsquo;ll actually do — the whole loop in 8 lines</summary>
      <div className="help-body">
        <ol style={{ margin: "6px 0", paddingLeft: 20 }}>
          <li>Build a better prompt (in Codize).</li>
          <li>Use your AI tool — ChatGPT, Claude, Cursor — outside Codize.</li>
          <li>Bring the result back.</li>
          <li>Note what the AI changed (Review).</li>
          <li>Save one piece of proof (Evidence).</li>
          <li>Check it actually works (Verify).</li>
          <li>Explain what you built in your own words (Defense).</li>
          <li>Export a report you can show anyone.</li>
        </ol>
        <p className="muted" style={{ margin: "6px 0 0" }}>
          Repeat per phase. You never have to do all of it at once.
        </p>
      </div>
    </details>
  );
}
