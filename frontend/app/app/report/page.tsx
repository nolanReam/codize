"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import DefenseReportView from "@/components/DefenseReportView";
import AdaptiveStepGuide from "@/components/AdaptiveStepGuide";
import { ApiError, getDefenseReport, getEvaluation } from "@/lib/api";
import { buildReportMarkdown, reportIsReady } from "@/lib/report";
import type { DefenseReport } from "@/lib/types";

function phaseFromSearch(search: string): number | null {
  const value = new URLSearchParams(search).get("phase");
  if (!value || !/^\d+$/.test(value)) return null;
  const phase = Number(value);
  return Number.isSafeInteger(phase) && phase > 0 ? phase : null;
}

function safeReportError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Defense Report is temporarily unavailable.";
  if (error.status === 401) return error.message;
  if (error.status === 404) return "That phase is not available for this project.";
  if (error.status === 409) return "This project is not ready for a Defense Report yet.";
  return "Defense Report is temporarily unavailable.";
}

export default function ReportPage() {
  const [report, setReport] = useState<DefenseReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preActive, setPreActive] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPreActive(false);
    setCopied(false);
    try {
      const evaluation = await getEvaluation();
      if (
        evaluation.state === "not_started" ||
        evaluation.state === "intake_needed" ||
        evaluation.state === "roadmap_needed"
      ) {
        setPreActive(true);
        setReport(null);
        return;
      }
      const requestedPhase = phaseFromSearch(window.location.search);
      const phaseNumber = requestedPhase ?? evaluation.current_phase ?? 1;
      setReport(await getDefenseReport(phaseNumber));
    } catch (loadError) {
      setReport(null);
      setError(safeReportError(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function copyMarkdown() {
    if (!report || !reportIsReady(report)) return;
    try {
      await navigator.clipboard.writeText(buildReportMarkdown(report));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  function downloadMarkdown() {
    if (!report || !reportIsReady(report)) return;
    const blob = new Blob([buildReportMarkdown(report)], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `codize-defense-report-phase-${report.phase_number}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const ready = report ? reportIsReady(report) : false;

  return (
    <>
      <div className="spread report-page-heading">
        <div>
          <h1 className="page-title">Defense Report</h1>
          <p className="page-sub">
            Keep a clear record of what changed, what you reviewed, what you tested, what
            Evidence you recorded, and how you explained the project.
          </p>
          <p className="report-page-trust">
            Workflow records and Evidence are student-recorded or student-confirmed.
            Verification results are not independent proof.
          </p>
        </div>
        {ready && (
          <div className="row report-export-actions" aria-label="Export Defense Report">
            <button className="btn primary" type="button" onClick={copyMarkdown}>
              {copied ? "Copied ✓" : "Copy as Markdown"}
            </button>
            <button className="btn" type="button" onClick={downloadMarkdown}>
              Download .md
            </button>
          </div>
        )}
      </div>
      <AdaptiveStepGuide stage="report" />

      {copied && (
        <p className="sr-only" role="status" aria-live="polite">
          Defense Report copied as Markdown.
        </p>
      )}

      {loading && (
        <div className="report-loading" role="status" aria-live="polite">
          <span className="loading" aria-hidden="true">
            loading
          </span>
          <p>Preparing your Defense Report…</p>
        </div>
      )}

      {!loading && error && (
        <div className="notice error report-error" role="alert">
          <strong>{error}</strong>
          <p>Your project navigation is still available. Retry the Report when you&rsquo;re ready.</p>
          <div className="row">
            <button className="btn small" type="button" onClick={load}>
              Retry Report
            </button>
            <Link href="/app" className="btn small">
              Project Home
            </Link>
          </div>
        </div>
      )}

      {!loading && preActive && (
        <div className="card primary report-prerequisite">
          <h2>Build your project record first</h2>
          <p>
            Finish intake and create the roadmap before Codize can prepare a phase Defense
            Report.
          </p>
          <Link href="/app/intake" className="btn primary">
            Go to intake
          </Link>
        </div>
      )}

      {!loading && !error && report && !ready && (
        <div className="card primary report-prerequisite">
          <p className="report-kicker">Phase {report.phase_number}</p>
          <h2>
            {report.defense.state === "in_progress"
              ? "Finish Project Defense first"
              : "Start Project Defense first"}
          </h2>
          <p>
            {report.defense.state === "in_progress"
              ? "This Defense attempt is still active. Complete the remaining questions before viewing its Report."
              : "A Defense Report becomes available after a completed Project Defense attempt for this phase."}
          </p>
          <div className="row">
            <Link href="/app/gate" className="btn primary">
              {report.defense.state === "in_progress"
                ? "Continue Project Defense"
                : "Start Project Defense"}
            </Link>
            <Link href="/app" className="btn">
              Project Home
            </Link>
          </div>
        </div>
      )}

      {!loading && !error && report && ready && <DefenseReportView report={report} />}
    </>
  );
}
