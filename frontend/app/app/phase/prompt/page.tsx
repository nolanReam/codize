"use client";

import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import SaveBar from "@/components/SaveBar";
import { getIntakeStatus } from "@/lib/api";
import { useDraft } from "@/lib/drafts";
import { phaseGuide } from "@/lib/phaseGuide";
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
// persisted as the phase's prompt_builder artifact (M13B). M13E.1 added the
// beginner layer: a plain-language phase explanation, starter asks (from the
// static phase guide + the phase's own roadmap tasks), and per-field help —
// the builder should produce a good prompt even when the student doesn't yet
// know what to ask.
export default function PromptBuilderPage() {
  const wf = useWorkflowSection("prompt_builder");
  const [inputs, setInputs] = useState<PromptBuilderInputs>(EMPTY);
  const [built, setBuilt] = useState<ReturnType<typeof buildPrompt> | null>(null);
  const [copied, setCopied] = useState(false);
  const [intakePurpose, setIntakePurpose] = useState<string | null>(null);
  const [intakeStack, setIntakeStack] = useState<string | null>(null);

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

  // Unsaved-draft persistence (M13E.2): the saved artifact prefills first,
  // then any local draft (typed but never saved) overlays it once.
  const draft = useDraft<PromptBuilderInputs>(
    wf.phase ? `prompt_builder:${wf.phase.phase}` : null
  );
  const draftApplied = useRef(false);
  useEffect(() => {
    if (wf.loading || !draft.ready || draftApplied.current) return;
    draftApplied.current = true;
    if (draft.restored) setInputs({ ...EMPTY, ...draft.restored });
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
    saveDraft(inputs);
  }, [inputs, saveDraft]);

  // The student's own intake answers, offered as tap-to-use starters (never
  // auto-filled — the student stays the author of every field).
  useEffect(() => {
    let cancelled = false;
    getIntakeStatus()
      .then((s) => {
        if (cancelled) return;
        setIntakePurpose(s.answers?.purpose ?? null);
        setIntakeStack(s.answers?.stack ?? null);
      })
      .catch(() => {
        // Starters are optional sugar; the page works without them.
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
    const ok = await wf.save({
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
    if (ok) {
      skipDraftEcho.current = true;
      draft.clear();
    }
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

  const guide = wf.phase ? phaseGuide(wf.phase.phase_title) : null;
  const roadmapStarters = wf.phase
    ? wf.phase.ai_appropriate_tasks.filter((t) => !t.completed).slice(0, 3)
    : [];

  return (
    <>
      <h1 className="page-title">Prompt Builder</h1>
      <p className="page-sub">
        Plan the request before you generate. You don&rsquo;t need to know what to ask yet —
        that&rsquo;s what this page is for. Built deterministically: no AI writes your prompt.
      </p>

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
            {wf.phase && guide && (
              <div className="card" style={{ marginBottom: 14 }}>
                <h3>
                  What Phase {wf.phase.phase} means — {wf.phase.phase_title}
                </h3>
                <p>{guide.meaning}</p>
                <p className="muted" style={{ marginTop: 8 }}>
                  Your roadmap puts it this way: {wf.phase.core_concept}
                </p>
                <hr className="rule" />
                <p className="muted" style={{ marginBottom: 4 }}>
                  Not sure what to ask AI? Tap a starter, then edit it to fit your project:
                </p>
                <div className="chips">
                  {guide.asks.map((a) => (
                    <button key={a} type="button" className="chip" onClick={() => set("aiTask", a)}>
                      {a}
                    </button>
                  ))}
                </div>
                {roadmapStarters.length > 0 && (
                  <>
                    <p className="muted" style={{ margin: "10px 0 4px" }}>
                      Or start from this phase&rsquo;s own AI-appropriate tasks:
                    </p>
                    <div className="chips">
                      {roadmapStarters.map((t) => (
                        <button
                          key={t.task_id}
                          type="button"
                          className="chip"
                          onClick={() => set("aiTask", t.description)}
                        >
                          {t.description}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
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
                    placeholder="e.g. a task tracker for my study group"
                  />
                  <p className="hint">One sentence is enough — the AI just needs the big picture.</p>
                  {intakePurpose && !inputs.projectGoal && (
                    <div className="chips">
                      <button
                        type="button"
                        className="chip"
                        onClick={() => set("projectGoal", intakePurpose)}
                      >
                        Use my intake answer
                      </button>
                    </div>
                  )}
                </div>
                <div className="field">
                  <label>What is this phase about?</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.phaseGoal}
                    onChange={(e) => set("phaseGoal", e.target.value)}
                    placeholder="e.g. designing the data model"
                  />
                  <p className="hint">
                    In your own words. Steal from &ldquo;What this phase means&rdquo; above.
                  </p>
                  {guide && !inputs.phaseGoal && (
                    <div className="chips">
                      <button
                        type="button"
                        className="chip"
                        onClick={() => set("phaseGoal", guide.meaning)}
                      >
                        Use the phase explanation
                      </button>
                    </div>
                  )}
                </div>
                <div className="field">
                  <label>What exactly should the AI do? (one task)</label>
                  <textarea
                    rows={3}
                    maxLength={2000}
                    value={inputs.aiTask}
                    onChange={(e) => set("aiTask", e.target.value)}
                    placeholder="e.g. propose a schema for tasks and members, and explain each table"
                  />
                  <p className="hint">
                    Pick ONE thing. Unsure? Tap a starter above — you can edit it here.
                  </p>
                </div>
                <div className="field">
                  <label>Files / components involved (optional)</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.files}
                    onChange={(e) => set("files", e.target.value)}
                    placeholder="e.g. app/models.py, app/routes/tasks.py"
                  />
                  <p className="hint">
                    Only if you know them — leaving this empty early on is normal.
                  </p>
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
                    placeholder="e.g. Java only — that's what I know"
                  />
                  <p className="hint">
                    Rules the AI must follow. Your language counts: &ldquo;Python only&rdquo; is a
                    great constraint.
                  </p>
                  {intakeStack && !inputs.constraints && (
                    <div className="chips">
                      <button
                        type="button"
                        className="chip"
                        onClick={() => set("constraints", `Stick to what I know: ${intakeStack}`)}
                      >
                        Use my stack from intake
                      </button>
                    </div>
                  )}
                </div>
                <div className="field">
                  <label>What must the AI NOT change?</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.doNotChange}
                    onChange={(e) => set("doNotChange", e.target.value)}
                    placeholder="e.g. the auth setup, main.py"
                  />
                  <p className="hint">
                    Anything that already works. If nothing&rsquo;s built yet, leave it empty.
                  </p>
                </div>
                <div className="field">
                  <label>What are you least sure about? (optional)</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.uncertainty}
                    onChange={(e) => set("uncertainty", e.target.value)}
                    placeholder="e.g. how the foreign keys should link"
                  />
                  <p className="hint">
                    Naming what confuses you is a strength — the AI will flag anything touching it.
                  </p>
                </div>
                <label className="checkline">
                  <input
                    type="checkbox"
                    checked={inputs.planFirst}
                    onChange={(e) => set("planFirst", e.target.checked)}
                  />
                  Ask for a plan before any code
                </label>
                <p className="hint" style={{ margin: "0 0 6px 26px" }}>
                  The AI proposes first, you approve — you stay the decision-maker.
                </p>
                <label className="checkline">
                  <input
                    type="checkbox"
                    checked={inputs.wantChecks}
                    onChange={(e) => set("wantChecks", e.target.checked)}
                  />
                  Ask for manual verification steps
                </label>
                <p className="hint" style={{ margin: "0 0 0 26px" }}>
                  So you can prove the result works instead of trusting it.
                </p>
              </div>
            </div>

            <div className="row" style={{ margin: "16px 0" }}>
              <button className="btn primary" onClick={generate} disabled={!inputs.aiTask.trim()}>
                Build the prompt
              </button>
              {!inputs.aiTask.trim() && (
                <span className="muted">
                  Fill &ldquo;What exactly should the AI do?&rdquo; first — a starter above works.
                </span>
              )}
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
          </div>

          <aside className="ws-rail" aria-label="Guidance">
            <GuideCard title="What is this page?">
              <p>
                Before you ask your AI tool for code, you plan the request here. Codize turns your
                answers into a scoped, fenced prompt — the difference between directing AI and
                gambling with it.
              </p>
            </GuideCard>
            <GuideCard title="A good ask is…">
              <ul>
                <li><strong>One task</strong>, not &ldquo;build my app&rdquo;.</li>
                <li><strong>Fenced</strong> — says what must not change.</li>
                <li><strong>Checkable</strong> — asks how you&rsquo;ll verify it.</li>
              </ul>
              <p>You don&rsquo;t have to write it from scratch — the starters exist to be edited.</p>
            </GuideCard>
            <GuideCard title="Confused by a field?">
              <p>
                Every field has a hint under it, and every field except the AI task is optional.
                A prompt from just one clear task already beats most prompts.
              </p>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
