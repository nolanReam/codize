"use client";

import { useEffect, useState } from "react";

import Async from "@/components/Async";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { buildPrompt, type PromptBuilderInputs } from "@/lib/promptBuilder";
import { useWorkflowSection } from "@/lib/useWorkflowSection";

const EMPTY: PromptBuilderInputs = {
  projectGoal: "",
  phaseGoal: "",
  aiTask: "",
  files: "",
  constraints: "",
  doNotChange: "",
  planFirst: true,
  wantChecks: true,
  uncertainty: "",
};

// Deterministic client-side Prompt Builder (v0.1) — no LLM call. Output is
// persisted as the phase's prompt_builder artifact (M13B).
export default function PromptBuilderPage() {
  const wf = useWorkflowSection("prompt_builder");
  const [inputs, setInputs] = useState<PromptBuilderInputs>(EMPTY);
  const [built, setBuilt] = useState<ReturnType<typeof buildPrompt> | null>(null);
  const [copied, setCopied] = useState(false);

  // Prefill from the saved artifact once loaded.
  useEffect(() => {
    if (!wf.stored) return;
    const saved = wf.stored.inputs ?? {};
    setInputs({
      projectGoal: saved.project_goal ?? "",
      phaseGoal: saved.phase_goal ?? "",
      aiTask: saved.ai_task ?? "",
      files: saved.files ?? "",
      constraints: saved.constraints ?? "",
      doNotChange: saved.do_not_change ?? "",
      planFirst: saved.plan_first !== "no",
      wantChecks: saved.want_checks !== "no",
      uncertainty: saved.uncertainty ?? "",
    });
    setBuilt({
      prompt: wf.stored.generated_prompt,
      whyStronger: wf.stored.why_stronger ?? "",
      badPrompt: wf.stored.bad_prompt_comparison ?? "",
    });
  }, [wf.stored]);

  if (wf.notReady) return <NotReady title="Prompt Builder" />;

  const set = (key: keyof PromptBuilderInputs, value: string | boolean) =>
    setInputs((prev) => ({ ...prev, [key]: value }));

  function generate() {
    setBuilt(buildPrompt(inputs));
    setCopied(false);
  }

  async function save() {
    const result = built ?? buildPrompt(inputs);
    setBuilt(result);
    await wf.save({
      inputs: {
        project_goal: inputs.projectGoal.slice(0, 2000),
        phase_goal: inputs.phaseGoal.slice(0, 2000),
        ai_task: inputs.aiTask.slice(0, 2000),
        files: inputs.files.slice(0, 2000),
        constraints: inputs.constraints.slice(0, 2000),
        do_not_change: inputs.doNotChange.slice(0, 2000),
        plan_first: inputs.planFirst ? "yes" : "no",
        want_checks: inputs.wantChecks ? "yes" : "no",
        uncertainty: inputs.uncertainty.slice(0, 2000),
      },
      generated_prompt: result.prompt,
      why_stronger: result.whyStronger.slice(0, 2000),
      bad_prompt_comparison: result.badPrompt.slice(0, 8000),
    });
  }

  async function copy() {
    if (!built) return;
    try {
      await navigator.clipboard.writeText(built.prompt);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <>
      <h1 className="page-title">Prompt Builder</h1>
      <p className="page-sub">
        Plan the request before you generate. A scoped, constraint-driven prompt is the
        difference between directing AI and gambling with it. Built deterministically — no AI
        writes your prompt.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        {wf.phase && (
          <p className="muted" style={{ marginBottom: 14 }}>
            Building for <strong>Phase {wf.phase.phase}: {wf.phase.phase_title}</strong>
          </p>
        )}

        <div className="card-grid">
          <div className="card">
            <h3>Context</h3>
            <div className="field">
              <label>What are you building overall?</label>
              <input
                type="text"
                maxLength={2000}
                value={inputs.projectGoal}
                onChange={(e) => set("projectGoal", e.target.value)}
                placeholder="a task tracker for my study group"
              />
            </div>
            <div className="field">
              <label>What is this phase about?</label>
              <input
                type="text"
                maxLength={2000}
                value={inputs.phaseGoal}
                onChange={(e) => set("phaseGoal", e.target.value)}
                placeholder="designing the data model"
              />
            </div>
            <div className="field">
              <label>What exactly should the AI do? (one task)</label>
              <textarea
                rows={3}
                maxLength={2000}
                value={inputs.aiTask}
                onChange={(e) => set("aiTask", e.target.value)}
                placeholder="propose a schema for tasks and members, and explain each table"
              />
            </div>
            <div className="field">
              <label>Files / components involved (optional)</label>
              <input
                type="text"
                maxLength={2000}
                value={inputs.files}
                onChange={(e) => set("files", e.target.value)}
                placeholder="app/models.py, app/routes/tasks.py"
              />
            </div>
          </div>

          <div className="card">
            <h3>Guardrails</h3>
            <div className="field">
              <label>Constraints (stack, style, requirements)</label>
              <input
                type="text"
                maxLength={2000}
                value={inputs.constraints}
                onChange={(e) => set("constraints", e.target.value)}
                placeholder="FastAPI, async, ownership fields + RLS"
              />
            </div>
            <div className="field">
              <label>What must the AI NOT change?</label>
              <input
                type="text"
                maxLength={2000}
                value={inputs.doNotChange}
                onChange={(e) => set("doNotChange", e.target.value)}
                placeholder="the auth setup, main.py"
              />
            </div>
            <div className="field">
              <label>What are you least sure about? (optional)</label>
              <input
                type="text"
                maxLength={2000}
                value={inputs.uncertainty}
                onChange={(e) => set("uncertainty", e.target.value)}
                placeholder="how the foreign keys should link"
              />
            </div>
            <label className="checkline">
              <input
                type="checkbox"
                checked={inputs.planFirst}
                onChange={(e) => set("planFirst", e.target.checked)}
              />
              Ask for a plan before any code
            </label>
            <label className="checkline">
              <input
                type="checkbox"
                checked={inputs.wantChecks}
                onChange={(e) => set("wantChecks", e.target.checked)}
              />
              Ask for manual verification steps
            </label>
          </div>
        </div>

        <div className="row" style={{ margin: "16px 0" }}>
          <button className="btn primary" onClick={generate} disabled={!inputs.aiTask.trim()}>
            Build the prompt
          </button>
        </div>

        {built && (
          <>
            <div className="card">
              <div className="spread">
                <h3>Your prompt — paste into your AI tool</h3>
                <button className="btn small" onClick={copy}>
                  {copied ? "Copied ✓" : "Copy"}
                </button>
              </div>
              <pre className="output">{built.prompt}</pre>
            </div>
            <div className="card">
              <h3>Why this is stronger</h3>
              <p>{built.whyStronger}</p>
              <hr className="rule" />
              <p className="muted">
                Compare with what usually goes wrong:{" "}
                <span className="mono">&ldquo;{built.badPrompt}&rdquo;</span> — no scope, no
                fences, no verification. That prompt is how projects end up 80% done and 100%
                confusing.
              </p>
            </div>
            <SaveBar
              saving={wf.saving}
              saveError={wf.saveError}
              savedAt={wf.savedAt}
              onSave={save}
              label="Save to workflow"
            />
          </>
        )}
      </Async>
    </>
  );
}
