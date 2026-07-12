"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { useDraft } from "@/lib/drafts";
import { useWorkflowSection } from "@/lib/useWorkflowSection";
import type { EvidenceEntry, EvidenceKind } from "@/lib/types";

// The five everyday kinds are always visible as tap-to-pick chips; the more
// technical kinds live behind "More types" (M13E.3 — the panel read as a
// legal form to the first tester). Same backend enum, friendlier surface.
const KINDS: { value: EvidenceKind; label: string; placeholder: string; primary?: boolean }[] = [
  { value: "screenshot_note", label: "Screenshot", placeholder: "what the screenshot shows — link or description", primary: true },
  { value: "terminal_output", label: "Terminal output", placeholder: "paste the relevant output", primary: true },
  { value: "test_output", label: "Test result", placeholder: "3 passed in 0.21s", primary: true },
  { value: "changed_files", label: "Files you changed", placeholder: "app/routes/tasks.py, app/models.py", primary: true },
  { value: "note", label: "Short note", placeholder: "anything that shows the work is real", primary: true },
  { value: "repo_url", label: "Repo URL", placeholder: "https://github.com/you/project" },
  { value: "commit_hash", label: "Commit hash", placeholder: "a1b2c3d" },
  { value: "app_url", label: "App URL", placeholder: "https://myapp.example.com" },
  { value: "api_response", label: "API response", placeholder: '{"id": 1, "status": "created"}' },
];

// Evidence Panel — manual, self-reported evidence for v0.1. Nothing is
// fetched or verified automatically; honesty is part of the training.
export default function EvidencePanelPage() {
  const wf = useWorkflowSection("evidence");
  const [entries, setEntries] = useState<EvidenceEntry[]>([]);
  const [summary, setSummary] = useState("");
  const [kind, setKind] = useState<EvidenceKind>("screenshot_note");
  const [content, setContent] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!wf.stored) return;
    setEntries(wf.stored.entries ?? []);
    setSummary(wf.stored.summary ?? "");
  }, [wf.stored]);

  // Unsaved-draft persistence (M13E.2): backend data prefills first, then the
  // local draft (including a half-typed "Add evidence" box) overlays once.
  type EvidenceDraft = {
    entries: EvidenceEntry[];
    summary: string;
    kind: EvidenceKind;
    content: string;
  };
  const draft = useDraft<EvidenceDraft>(wf.phase ? `evidence:${wf.phase.phase}` : null);
  const draftApplied = useRef(false);
  useEffect(() => {
    if (wf.loading || !draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) {
      setEntries(draft.restored.entries ?? []);
      setSummary(draft.restored.summary ?? "");
      setKind(draft.restored.kind ?? "screenshot_note");
      setContent(draft.restored.content ?? "");
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
    saveDraft({ entries, summary, kind, content });
  }, [entries, summary, kind, content, saveDraft]);

  if (wf.notReady) return <NotReady title="Evidence Panel" />;

  function addEntry() {
    const trimmed = content.trim();
    if (!trimmed) return;
    if (entries.length >= 20) {
      setFormError("Evidence is capped at 20 entries per phase — remove one first.");
      return;
    }
    setFormError(null);
    setEntries([...entries, { kind, content: trimmed.slice(0, 8000) }]);
    setContent("");
  }

  async function save() {
    const ok = await wf.save({
      entries,
      summary: summary.trim() ? summary.slice(0, 2000) : null,
    });
    if (ok) {
      skipDraftEcho.current = true;
      draft.clear();
    }
  }

  return (
    <>
      <h1 className="page-title">Evidence Panel</h1>
      <p className="page-sub">
        Proof you checked something — <strong>one small piece is enough</strong> for this phase.
        It goes straight into your Defense Report.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
        {wf.phase && (
          <p className="muted" style={{ marginBottom: 14 }}>
            Evidence for <strong>Phase {wf.phase.phase}: {wf.phase.phase_title}</strong>
          </p>
        )}

        <div className="card primary">
          <h3>Add one piece of proof</h3>
          {formError && <div className="notice error">{formError}</div>}
          <div className="chips" style={{ marginTop: 0 }}>
            {KINDS.filter((k) => k.primary).map((k) => (
              <button
                key={k.value}
                type="button"
                className={`chip${kind === k.value ? " active" : ""}`}
                onClick={() => setKind(k.value)}
              >
                {k.label}
              </button>
            ))}
          </div>
          <details className="help">
            <summary>More types</summary>
            <div className="help-body">
              <div className="chips" style={{ marginTop: 0 }}>
                {KINDS.filter((k) => !k.primary).map((k) => (
                  <button
                    key={k.value}
                    type="button"
                    className={`chip${kind === k.value ? " active" : ""}`}
                    onClick={() => setKind(k.value)}
                  >
                    {k.label}
                  </button>
                ))}
              </div>
            </div>
          </details>
          <div className="field" style={{ marginTop: 10 }}>
            <label>{KINDS.find((k) => k.value === kind)?.label}</label>
            <textarea
              rows={3}
              maxLength={8000}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={KINDS.find((k) => k.value === kind)?.placeholder}
            />
            {kind === "repo_url" || kind === "app_url" ? (
              <p className="hint">Must be an http(s) URL.</p>
            ) : kind === "commit_hash" ? (
              <p className="hint">7–40 hex characters, e.g. a1b2c3d.</p>
            ) : null}
          </div>
          <div className="row">
            <button className="btn primary" onClick={addEntry} disabled={!content.trim()}>
              Add entry
            </button>
            <span className="muted">
              Nothing yet? That&rsquo;s fine —{" "}
              <Link href="/app/phase" className="mono" style={{ fontSize: 12 }}>
                skip for now →
              </Link>{" "}
              and come back after your next AI session.
            </span>
          </div>
        </div>

        <div className="card">
          <h3>Collected evidence ({entries.length}/20)</h3>
          {entries.length === 0 && (
            <p className="empty">
              Nothing attached yet — add one piece above and it shows up in your Defense Report.
            </p>
          )}
          {entries.map((entry, idx) => (
            <div className="task" key={idx}>
              <span className="tag">{entry.kind}</span>
              <span className="mono" style={{ flex: 1, overflowWrap: "anywhere" }}>
                {entry.content.length > 300 ? `${entry.content.slice(0, 300)}…` : entry.content}
              </span>
              <button
                className="btn small"
                onClick={() => setEntries(entries.filter((_, i) => i !== idx))}
              >
                remove
              </button>
            </div>
          ))}
          <div className="field" style={{ marginTop: 14 }}>
            <label>What does this evidence show, in one or two sentences?</label>
            <textarea
              rows={2}
              maxLength={2000}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="The endpoint works end-to-end: the test output shows the create + fetch cycle passing."
            />
          </div>
        </div>

        <SaveBar
          saving={wf.saving}
          saveError={wf.saveError}
          savedAt={wf.savedAt}
          onSave={save}
          label="Save evidence"
        />
          </div>

          <aside className="ws-rail" aria-label="Guidance">
            <GuideCard title="Why bother?">
              <p>
                Evidence turns &ldquo;it works, trust me&rdquo; into something you can show a
                teacher or interviewer. One passing test output beats &ldquo;everything
                works&rdquo; — and failed output counts too: it proves honest checking.
              </p>
            </GuideCard>
            <GuideCard title="The fine print">
              <p>
                Manual for v0.1 — Codize doesn&rsquo;t fetch or verify anything for you, and it
                records what you <em>did</em>, not that the code is correct. Pasting a real API
                key is rejected on save.
              </p>
              <p>
                Your typing survives tab switches as a local draft; <strong>Save evidence</strong>{" "}
                stores it to your project.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
