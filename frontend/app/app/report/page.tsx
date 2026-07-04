"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import { ApiError, getEvaluation, getIntakeStatus, getWorkflow } from "@/lib/api";
import type { Evaluation, WorkflowSections } from "@/lib/types";

type RowStatus = "ready" | "partial" | "missing";

function StatusPill({ status }: { status: RowStatus }) {
  const map: Record<RowStatus, { label: string; cls: string }> = {
    ready: { label: "collected", cls: "ok" },
    partial: { label: "in progress", cls: "warn" },
    missing: { label: "not started", cls: "" },
  };
  const { label, cls } = map[status];
  return <span className={`pill ${cls}`}>{label}</span>;
}

// Project Defense Report — M13C.1 placeholder. It shows, honestly, which
// source materials the report will assemble from and whether each exists yet.
// The assembled/exportable report itself is M13C.2.
export default function ReportPage() {
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [purpose, setPurpose] = useState<string | null>(null);
  const [sections, setSections] = useState<WorkflowSections | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preActive, setPreActive] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPreActive(false);
    try {
      const ev = await getEvaluation();
      if (
        ev.state === "not_started" ||
        ev.state === "intake_needed" ||
        ev.state === "roadmap_needed"
      ) {
        setPreActive(true);
        setLoading(false);
        return;
      }
      setEvaluation(ev);
      const [workflow, intake] = await Promise.allSettled([
        getWorkflow(ev.current_phase ?? 1),
        getIntakeStatus(),
      ]);
      if (workflow.status === "fulfilled") setSections(workflow.value.sections);
      if (intake.status === "fulfilled") setPurpose(intake.value.answers?.purpose ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load report status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (preActive) {
    return (
      <>
        <h1 className="page-title">Project Defense Report</h1>
        <div className="notice info">
          Your defense report assembles from your project as you build it. Start by
          finishing intake and generating your roadmap.
        </div>
        <Link href="/app/intake" className="btn primary">
          Go to intake
        </Link>
      </>
    );
  }

  const gateStatus: RowStatus = evaluation?.recent_gate
    ? evaluation.recent_gate.outcome === "passed"
      ? "ready"
      : "partial"
    : "missing";

  const ROWS: { label: string; detail: string; status: RowStatus }[] = evaluation
    ? [
        {
          label: "Project & intake",
          detail: purpose ? `“${purpose}”` : "Your project purpose and intake answers.",
          status: purpose ? "ready" : "partial",
        },
        {
          label: "Current phase",
          detail: `Phase ${evaluation.current_phase} — ${evaluation.phase_title}`,
          status: "ready",
        },
        {
          label: "Prompt Builder",
          detail: "The scoped prompt you engineered for this phase.",
          status: sections?.prompt_builder ? "ready" : "missing",
        },
        {
          label: "Review Board",
          detail: "What the AI changed, and what you accepted, rejected, or edited.",
          status: sections?.review_board ? "ready" : "missing",
        },
        {
          label: "Evidence",
          detail: "Repo, commits, outputs, and screenshots proving the work.",
          status: sections?.evidence ? "ready" : "missing",
        },
        {
          label: "Verification",
          detail: "The manual checks you ran to prove behavior.",
          status: sections?.verification ? "ready" : "missing",
        },
        {
          label: "Gate outcome",
          detail:
            evaluation.recent_gate?.summary ??
            "Your Interrogation Gate result for this phase.",
          status: gateStatus,
        },
        {
          label: "Evaluation summary",
          detail: evaluation.next_action,
          status: "ready",
        },
      ]
    : [];

  const collected = ROWS.filter((r) => r.status === "ready").length;

  return (
    <>
      <div className="spread">
        <div>
          <h1 className="page-title">Project Defense Report</h1>
          <p className="page-sub">
            Everything you&rsquo;d need to stand behind this project — in a demo, an
            interview, or when it breaks. Assembled from your real workflow, not a summary
            you write after the fact.
          </p>
        </div>
        {evaluation && (
          <span className="pill accent">
            {collected}/{ROWS.length} sources
          </span>
        )}
      </div>

      <Async loading={loading} error={error} onRetry={load}>
        <div className="card">
          <h3>What the report will assemble from</h3>
          {ROWS.map((row) => (
            <div
              key={row.label}
              style={{ padding: "11px 0", borderBottom: "1px solid var(--border)" }}
            >
              <div className="spread">
                <strong>{row.label}</strong>
                <StatusPill status={row.status} />
              </div>
              <p className="muted" style={{ marginTop: 4, overflowWrap: "anywhere" }}>
                {row.detail}
              </p>
            </div>
          ))}
        </div>

        <div className="card" style={{ borderColor: "var(--border-strong)" }}>
          <h3>Full report — M13C.2</h3>
          <p className="muted">
            The generated, shareable Project Defense Report lands in the next milestone. It
            will compile the sources above across every phase into a single document you can
            take into an interview. For now, keep each phase&rsquo;s workflow complete — a
            report is only as strong as the evidence behind it.
          </p>
          <div className="row" style={{ marginTop: 12 }}>
            <Link href="/app/phase" className="btn">
              Back to phase workspace
            </Link>
            <Link href="/app" className="btn">
              Cockpit
            </Link>
          </div>
        </div>
      </Async>
    </>
  );
}
