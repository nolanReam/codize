"use client";

import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { useDraft } from "@/lib/drafts";
import { useWorkflowSection } from "@/lib/useWorkflowSection";
import type { EvidenceEntry, EvidenceKind } from "@/lib/types";

const KINDS: { value: EvidenceKind; label: string; placeholder: string }[] = [
  { value: "repo_url", label: "Repo URL", placeholder: "https://github.com/you/project" },
  { value: "commit_hash", label: "Commit hash", placeholder: "a1b2c3d" },
  { value: "changed_files", label: "Changed files", placeholder: "app/routes/tasks.py, app/models.py" },
  { value: "terminal_output", label: "Terminal output", placeholder: "paste the relevant output" },
  { value: "test_output", label: "Test output", placeholder: "3 passed in 0.21s" },
  { value: "screenshot_note", label: "Screenshot note/link", placeholder: "screenshot of the working flow — link or description" },
  { value: "app_url", label: "App URL", placeholder: "https://myapp.example.com" },
  { value: "api_response", label: "API response example", placeholder: '{"id": 1, "status": "created"}' },
  { value: "note", label: "Note", placeholder: "anything else that proves the work" },
];

// Evidence Panel — manual, self-reported evidence for v0.1. Nothing is
// fetched or verified automatically; honesty is part of the training.
export default function EvidencePanelPage() {
  const wf = useWorkflowSection("evidence");
  const [entries, setEntries] = useState<EvidenceEntry[]>([]);
  const [summary, setSummary] = useState("");
  const [kind, setKind] = useState<EvidenceKind>("repo_url");
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
      setKind(draft.restored.kind ?? "repo_url");
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
        Attach proof of the work: repo links, commits, outputs, screenshots-as-notes. Manual for
        v0.1 — Codize doesn&rsquo;t fetch or verify anything for you, and pasting a real API key
        is rejected on save.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
        {wf.phase && (
          <p className="muted" style={{ marginBottom: 14 }}>
            Evidence for <strong>Phase {wf.phase.phase}: {wf.phase.phase_title}</strong>
          </p>
        )}

        <div className="card">
          <h3>Add evidence</h3>
          {formError && <div className="notice error">{formError}</div>}
          <div className="field">
            <label>Type</label>
            <select value={kind} onChange={(e) => setKind(e.target.value as EvidenceKind)}>
              {KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Content</label>
            <textarea
              rows={4}
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
          <button className="btn" onClick={addEntry} disabled={!content.trim()}>
            Add entry
          </button>
        </div>

        <div className="card">
          <h3>Collected evidence ({entries.length}/20)</h3>
          {entries.length === 0 && <p className="empty">Nothing attached yet.</p>}
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
            <GuideCard title="What counts as evidence?">
              <p>
                Anything that would convince a skeptical teacher the work is real: a repo link, a
                commit hash, test output, a terminal paste, a screenshot description.
              </p>
            </GuideCard>
            <GuideCard title="Small proofs beat big claims">
              <ul>
                <li>One passing test output &gt; &ldquo;everything works&rdquo;.</li>
                <li>A commit hash pins <em>when</em> you did it.</li>
                <li>Failed output is evidence too — of honest verification.</li>
              </ul>
            </GuideCard>
            <GuideCard title="Your text is kept">
              <p>
                Entries you add and text you type survive switching tabs as a local draft — press{" "}
                <strong>Save evidence</strong> to store them to your project.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
