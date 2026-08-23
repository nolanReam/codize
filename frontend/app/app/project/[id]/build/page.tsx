"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import V2Character from "@/components/v2/V2Character";
import { V2Button, V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import {
  acceptPrompt,
  getBuildState,
  getCurrentChange,
  getV2Project,
  handoffPrompt,
  selectCodingAgent,
  selectEffort,
  updatePromptDraft,
} from "@/lib/v2-api";
import type {
  BuildResumeState,
  CodingAgentChoice,
  CurrentChangeView,
  EffortCategory,
  V2ProjectView,
} from "@/lib/v2-types";

const agentOptions: Array<{ key: CodingAgentChoice; label: string; hint: string }> = [
  { key: "codex", label: "Codex", hint: "Local or cloud coding agent" },
  { key: "claude_code", label: "Claude Code", hint: "Terminal coding agent" },
  { key: "cursor", label: "Cursor", hint: "AI code editor" },
  { key: "chatgpt", label: "ChatGPT", hint: "Chat-based coding help" },
  { key: "replit", label: "Replit", hint: "Browser-based coding environment" },
  { key: "other", label: "Other", hint: "Use another coding agent" },
];

const effortOptions: Array<{ key: EffortCategory; label: string; hint: string }> = [
  { key: "quick", label: "Quick", hint: "Small, obvious, low-risk change." },
  { key: "standard", label: "Standard", hint: "Normal feature with a few connected pieces." },
  { key: "deep", label: "Deep", hint: "Tricky, unfamiliar, architectural, or high-risk work." },
];

interface BuildData {
  project: V2ProjectView;
  change: CurrentChangeView;
  build: BuildResumeState;
}

export default function BuildPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<BuildData | null>(null);
  const [empty, setEmpty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [promptText, setPromptText] = useState("");
  const [effort, setEffort] = useState<EffortCategory | "">("");
  const [editingReview, setEditingReview] = useState(false);
  const [showWhy, setShowWhy] = useState(false);
  const [agentHelp, setAgentHelp] = useState(false);
  const [status, setStatus] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [project, current] = await Promise.all([getV2Project(id), getCurrentChange(id)]);
      if (!current.current_change) {
        setEmpty(true);
        setData(null);
        return;
      }
      const build = await getBuildState(id, current.current_change.id);
      setData({ project, change: current.current_change, build });
      setPromptText(build.prompt_draft ?? "");
      setEffort(build.effort_category ?? "");
      setEmpty(false);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Couldn't load this build.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const runMutation = useCallback(
    async (action: () => Promise<unknown>, successMessage?: string) => {
      setBusy(true);
      setError(null);
      setConflict(null);
      try {
        await action();
        if (successMessage) setStatus(successMessage);
        await load();
      } catch (reason) {
        if (reason instanceof ApiError && reason.status === 409) {
          setConflict("This change was updated somewhere else. The latest state is now loaded.");
          await load();
        } else {
          setError(reason instanceof ApiError ? reason.message : "That action didn't work. Try again.");
        }
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const chooseAgent = (choice: CodingAgentChoice) => {
    if (!data) return;
    if (choice === "help_me_choose") setAgentHelp(true);
    void runMutation(
      () => selectCodingAgent(id, data.change.id, choice, data.project.version, data.build.current_change_version),
      choice === "help_me_choose" ? undefined : "Coding AI saved."
    );
  };

  const savePrompt = () => {
    if (!data || !promptText.trim()) {
      setError("Write a prompt before continuing.");
      return;
    }
    void runMutation(
      () =>
        updatePromptDraft(
          id,
          data.change.id,
          data.build.current_change_version,
          data.build.prompt_draft_version,
          promptText,
          data.build.structured_decisions.done_condition,
          data.build.structured_decisions.boundaries
        ),
      "Prompt saved."
    );
    setEditingReview(false);
  };

  const saveEffort = () => {
    if (!data || !effort) {
      setError("Choose an effort level before continuing.");
      return;
    }
    void runMutation(
      () => selectEffort(id, data.change.id, effort, data.build.current_change_version),
      "Effort saved."
    );
  };

  const approvePrompt = () => {
    if (!data) return;
    void runMutation(
      () =>
        acceptPrompt(
          id,
          data.change.id,
          data.build.current_change_version,
          data.build.prompt_draft_version
        ),
      "Prompt approved."
    );
  };

  const copyAndHandoff = async () => {
    if (!data?.build.accepted_prompt_version || !data.build.exact_handoff_prompt) return;
    try {
      await navigator.clipboard.writeText(data.build.exact_handoff_prompt);
    } catch {
      setError("Clipboard access is unavailable. Select and copy the prompt manually; it has not been handed off yet.");
      return;
    }
    await runMutation(
      () =>
        handoffPrompt(
          id,
          data.change.id,
          data.build.accepted_prompt_version!.id,
          data.build.current_change_version,
          data.build.accepted_prompt_version!.version
        ),
      "Prompt copied and marked as handed off."
    );
  };

  const copyAgain = async () => {
    if (!data?.build.exact_handoff_prompt) return;
    try {
      await navigator.clipboard.writeText(data.build.exact_handoff_prompt);
      setStatus("Prompt copied.");
    } catch {
      setError("Clipboard access is unavailable. You can select the prompt and copy it manually.");
    }
  };

  if (!data && !empty && !error) {
    return <div className="v2-page v2-build-page"><V2Card><V2Skeleton lines={7} /></V2Card></div>;
  }

  if (empty) {
    return (
      <div className="v2-page v2-page-narrow">
        <V2Card>
          <h1>No current change</h1>
          <p>Start or resume a plan item before opening Build.</p>
          <Link className="v2-button v2-button-primary" href={`/app/project/${id}`}>Back to Project</Link>
        </V2Card>
      </div>
    );
  }

  return (
    <div className="v2-page v2-build-page">
      {data && (
        <>
          <header className="v2-build-header">
            <div>
              <p className="v2-eyebrow">{data.project.display_name}</p>
              <h1>{data.change.goal_snapshot}</h1>
            </div>
            {data.build.selected_agent && <span className="v2-agent-badge">{data.build.selected_agent.display_name}</span>}
          </header>

          {conflict && <V2Notice>{conflict}</V2Notice>}
          {error && <V2Notice tone="error">{error}</V2Notice>}
          <p className="sr-only" role="status" aria-live="polite">{status}</p>

          <div className="v2-conversation">
            <div className="v2-build-character">
              <V2Character size="medium" />
            </div>
            <div className="v2-character-message">
              <V2Character size="mini" />
              <div>
                {data.build.build_stage === "choose_agent" && <p>What coding AI are you using? I’ll tailor model and effort guidance to the tool you actually use.</p>}
                {data.build.build_stage === "edit_prompt" && <p>Here’s the prompt I built from what you decided. Make any changes you want.</p>}
                {data.build.build_stage === "choose_effort" && <p>What effort level do you think this prompt needs in {data.build.selected_agent?.display_name ?? "your coding AI"}?</p>}
                {data.build.build_stage === "review_prompt" && <p>Here’s the prompt I built from what you decided.</p>}
                {data.build.build_stage === "ready_to_handoff" && <p>Your prompt is ready.</p>}
                {data.build.build_stage === "waiting_for_return" && <p>Your coding AI has the prompt. Come back here when it finishes.</p>}
              </div>
            </div>

            {data.build.build_stage === "choose_agent" && (
              <section className="v2-agent-stage" aria-label="Choose your coding AI">
                <div className="v2-agent-grid">
                  {agentOptions.map((option) => (
                    <button key={option.key} type="button" onClick={() => chooseAgent(option.key)} disabled={busy}>
                      <strong>{option.label}</strong>
                      <small>{option.hint}</small>
                    </button>
                  ))}
                </div>
                <V2Button tone="ghost" onClick={() => chooseAgent("help_me_choose")} disabled={busy}>
                  Help me choose
                </V2Button>
                {agentHelp && <p className="v2-muted">Choose the tool where you are already building: editor or terminal agents for a local project, a browser agent for a browser project, or ChatGPT for a chat-based handoff.</p>}
              </section>
            )}

            {data.build.build_stage === "edit_prompt" && (
              <V2Card className="v2-stage-card">
                <label className="v2-field-label" htmlFor="v2-prompt-draft">Your prompt</label>
                <textarea id="v2-prompt-draft" className="v2-prompt-editor" value={promptText} onChange={(event) => setPromptText(event.target.value)} rows={15} disabled={busy} />
                <div className="v2-action-row"><V2Button onClick={savePrompt} disabled={busy}>{busy ? "Saving…" : "Save & continue"}</V2Button></div>
              </V2Card>
            )}

            {data.build.build_stage === "choose_effort" && (
              <V2Card className="v2-stage-card">
                <fieldset className="v2-effort-fieldset">
                  <legend>How much thinking does this prompt need?</legend>
                  {effortOptions.map((option) => (
                    <label key={option.key} className={effort === option.key ? "is-selected" : ""}>
                      <input type="radio" name="effort" value={option.key} checked={effort === option.key} onChange={() => setEffort(option.key)} />
                      <span><strong>{option.label}</strong><small>{option.hint}</small></span>
                    </label>
                  ))}
                </fieldset>
                <div className="v2-action-row"><V2Button onClick={saveEffort} disabled={busy}>{busy ? "Saving…" : "Submit"}</V2Button></div>
              </V2Card>
            )}

            {data.build.build_stage === "review_prompt" && (
              <div className="v2-review-stage">
                <V2Card className="v2-stage-card v2-prompt-card">
                  <p className="v2-card-label">Your prompt</p>
                  {editingReview ? (
                    <textarea aria-label="Edit prompt" className="v2-prompt-editor" value={promptText} onChange={(event) => setPromptText(event.target.value)} rows={15} disabled={busy} />
                  ) : (
                    <pre tabIndex={0}>{data.build.prompt_draft}</pre>
                  )}
                  {showWhy && (
                    <div className="v2-why-panel">
                      <h3>Why this structure?</h3>
                      <p><strong>Project context</strong> says what already exists. <strong>Current change</strong> keeps the work focused. <strong>Done</strong> gives you something real to check. <strong>Boundaries</strong> protect what should stay working.</p>
                    </div>
                  )}
                </V2Card>
                <div className="v2-action-row v2-prompt-actions">
                  <V2Button tone="secondary" onClick={() => editingReview ? savePrompt() : setEditingReview(true)} disabled={busy}>{editingReview ? "Save edit" : "Edit"}</V2Button>
                  <V2Button tone="ghost" onClick={() => setShowWhy((value) => !value)} aria-expanded={showWhy}>{showWhy ? "Hide why" : "Why is this prompt structured this way?"}</V2Button>
                  {!editingReview && <V2Button onClick={approvePrompt} disabled={busy}>{busy ? "Saving…" : "Continue"}</V2Button>}
                </div>
              </div>
            )}

            {data.build.build_stage === "ready_to_handoff" && (
              <V2Card className="v2-stage-card v2-handoff-card">
                <p className="v2-card-label">Ready for {data.build.selected_agent?.display_name ?? "your coding AI"}</p>
                <h2>Your prompt</h2>
                <pre tabIndex={0}>{data.build.exact_handoff_prompt}</pre>
                <p>Open your coding AI and let it finish this change. Codize does not run the code for you.</p>
                <V2Button onClick={() => void copyAndHandoff()} disabled={busy}>{busy ? "Handing off…" : "Copy prompt & hand off"}</V2Button>
              </V2Card>
            )}

            {data.build.build_stage === "waiting_for_return" && (
              <V2Card className="v2-stage-card v2-handoff-card">
                <p className="v2-card-label">Waiting for return</p>
                <h2>Prompt handed off</h2>
                <pre tabIndex={0}>{data.build.exact_handoff_prompt}</pre>
                <p>Finish the change in {data.build.selected_agent?.display_name ?? "your coding AI"}. Reporting what happened and checking the result arrive in the next frontend slice.</p>
                <V2Button tone="secondary" onClick={() => void copyAgain()}>Copy prompt again</V2Button>
              </V2Card>
            )}
          </div>
        </>
      )}
    </div>
  );
}
