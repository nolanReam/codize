"use client";

import { useEffect, useState } from "react";

import Async from "@/components/Async";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { useWorkflowSection } from "@/lib/useWorkflowSection";
import type { VerificationCheckId, VerificationResult } from "@/lib/types";

const CHECKS: { id: VerificationCheckId; label: string; whenRelevant?: boolean }[] = [
  { id: "app_runs_locally", label: "The app runs locally" },
  { id: "smoke_test", label: "Ran at least one smoke test" },
  { id: "api_route_checked", label: "The relevant API route responds correctly" },
  { id: "ui_flow_checked", label: "The relevant UI flow works" },
  { id: "failure_case_tested", label: "Tested at least one failure case" },
  { id: "auth_boundary_checked", label: "Auth boundary checked", whenRelevant: true },
  { id: "secret_exposure_checked", label: "No secrets exposed in frontend/repo" },
  { id: "rls_wrong_user_checked", label: "Wrong-user access blocked (RLS)", whenRelevant: true },
];

const RESULTS: { value: VerificationResult; label: string }[] = [
  { value: "pass", label: "pass" },
  { value: "fail", label: "fail" },
  { value: "skipped", label: "skipped" },
  { value: "not_applicable", label: "n/a" },
];

type CheckState = { result: VerificationResult | ""; note: string };

// Verification Lab — manual verification evidence for v0.1. This proves the
// student performed reasonable checks, not that the code is fully correct.
export default function VerificationLabPage() {
  const wf = useWorkflowSection("verification");
  const [state, setState] = useState<Record<VerificationCheckId, CheckState>>(
    Object.fromEntries(CHECKS.map((c) => [c.id, { result: "", note: "" }])) as Record<
      VerificationCheckId,
      CheckState
    >
  );
  const [explanation, setExplanation] = useState("");

  useEffect(() => {
    if (!wf.stored) return;
    setState((prev) => {
      const next = { ...prev };
      for (const check of wf.stored?.checks ?? []) {
        next[check.check] = { result: check.result, note: check.note ?? "" };
      }
      return next;
    });
    setExplanation(wf.stored.explanation ?? "");
  }, [wf.stored]);

  if (wf.notReady) return <NotReady title="Verification Lab" />;

  async function save() {
    const checks = CHECKS.filter((c) => state[c.id].result !== "").map((c) => ({
      check: c.id,
      result: state[c.id].result as VerificationResult,
      note: state[c.id].note.trim() ? state[c.id].note.slice(0, 2000) : null,
    }));
    await wf.save({
      checks,
      explanation: explanation.trim() ? explanation.slice(0, 2000) : null,
    });
  }

  const recorded = CHECKS.filter((c) => state[c.id].result !== "").length;

  return (
    <>
      <h1 className="page-title">Verification Lab</h1>
      <p className="page-sub">
        Prove the code works instead of trusting the AI&rsquo;s word for it. These are manual
        checks — record what you actually did. A recorded &ldquo;fail&rdquo; is more valuable
        than a fake &ldquo;pass&rdquo;.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        {wf.phase && (
          <p className="muted" style={{ marginBottom: 14 }}>
            Verifying <strong>Phase {wf.phase.phase}: {wf.phase.phase_title}</strong> ·{" "}
            {recorded}/{CHECKS.length} checks recorded
          </p>
        )}

        <div className="card">
          <h3>Checks</h3>
          {CHECKS.map((check) => (
            <div key={check.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <div className="spread">
                <span>
                  {check.label}
                  {check.whenRelevant && <span className="muted"> (when relevant)</span>}
                </span>
                <div className="row">
                  {RESULTS.map((r) => (
                    <button
                      key={r.value}
                      className={`btn small${state[check.id].result === r.value ? " primary" : ""}`}
                      onClick={() =>
                        setState((prev) => ({
                          ...prev,
                          [check.id]: {
                            ...prev[check.id],
                            result: prev[check.id].result === r.value ? "" : r.value,
                          },
                        }))
                      }
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
              {state[check.id].result !== "" && (
                <input
                  type="text"
                  maxLength={2000}
                  style={{ marginTop: 8 }}
                  value={state[check.id].note}
                  onChange={(e) =>
                    setState((prev) => ({
                      ...prev,
                      [check.id]: { ...prev[check.id], note: e.target.value },
                    }))
                  }
                  placeholder="How did you check it? (e.g. 'curl POST /tasks with a missing title → 422')"
                />
              )}
            </div>
          ))}
        </div>

        <div className="card">
          <h3>What does this verification prove?</h3>
          <textarea
            rows={3}
            maxLength={2000}
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="In your own words: what do these checks demonstrate, and what's still unproven?"
          />
        </div>

        <SaveBar
          saving={wf.saving}
          saveError={wf.saveError}
          savedAt={wf.savedAt}
          onSave={save}
          label="Save verification"
        />
      </Async>
    </>
  );
}
