"use client";

import { useEffect, useState } from "react";

import Async from "@/components/Async";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
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

  if (wf.notReady) return <NotReady title="Review Board" />;

  async function save() {
    const files = filesChanged
      .split("\n")
      .map((f) => f.trim())
      .filter(Boolean)
      .slice(0, 50)
      .map((f) => f.slice(0, 300));
    await wf.save({
      files_changed: files,
      ...Object.fromEntries(
        FIELDS.map((f) => [f.key, values[f.key].trim() ? values[f.key].slice(0, 2000) : null])
      ),
    });
  }

  return (
    <>
      <h1 className="page-title">Review Board</h1>
      <p className="page-sub">
        You just used an AI tool. Before building on top of the result, put it on the record —
        this is what separates directing AI from trusting it. Your answers feed your Project
        Defense Report.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
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
      </Async>
    </>
  );
}
