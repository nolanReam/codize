"use client";

import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { useDraft } from "@/lib/drafts";
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

// The note question depends on the result (M13E.2, pilot issue 5): only a
// pass asks "how was it checked" — a skipped/N/A check was, by definition,
// not checked, so its note is an optional reason and never required.
const NOTE_PROMPTS: Record<
  VerificationResult,
  { label: string; placeholder: string }
> = {
  pass: {
    label: "How did you check it?",
    placeholder: "e.g. curl POST /tasks with a missing title → 422",
  },
  fail: {
    label: "What failed, or what needs fixing?",
    placeholder: "e.g. the route 500s when title is missing — needs validation",
  },
  skipped: {
    label: "Why are you skipping it for now? (optional)",
    placeholder: "e.g. will check this after the next feature lands",
  },
  not_applicable: {
    label: "Why doesn't this apply? (optional)",
    placeholder: "e.g. this phase has no UI yet",
  },
};

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

  // Unsaved-draft persistence (M13E.2): backend data prefills first, then any
  // local draft overlays once.
  type VerifyDraft = { state: Record<VerificationCheckId, CheckState>; explanation: string };
  const draft = useDraft<VerifyDraft>(wf.phase ? `verification:${wf.phase.phase}` : null);
  const draftApplied = useRef(false);
  useEffect(() => {
    if (wf.loading || !draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) {
      setState((prev) => ({ ...prev, ...draft.restored?.state }));
      setExplanation(draft.restored.explanation ?? "");
    }
  }, [wf.loading, draft.ready, draft.restored]);
  // A successful save re-prefills state from the stored artifact, which would
  // immediately re-write the just-cleared draft — skip that one echo.
  const skipDraftEcho = useRef(false);
  const saveDraft = draft.save;
  useEffect(() => {
    if (!draftApplied.current) return;
    if (skipDraftEcho.current) {
      skipDraftEcho.current = false;
      return;
    }
    saveDraft({ state, explanation });
  }, [state, explanation, saveDraft]);

  if (wf.notReady) return <NotReady title="Verification Lab" />;

  async function save() {
    const checks = CHECKS.filter((c) => state[c.id].result !== "").map((c) => ({
      check: c.id,
      result: state[c.id].result as VerificationResult,
      note: state[c.id].note.trim() ? state[c.id].note.slice(0, 2000) : null,
    }));
    const ok = await wf.save({
      checks,
      explanation: explanation.trim() ? explanation.slice(0, 2000) : null,
    });
    if (ok) {
      skipDraftEcho.current = true;
      draft.clear();
    }
  }

  const recorded = CHECKS.filter((c) => state[c.id].result !== "").length;

  return (
    <>
      <h1 className="page-title">Verification Lab</h1>
      <p className="page-sub">
        A quick honesty check, not homework — mark what you actually tried. It lands in your
        Defense Report.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
        {wf.phase && (
          <p className="muted" style={{ marginBottom: 14 }}>
            Phase {wf.phase.phase}: {wf.phase.phase_title} · {recorded}/{CHECKS.length} recorded ·
            you can save any time and come back later
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
                <div style={{ marginTop: 8 }}>
                  <p className="hint" style={{ margin: "0 0 4px" }}>
                    {NOTE_PROMPTS[state[check.id].result as VerificationResult].label}
                  </p>
                  <input
                    type="text"
                    maxLength={2000}
                    value={state[check.id].note}
                    onChange={(e) =>
                      setState((prev) => ({
                        ...prev,
                        [check.id]: { ...prev[check.id], note: e.target.value },
                      }))
                    }
                    placeholder={
                      NOTE_PROMPTS[state[check.id].result as VerificationResult].placeholder
                    }
                  />
                  {(state[check.id].result === "skipped" ||
                    state[check.id].result === "not_applicable") && (
                    <p className="hint" style={{ margin: "4px 0 0" }}>
                      {state[check.id].result === "skipped"
                        ? "Recorded as “skipped for now” — no evidence needed."
                        : "Recorded as “doesn't apply” — no evidence needed."}
                    </p>
                  )}
                </div>
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
          </div>

          <aside className="ws-rail" aria-label="Guidance">
            <GuideCard title="What the four results mean">
              <ul>
                <li>
                  <strong>pass</strong> — you checked it and it worked. Say how.
                </li>
                <li>
                  <strong>fail</strong> — you checked it and it didn&rsquo;t. Say what broke.
                </li>
                <li>
                  <strong>skipped</strong> — not checked yet. That&rsquo;s allowed; no evidence
                  needed.
                </li>
                <li>
                  <strong>n/a</strong> — doesn&rsquo;t apply to this phase. Also fine.
                </li>
              </ul>
            </GuideCard>
            <GuideCard title="A recorded fail is progress">
              <p>
                The report labels skipped and n/a honestly — nobody expects all eight checks every
                phase. A real &ldquo;fail&rdquo; with notes is worth more than a fake
                &ldquo;pass&rdquo;.
              </p>
            </GuideCard>
            <GuideCard title="Your text is kept">
              <p>
                Results and notes survive switching tabs as a local draft — press{" "}
                <strong>Save verification</strong> to store them to your project.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
