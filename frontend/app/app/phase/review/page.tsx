"use client";

import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { useDraft } from "@/lib/drafts";
import { useWorkflowSection } from "@/lib/useWorkflowSection";

const FIELDS: { key: FieldKey; label: string; placeholder: string }[] = [
  { key: "ai_generated", label: "What did the AI generate?", placeholder: "the POST /tasks route and the Task model" },
  { key: "accepted", label: "What did you accept?", placeholder: "the route handler, mostly as-is" },
  { key: "rejected", label: "What did you reject?", placeholder: "an unrequested rewrite of the auth middleware" },
  { key: "edited_manually", label: "What did you edit manually?", placeholder: "renamed fields, tightened the validation" },
  { key: "ai_assumptions", label: "What assumptions did the AI make?", placeholder: "it assumed every task has a due date" },
  { key: "least_confident", label: "What are you least confident about?", placeholder: "the query in list_tasks — I couldn't fully trace it" },
  { key: "out_of_scope_changes", label: "Did the AI change anything outside the requested scope?", placeholder: "it reformatted imports across three files" },
];

type FieldKey =
  | "ai_generated"
  | "accepted"
  | "rejected"
  | "edited_manually"
  | "ai_assumptions"
  | "least_confident"
  | "out_of_scope_changes";

// Review Board — turn passive prompting into active engineering: record what
// the AI tool changed before you build on top of it.
export default function ReviewBoardPage() {
  const wf = useWorkflowSection("review_board");
  const [filesChanged, setFilesChanged] = useState("");
  const [values, setValues] = useState<Record<FieldKey, string>>({
    ai_generated: "",
    accepted: "",
    rejected: "",
    edited_manually: "",
    ai_assumptions: "",
    least_confident: "",
    out_of_scope_changes: "",
  });

  useEffect(() => {
    if (!wf.stored) return;
    setFilesChanged((wf.stored.files_changed ?? []).join("\n"));
    setValues((prev) => {
      const next = { ...prev };
      for (const f of FIELDS) next[f.key] = (wf.stored?.[f.key] as string | null) ?? "";
      return next;
    });
  }, [wf.stored]);

  // Unsaved-draft persistence (M13E.2): saved backend data prefills first,
  // then any local draft (typed but never saved) overlays it once.
  type ReviewDraft = { filesChanged: string; values: Record<FieldKey, string> };
  const draft = useDraft<ReviewDraft>(wf.phase ? `review_board:${wf.phase.phase}` : null);
  const draftApplied = useRef(false);
  useEffect(() => {
    if (wf.loading || !draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) {
      setFilesChanged(draft.restored.filesChanged ?? "");
      setValues((prev) => ({ ...prev, ...draft.restored?.values }));
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
    saveDraft({ filesChanged, values });
  }, [filesChanged, values, saveDraft]);

  if (wf.notReady) return <NotReady title="Review Board" />;

  async function save() {
    const files = filesChanged
      .split("\n")
      .map((f) => f.trim())
      .filter(Boolean)
      .slice(0, 50)
      .map((f) => f.slice(0, 300));
    const ok = await wf.save({
      files_changed: files,
      ...Object.fromEntries(
        FIELDS.map((f) => [f.key, values[f.key].trim() ? values[f.key].slice(0, 2000) : null])
      ),
    });
    if (ok) {
      skipDraftEcho.current = true;
      draft.clear();
    }
  }

  return (
    <>
      <h1 className="page-title">Review Board</h1>
      <p className="page-sub">
        Back from your AI tool? Note what it actually did before you build on it. Every field is
        optional — skip what you don&rsquo;t know.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
            {wf.phase && (
              <p className="muted" style={{ marginBottom: 14 }}>
                Reviewing work in <strong>Phase {wf.phase.phase}: {wf.phase.phase_title}</strong>
              </p>
            )}

            <div className="card">
              <h3>What changed</h3>
              <div className="field">
                <label>Files changed (one per line, up to 50)</label>
                <textarea
                  rows={4}
                  value={filesChanged}
                  onChange={(e) => setFilesChanged(e.target.value)}
                  placeholder={"app/routes/tasks.py\napp/models.py"}
                />
                <p className="hint">
                  If you can&rsquo;t list them, that itself is a finding — check your tool&rsquo;s
                  diff before saving.
                </p>
              </div>
            </div>

            <div className="card">
              <h3>The review</h3>
              {FIELDS.map((f) => (
                <div className="field" key={f.key}>
                  <label>{f.label}</label>
                  <textarea
                    rows={2}
                    maxLength={2000}
                    value={values[f.key]}
                    onChange={(e) => setValues((prev) => ({ ...prev, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                  />
                </div>
              ))}
            </div>

            <SaveBar
              saving={wf.saving}
              saveError={wf.saveError}
              savedAt={wf.savedAt}
              onSave={save}
              label="Save review"
            />
          </div>

          <aside className="ws-rail" aria-label="Guidance">
            <GuideCard title="What is this page?">
              <p>
                After your AI tool generates something, you record here what it actually did —
                before you build on top of it. It&rsquo;s the &ldquo;Review&rdquo; step of the
                Build Loop.
              </p>
            </GuideCard>
            <GuideCard title="Honest answers win">
              <ul>
                <li>&ldquo;I don&rsquo;t know what it changed&rdquo; is a real finding.</li>
                <li>Rejected nothing? Say so — but check the diff first.</li>
                <li>The &ldquo;least confident&rdquo; answer becomes your best gate prep.</li>
              </ul>
            </GuideCard>
            <GuideCard title="Your text is kept">
              <p>
                Anything you type here survives switching tabs — it&rsquo;s kept as a local draft
                until you press <strong>Save review</strong>, which stores it to your project.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
