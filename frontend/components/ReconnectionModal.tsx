"use client";

import type { ReconnectionSummary } from "@/lib/types";

// Spec invariants: the modal renders before the workspace, shows the verbatim
// intake purpose in large text, and is dismissed ONLY by the button — no
// timer, no click-outside, no Escape. (No key/overlay handlers by design.)
export default function ReconnectionModal({
  summary,
  busy,
  onKeepBuilding,
}: {
  summary: ReconnectionSummary;
  busy: boolean;
  onKeepBuilding: () => void;
}) {
  return (
    <div className="modal-overlay">
      <div className="modal">
        <span className="pill accent">Welcome back</span>
        <p className="muted" style={{ marginTop: 14 }}>
          Remember — you&rsquo;re building this because:
        </p>
        <p className="purpose">&ldquo;{summary.intake_purpose}&rdquo;</p>

        <div className="kv">
          <span className="k">Where you left off</span>
          <span>
            Phase {summary.current_phase} — {summary.phase_title}
          </span>
        </div>
        <div className="kv">
          <span className="k">Core concept</span>
          <span>{summary.phase_reminder}</span>
        </div>
        {summary.last_gate_summary && (
          <div className="kv">
            <span className="k">Last gate</span>
            <span>{summary.last_gate_summary}</span>
          </div>
        )}
        {summary.incomplete_tasks.length > 0 && (
          <div style={{ margin: "14px 0" }}>
            <p className="muted">Still open in this phase:</p>
            {summary.incomplete_tasks.slice(0, 5).map((t) => (
              <div className="task" key={t.task_id}>
                <span className="tag">{t.task_id}</span>
                <span>{t.description}</span>
              </div>
            ))}
          </div>
        )}
        <p style={{ margin: "16px 0 20px" }}>{summary.next_action}</p>

        <button className="btn primary" style={{ width: "100%" }} disabled={busy} onClick={onKeepBuilding}>
          {busy ? "…" : "Let's keep building"}
        </button>
      </div>
    </div>
  );
}
