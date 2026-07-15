"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import AdaptiveStepGuide from "@/components/AdaptiveStepGuide";
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

  // Quick-add guardrail chips append (never overwrite) the constraints field.
  const addConstraint = (text: string) =>
    setInputs((prev) => ({
      ...prev,
      constraints: prev.constraints.trim()
        ? prev.constraints.includes(text)
          ? prev.constraints
          : `${prev.constraints}. ${text}`
        : text,
    }));

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
        One clear ask beats a long conversation. Tap a starter if you&rsquo;re not sure — Codize
        turns it into a strong prompt.
      </p>
      <AdaptiveStepGuide stage="prompt" />

      <Async loading={wf.loading} error={wf.error} onRetry={wf.reload}>
        <div className="workspace">
          <div>
            {/* Step 1 — the ask. The only required field, starters included. */}
            <div className="card primary" style={{ marginBottom: 16 }}>
              <h3>Step 1 — What should the AI do?</h3>
              <textarea
                rows={3}
                maxLength={2000}
                value={inputs.aiTask}
                onChange={(e) => set("aiTask", e.target.value)}
                placeholder="One task, e.g. propose a schema for tasks and members, and explain each table"
              />
              {guide && (
                <>
                  <p className="muted" style={{ margin: "10px 0 0" }}>
                    Not sure? Tap one, then edit it:
                  </p>
                  <div className="chips">
                    {guide.asks.map((a) => (
                      <button
                        key={a}
                        type="button"
                        className="chip"
                        onClick={() => set("aiTask", a)}
                      >
                        {a}
                      </button>
                    ))}
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
              {wf.phase && guide && (
                <details className="help">
                  <summary>What does this phase mean?</summary>
                  <div className="help-body">
                    <p>{guide.meaning}</p>
                    <p className="muted">Your roadmap puts it this way: {wf.phase.core_concept}</p>
                  </div>
                </details>
              )}
            </div>

            <div className="card-grid">
              {/* Step 2 — context, all optional. */}
              <div className="card">
                <h3>Step 2 — Context (optional)</h3>
                <div className="field">
                  <label>Your project</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.projectGoal}
                    onChange={(e) => set("projectGoal", e.target.value)}
                    placeholder="one sentence, e.g. a task tracker for my study group"
                  />
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
                  <label>This phase</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.phaseGoal}
                    onChange={(e) => set("phaseGoal", e.target.value)}
                    placeholder="in your own words, e.g. designing the data model"
                  />
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
                  <label>Files involved</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.files}
                    onChange={(e) => set("files", e.target.value)}
                    placeholder="only if you know them, e.g. app/models.py"
                  />
                </div>
              </div>

              {/* Step 3 — guardrails. Quick-add chips over typing. */}
              <div className="card">
                <h3>Step 3 — Guardrails</h3>
                <div className="chips" style={{ marginTop: 0 }}>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => set("planFirst", true)}
                  >
                    Plan first
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => addConstraint("Ask me clarifying questions before writing any code")}
                  >
                    Ask questions before coding
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() =>
                      set(
                        "doNotChange",
                        inputs.doNotChange.trim()
                          ? `${inputs.doNotChange}, the auth setup`
                          : "the auth setup"
                      )
                    }
                  >
                    Do not touch auth
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => addConstraint("Explain each table and decision in plain language")}
                  >
                    Explain each table
                  </button>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => set("wantChecks", true)}
                  >
                    Give manual verification steps
                  </button>
                </div>
                <div className="field">
                  <label>Rules the AI must follow</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.constraints}
                    onChange={(e) => set("constraints", e.target.value)}
                    placeholder='e.g. "Python only — that&apos;s what I know"'
                  />
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
                  <label>Don&rsquo;t touch</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.doNotChange}
                    onChange={(e) => set("doNotChange", e.target.value)}
                    placeholder="anything that already works, e.g. main.py"
                  />
                </div>
                <div className="field">
                  <label>Least sure about</label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={inputs.uncertainty}
                    onChange={(e) => set("uncertainty", e.target.value)}
                    placeholder="naming it is a strength, e.g. foreign keys"
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
              {!inputs.aiTask.trim() && (
                <span className="muted">Step 1 first — a starter chip works.</span>
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
                {/* The loop's hand-off: prompt out → result back (M15B). */}
                {wf.savedAt && (
                  <p className="muted" style={{ marginTop: 12 }}>
                    Use your prompt in your AI coding tool. Then{" "}
                    <Link href="/app/phase/import">Bring Back What Changed →</Link>
                  </p>
                )}
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
