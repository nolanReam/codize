"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import AdaptiveStepGuide from "@/components/AdaptiveStepGuide";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { containsSecretMarker, useDraft } from "@/lib/drafts";
import {
  buildImportPayload,
  CONTENT_MAX,
  EMPTY_FORM,
  formFromStored,
  GIT_DIFF_EXPLANATION,
  type ImportForm,
  PAGE_INTRO,
  PAGE_REASSURANCE,
  PAGE_TITLE,
  saveBlocker,
  SECRET_REMINDER,
  SOURCE_OPTIONS,
  sourceOption,
  SUMMARY_MAX,
  TOOL_NAME_MAX,
} from "@/lib/implementationImport";
import { useWorkflowSection } from "@/lib/useWorkflowSection";

// "Bring Back What Changed" — the step between using an external AI tool
// and reviewing its work. Storage only: what's saved is the student's own
// record (self-reported, never verified); Codize runs no analysis on it.
export default function BringBackPage() {
  const wf = useWorkflowSection("implementation_import");
  const [form, setForm] = useState<ImportForm>(EMPTY_FORM);
  const [dirty, setDirty] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  // Prefill from the saved artifact once loaded (and after each save).
  useEffect(() => {
    if (!wf.stored) return;
    setForm(formFromStored(wf.stored));
  }, [wf.stored]);

  // Unsaved-draft persistence (M13E.2 pattern): backend data prefills first,
  // then the local draft overlays once; a successful save clears it.
  const draft = useDraft<ImportForm>(
    wf.phase ? `implementation_import:${wf.phase.phase}` : null
  );
  const draftApplied = useRef(false);
  useEffect(() => {
    if (wf.loading || !draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) {
      setForm({ ...EMPTY_FORM, ...draft.restored });
      setDirty(true);
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
    saveDraft(form);
  }, [form, saveDraft]);

  if (wf.notReady) return <NotReady title={PAGE_TITLE} />;

  // User edits go through set(): they mark the form dirty and retire the
  // saved-confirmation notice. Prefills use setForm directly and do neither.
  const set = <K extends keyof ImportForm>(key: K, value: ImportForm[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
    setJustSaved(false);
  };

  async function save() {
    const ok = await wf.save(buildImportPayload(form));
    if (ok) {
      skipDraftEcho.current = true;
      draft.clear();
      setDirty(false);
      setJustSaved(true);
    }
  }

  const selected = sourceOption(form.sourceKind);
  const mainIsContent = selected.contentLabel != null;
  const blocker = saveBlocker(form);
  // The drafts layer refuses to keep credential-like text on this device —
  // say so instead of failing silently (server save still works after cleanup).
  const draftBlocked = dirty && containsSecretMarker(JSON.stringify(form));

  const contentField = (label: string, hint?: string) => (
    <div className="field">
      <label htmlFor="import-content">{label}</label>
      <textarea
        id="import-content"
        className="code"
        rows={mainIsContent ? 12 : 5}
        value={form.content}
        onChange={(e) => set("content", e.target.value)}
        placeholder="Paste it exactly as you have it — line breaks, indentation, and Markdown are kept."
        spellCheck={false}
      />
      <p className="hint" style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <span>{hint ?? "Pasted exactly as-is — nothing is reformatted."}</span>
        <span aria-label={`${form.content.length} of ${CONTENT_MAX} characters used`}>
          {form.content.length.toLocaleString()} / {CONTENT_MAX.toLocaleString()}
        </span>
      </p>
    </div>
  );

  const changedFilesField = (emphasized: boolean) => (
    <div className="field">
      <label htmlFor="import-files">
        Changed files{emphasized ? "" : " (optional)"}
      </label>
      <textarea
        id="import-files"
        className="code"
        rows={emphasized ? 8 : 3}
        value={form.changedFilesText}
        onChange={(e) => set("changedFilesText", e.target.value)}
        placeholder={"app/routes/tasks.py\napp/models/task.py\nfrontend/components/TaskCard.tsx"}
        spellCheck={false}
      />
      <p className="hint">
        One file per line — list the ones you know about; it doesn&rsquo;t have to be complete.
      </p>
    </div>
  );

  const summaryField = (emphasized: boolean) => (
    <div className="field">
      <label htmlFor="import-summary">What changed?{emphasized ? "" : " (optional)"}</label>
      <textarea
        id="import-summary"
        rows={emphasized ? 6 : 3}
        maxLength={SUMMARY_MAX}
        value={form.summary}
        onChange={(e) => set("summary", e.target.value)}
        placeholder="e.g. AI added task ownership checks and changed the task route — I haven't reviewed all of it yet."
      />
      <p className="hint">
        Describe the result in your own words. It&rsquo;s okay if you&rsquo;re still unsure.
      </p>
    </div>
  );

  return (
    <>
      <h1 className="page-title">{PAGE_TITLE}</h1>
      <p className="page-sub">
        {PAGE_INTRO} <strong>{PAGE_REASSURANCE}</strong>
      </p>
      <AdaptiveStepGuide stage="import" />

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
            {wf.phase && (
              <p className="muted" style={{ marginBottom: 14 }}>
                For <strong>Phase {wf.phase.phase}: {wf.phase.phase_title}</strong>
              </p>
            )}

            <div className="card primary">
              <fieldset className="kind-picker">
                <legend>What are you bringing back?</legend>
                <div className="chips" style={{ marginTop: 4 }}>
                  {SOURCE_OPTIONS.map((opt) => (
                    <label
                      key={opt.value}
                      className={`chip${form.sourceKind === opt.value ? " active" : ""}`}
                    >
                      <input
                        type="radio"
                        name="source-kind"
                        value={opt.value}
                        checked={form.sourceKind === opt.value}
                        onChange={() => set("sourceKind", opt.value)}
                      />
                      {opt.label}
                    </label>
                  ))}
                </div>
                <p className="hint">{selected.description}</p>
              </fieldset>

              {form.sourceKind === "git_diff" && (
                <details className="help">
                  <summary>What is a git diff?</summary>
                  <div className="help-body">
                    <p>{GIT_DIFF_EXPLANATION}</p>
                  </div>
                </details>
              )}

              <div style={{ marginTop: 10 }}>
                {selected.contentLabel != null && contentField(selected.contentLabel)}
                {form.sourceKind === "changed_files" && changedFilesField(true)}
                {form.sourceKind === "manual_summary" && summaryField(true)}
              </div>
            </div>

            <details className="help" style={{ margin: "12px 0" }}>
              <summary>Add more detail (optional)</summary>
              <div className="help-body">
                {!mainIsContent &&
                  contentField(
                    "Paste the implementation material (optional)",
                    "Anything else you brought back — an AI response, code, a diff."
                  )}
                {form.sourceKind !== "changed_files" && changedFilesField(false)}
                {form.sourceKind !== "manual_summary" && summaryField(false)}
                <div className="field">
                  <label htmlFor="import-tool">AI tool used (optional)</label>
                  <input
                    id="import-tool"
                    type="text"
                    maxLength={TOOL_NAME_MAX}
                    value={form.toolName}
                    onChange={(e) => set("toolName", e.target.value)}
                    placeholder="ChatGPT, Claude, Cursor, Gemini, GitHub Copilot…"
                  />
                </div>
              </div>
            </details>

            {justSaved && (
              <div className="notice ok" role="status">
                <strong>Implementation material saved.</strong> It&rsquo;s part of this phase&rsquo;s
                record now.
                <div className="row" style={{ marginTop: 8 }}>
                  <Link href="/app/phase/change-map" style={{ color: "inherit", fontWeight: 700 }}>
                    Continue Change Map →
                  </Link>
                  <Link href="/app#current-work" style={{ color: "inherit" }}>
                    Back to current work
                  </Link>
                </div>
              </div>
            )}

            <p className="hint" style={{ marginTop: 12 }}>{SECRET_REMINDER}</p>
            {draftBlocked && (
              <p className="hint" style={{ color: "var(--warn)" }}>
                Something here looks like a real key, so this draft isn&rsquo;t being kept on this
                device — remove it before saving.
              </p>
            )}
            {dirty && !draftBlocked && !justSaved && (
              <p className="hint">
                Draft saved on this device — <strong>{wf.stored ? "Save changes" : "Save implementation material"}</strong>{" "}
                stores it to your project{wf.stored ? ", replacing this phase's previous save" : ""}.
              </p>
            )}

            <SaveBar
              saving={wf.saving}
              saveError={wf.saveError}
              savedAt={wf.savedAt}
              onSave={save}
              disabled={blocker != null}
              label={wf.stored ? "Save changes" : "Save implementation material"}
            />
            {blocker && <p className="hint">{blocker}</p>}
          </div>

          <aside className="ws-rail" aria-label="Guidance">
            <GuideCard title="Why this step?">
              <p>
                The habit that keeps you in control: scope a prompt, use your AI tool, then bring
                the result back <em>before</em> building on it. Whatever you save here feeds your
                review and your Defense Report.
              </p>
            </GuideCard>
            <GuideCard title="Already stuck?">
              <p>
                Bring back the latest AI response, diff, changed code, or your own notes — even a
                rough record is a starting point for rebuilding a clear picture.
              </p>
            </GuideCard>
            <GuideCard title="The fine print">
              <p>
                This is your own record — Codize doesn&rsquo;t run, verify, or trust any of it, and
                saving never ticks a build task. One record per phase: saving replaces your
                previous save here.
              </p>
              <p>
                Typing survives tab switches as a local draft; anything that looks like a real API
                key is rejected before it&rsquo;s stored.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
