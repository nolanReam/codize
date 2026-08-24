"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import V2Character from "@/components/v2/V2Character";
import V2Dialogue from "@/components/v2/V2Dialogue";
import { V2Button, V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import {
  acceptPrompt,
  completeCurrentChange,
  confirmCurrentChange,
  getBuildState,
  getCurrentChange,
  getV2Project,
  getV2Plan,
  getPreferences,
  getRecentChanges,
  handoffPrompt,
  createStudentCheckPlan,
  recordCheck,
  recordReturn,
  requestTeachingHelp,
  respondToTeaching,
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
  PlanItemView,
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

interface LogicalCommandIdentity {
  signature: string;
  commandId: string;
  relatedId?: string;
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
  const [observation, setObservation] = useState("");
  const [teachingResponse, setTeachingResponse] = useState("");
  const [checkPlan, setCheckPlan] = useState("");
  const [effortMessage, setEffortMessage] = useState("");
  const [returnReady, setReturnReady] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [planItem, setPlanItem] = useState<PlanItemView | null>(null);
  const [completed, setCompleted] = useState<{ observation: string; goal: string } | null>(null);
  const teachingCommands = useRef(new Map<string, LogicalCommandIdentity>());

  const commandFor = useCallback((operation: string, signature: string, related = false) => {
    const current = teachingCommands.current.get(operation);
    if (current?.signature === signature) return current;
    const created = {
      signature,
      commandId: crypto.randomUUID(),
      relatedId: related ? crypto.randomUUID() : undefined,
    };
    teachingCommands.current.set(operation, created);
    return created;
  }, []);

  const resolveCommand = useCallback((operation: string, commandId: string) => {
    if (teachingCommands.current.get(operation)?.commandId === commandId) {
      teachingCommands.current.delete(operation);
    }
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [project, current, plan, preferences, recent] = await Promise.all([
        getV2Project(id), getCurrentChange(id), getV2Plan(id), getPreferences(), getRecentChanges(id)
      ]);
      setSoundEnabled(preferences.dialogue_sound_enabled);
      if (!current.current_change) {
        const latest = recent.recent_changes[0];
        if (latest) setCompleted({ observation: latest.observation, goal: latest.goal });
        setEmpty(!latest);
        setData(null);
        return;
      }
      const build = await getBuildState(id, current.current_change.id);
      setData({ project, change: current.current_change, build });
      setPlanItem(plan.items.find((item) => item.id === current.current_change?.plan_item_id) ?? null);
      setPromptText(build.prompt_draft ?? [
        `Project: ${project.display_name}`,
        `Current change: ${current.current_change.goal_snapshot}`,
        `Done when: ${current.current_change.done_condition_snapshot ?? "the requested result is observable"}`,
        "Make only this focused change. Preserve existing working behavior and report what changed.",
      ].join("\n\n"));
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

  const confirm = () => {
    if (!data) return;
    const identity = commandFor(
      "confirm-change", `${data.change.id}:${data.build.current_change_version}`
    );
    void runMutation(() => confirmCurrentChange(id, data.change.id,
      data.build.current_change_version, identity.commandId).then((result) => {
        resolveCommand("confirm-change", identity.commandId);
        return result;
      }), "Current change confirmed.");
  };

  const reportReturn = (outcome: "worked" | "broken" | "unsure") => {
    if (!data) return;
    void runMutation(() => recordReturn(id, data.change.id, data.build.current_change_version,
      outcome, outcome !== "broken" && data.build.verification_plan_source === "codize"
        ? crypto.randomUUID() : null), "Return saved.");
  };

  const submitCheck = (result: "worked" | "did_not_work" | "unsure") => {
    if (!data?.build.active_check || !observation.trim()) {
      setError("Describe what you observed when you tried the check."); return;
    }
    void runMutation(() => recordCheck(id, data.change.id, data.build.active_check!.id,
      data.build.current_change_version, data.build.active_check!.version, result,
      observation, result === "unsure" ? crypto.randomUUID() : null), "Check saved.");
    setObservation("");
  };

  const complete = async () => {
    if (!data || !planItem || !data.build.active_check?.student_observation) return;
    setBusy(true); setError(null);
    try {
      const result = await completeCurrentChange(id, data.change.id,
        data.build.current_change_version, data.project.plan_version, planItem.version);
      setCompleted({ observation: result.check.student_observation ?? "Check completed.",
        goal: data.change.goal_snapshot });
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) { setConflict("The completion state changed. Reloading the latest version."); await load(); }
      else setError(reason instanceof ApiError ? reason.message : "Couldn't complete this change.");
    } finally { setBusy(false); }
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
    const identity = commandFor(
      "effort",
      `${data.change.id}:${data.build.current_change_version}:${effort}`
    );
    setBusy(true);
    setError(null);
    setConflict(null);
    void selectEffort(id, data.change.id, effort, data.build.current_change_version,
      identity.commandId)
      .then(async (result) => {
        resolveCommand("effort", identity.commandId);
        setEffortMessage(result.feedback.message);
        setStatus(result.feedback.message);
        await load();
      })
      .catch(async (reason) => {
        if (reason instanceof ApiError && reason.status === 409) {
          setConflict("This change was updated somewhere else. The latest state is now loaded.");
          await load();
        } else {
          setError(reason instanceof ApiError ? reason.message : "That effort choice couldn't be saved.");
        }
      })
      .finally(() => setBusy(false));
  };

  const askForHelp = () => {
    if (!data?.build.teaching?.can_request_help) return;
    const interaction = data.build.teaching;
    const identity = commandFor(
      "teaching-help",
      `${data.change.id}:${data.build.current_change_version}:${interaction.context}:${interaction.hint_level}`
    );
    void runMutation(
      () => requestTeachingHelp(id, data.change.id, data.build.current_change_version,
        interaction.context, identity.commandId).then((result) => {
          resolveCommand("teaching-help", identity.commandId);
          return result;
        }),
      "A little more help is shown."
    );
  };

  const submitTeachingResponse = () => {
    const interaction = data?.build.teaching;
    if (!data || !interaction || interaction.context === "verification") return;
    const context = interaction.context;
    const response = interaction.mode === "remind" ? "continue" : teachingResponse.trim();
    if (!response) {
      setError("Write a short answer tied to this change before continuing.");
      return;
    }
    const identity = commandFor(
      "teaching-response",
      `${data.change.id}:${data.build.current_change_version}:${context}:${response}`
    );
    void runMutation(
      () => respondToTeaching(id, data.change.id, data.build.current_change_version,
        context, response, identity.commandId).then((result) => {
          resolveCommand("teaching-response", identity.commandId);
          setTeachingResponse("");
          return result;
        }),
      context === "understanding" ? "Understanding saved." : "Decision saved."
    );
  };

  const submitCheckPlan = () => {
    if (!data || !checkPlan.trim()) {
      setError("Describe one thing you can personally try to check the result.");
      return;
    }
    const plan = checkPlan.trim();
    const identity = commandFor(
      "check-plan",
      `${data.change.id}:${data.build.current_change_version}:${plan}`,
      true
    );
    void runMutation(
      () => createStudentCheckPlan(id, data.change.id,
        data.build.current_change_version, plan, identity.commandId,
        identity.relatedId!).then((result) => {
          resolveCommand("check-plan", identity.commandId);
          setCheckPlan("");
          return result;
        }),
      "Check plan saved."
    );
  };

  const approvePrompt = () => {
    if (!data) return;
    setEffortMessage("");
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

  if (completed) return <div className="v2-page v2-page-narrow"><V2Card className="v2-complete-card">
    <p className="v2-card-label">Done</p><h1>{completed.goal}</h1>
    <p><span aria-hidden="true">✓</span> Checked: {completed.observation}</p>
    <div className="v2-action-row"><Link className="v2-button v2-button-primary" href={`/app/project/${id}`}>Back to Project</Link>
      <Link className="v2-button v2-button-secondary" href={`/app/project/${id}`}>Keep building</Link></div>
  </V2Card></div>;

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
          {effortMessage && data.build.build_stage !== "choose_effort" && (
            <V2Notice>{effortMessage}</V2Notice>
          )}
          <p className="sr-only" role="status" aria-live="polite">{status}</p>

          <div className="v2-conversation">
            <div className="v2-build-character">
              <V2Character size="medium" />
            </div>
            <div className="v2-character-message">
              <V2Character size="mini" />
              <div>
                {data.build.build_stage === "confirm_change" && <V2Dialogue soundEnabled={soundEnabled} text="Let’s keep this focused. Confirm the one change and the result you’ll check." />}
                {data.build.build_stage === "intervention" && data.build.teaching && <V2Dialogue soundEnabled={soundEnabled} text={data.build.teaching.title} />}
                {data.build.build_stage === "choose_agent" && <V2Dialogue soundEnabled={soundEnabled} text="What coding AI are you using? I’ll tailor the handoff to the tool you actually use." />}
                {data.build.build_stage === "edit_prompt" && <V2Dialogue soundEnabled={soundEnabled} text="Here’s a prompt built from your current change. Make any changes you want." />}
                {data.build.build_stage === "choose_effort" && <V2Dialogue soundEnabled={soundEnabled} text={`What effort level does this prompt need in ${data.build.selected_agent?.display_name ?? "your coding AI"}?`} />}
                {data.build.build_stage === "review_prompt" && <V2Dialogue soundEnabled={soundEnabled} text="Review the exact prompt before you hand it off." />}
                {data.build.build_stage === "ready_to_handoff" && <V2Dialogue soundEnabled={soundEnabled} text="Your prompt is ready." />}
                {data.build.build_stage === "waiting_for_return" && <V2Dialogue soundEnabled={soundEnabled} text="Welcome back. What happened when your coding AI finished?" />}
                {(data.build.build_stage === "perform_check" || data.build.build_stage === "check_unsure") && <V2Dialogue soundEnabled={soundEnabled} text="Try this yourself, then tell me exactly what you observed." />}
                {data.build.build_stage === "propose_check" && <V2Dialogue soundEnabled={soundEnabled} text="Before checking, choose one thing you can personally try and observe." />}
                {data.build.build_stage === "understand" && data.build.teaching && <V2Dialogue soundEnabled={soundEnabled} text="One useful thing to understand before you finish." />}
                {data.build.build_stage === "ready_to_complete" && <V2Dialogue soundEnabled={soundEnabled} text="Your check worked. Save this result and finish the change." />}
                {data.build.build_stage === "check_failed" && <V2Dialogue soundEnabled={soundEnabled} text="That result doesn’t support completion yet. Your work is saved; Recovery will continue this in Phase 6." />}
              </div>
            </div>

            {data.build.build_stage === "confirm_change" && <V2Card className="v2-stage-card">
              <p className="v2-card-label">Current change</p><h2>{data.change.goal_snapshot}</h2>
              <p><strong>Done when:</strong> {planItem?.intended_outcome}</p>
              <V2Button onClick={confirm} disabled={busy}>{busy ? "Starting…" : "Start"}</V2Button>
            </V2Card>}

            {data.build.build_stage === "intervention" && data.build.teaching && (
              <V2Card className="v2-stage-card">
                <p className="v2-card-label">{data.build.teaching.mode}</p>
                <h2>{data.build.teaching.title}</h2>
                {data.build.teaching.risk === "slowdown" && (
                  <V2Notice>We’re slowing down briefly because this change affects access, sensitive data, deployment, or another consequential boundary. Your experience still counts; the safeguard stays.</V2Notice>
                )}
                {data.build.teaching.explanation && <p>{data.build.teaching.explanation}</p>}
                {data.build.teaching.example && <p className="v2-muted"><strong>For this project:</strong> {data.build.teaching.example}</p>}
                {data.build.teaching.reminder && <p>{data.build.teaching.reminder}</p>}
                {data.build.teaching.question && (
                  <>
                    <label className="v2-field-label" htmlFor="v2-teaching-response">{data.build.teaching.question}</label>
                    <textarea id="v2-teaching-response" rows={4} value={teachingResponse}
                      onChange={(event) => setTeachingResponse(event.target.value)} disabled={busy} />
                  </>
                )}
                {data.build.teaching.hint_text && <V2Notice>{data.build.teaching.hint_text}</V2Notice>}
                <div className="v2-action-row">
                  {data.build.teaching.can_request_help && (
                    <V2Button tone="secondary" onClick={askForHelp} disabled={busy}>
                      {data.build.teaching.hint_level === "none" ? "Need help?" : "Show me more"}
                    </V2Button>
                  )}
                  <V2Button onClick={submitTeachingResponse} disabled={busy}>
                    {busy ? "Saving…" : data.build.teaching.mode === "remind" ? "Continue" : "Save & continue"}
                  </V2Button>
                </div>
              </V2Card>
            )}

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
                {data.change.risk === "slowdown" && (
                  <V2Notice>
                    This prompt now touches a consequential boundary. Choose deliberately;
                    Codize will keep the required personal Check before completion.
                  </V2Notice>
                )}
                <fieldset className="v2-effort-fieldset">
                  <legend>How much thinking does this prompt need?</legend>
                  {effortOptions.map((option) => (
                    <label key={option.key} className={effort === option.key ? "is-selected" : ""}>
                      <input type="radio" name="effort" value={option.key} checked={effort === option.key} onChange={() => setEffort(option.key)} />
                      <span><strong>{option.label}</strong><small>{option.hint}</small></span>
                    </label>
                  ))}
                </fieldset>
                {(data.build.effort_feedback?.message || effortMessage) && (
                  <V2Notice>{data.build.effort_feedback?.message ?? effortMessage}</V2Notice>
                )}
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
                {!returnReady ? <><p>Finish the change in {data.build.selected_agent?.display_name ?? "your coding AI"}, then return here.</p>
                  <div className="v2-action-row"><V2Button onClick={() => setReturnReady(true)}>I’m back</V2Button>
                  <V2Button tone="secondary" onClick={() => void copyAgain()}>Copy prompt again</V2Button></div></> : <>
                  <p>What happened?</p><div className="v2-return-choices">
                    <V2Button onClick={() => reportReturn("worked")} disabled={busy}>It worked</V2Button>
                    <V2Button tone="secondary" onClick={() => reportReturn("broken")} disabled={busy}>Something’s wrong</V2Button>
                    <V2Button tone="ghost" onClick={() => reportReturn("unsure")} disabled={busy}>I’m not sure</V2Button>
                  </div></>}
              </V2Card>
            )}

            {(data.build.build_stage === "perform_check" || data.build.build_stage === "check_unsure") && data.build.active_check && <V2Card className="v2-stage-card v2-check-card">
              <p className="v2-card-label">Try this</p><h2>{data.build.active_check.check_plan}</h2>
              {data.build.build_stage === "check_unsure" && <V2Notice>Uncertainty is useful. Run the check and record only what you actually see.</V2Notice>}
              <label className="v2-field-label" htmlFor="v2-observation">What did you observe?</label>
              <textarea id="v2-observation" rows={4} value={observation} onChange={(event) => setObservation(event.target.value)} />
              <p className="v2-muted">These buttons confirm that you performed the check yourself.</p>
              <div className="v2-return-choices"><V2Button onClick={() => submitCheck("worked")} disabled={busy}>Worked</V2Button>
                <V2Button tone="secondary" onClick={() => submitCheck("did_not_work")} disabled={busy}>Didn’t work</V2Button>
                <V2Button tone="ghost" onClick={() => submitCheck("unsure")} disabled={busy}>Not sure</V2Button></div>
            </V2Card>}

            {data.build.build_stage === "propose_check" && data.build.teaching && (
              <V2Card className="v2-stage-card v2-check-card">
                <p className="v2-card-label">{data.build.teaching.mode}</p>
                <h2>{data.build.teaching.title}</h2>
                {data.build.teaching.explanation && <p>{data.build.teaching.explanation}</p>}
                {data.build.teaching.example && <p className="v2-muted"><strong>For this project:</strong> {data.build.teaching.example}</p>}
                {data.build.teaching.reminder && <p>{data.build.teaching.reminder}</p>}
                <label className="v2-field-label" htmlFor="v2-check-plan">
                  {data.build.teaching.question ?? "What will you personally try and observe?"}
                </label>
                <textarea id="v2-check-plan" rows={4} value={checkPlan}
                  onChange={(event) => setCheckPlan(event.target.value)} disabled={busy} />
                {data.build.teaching.hint_text && <V2Notice>{data.build.teaching.hint_text}</V2Notice>}
                <div className="v2-action-row">
                  {data.build.teaching.can_request_help && (
                    <V2Button tone="secondary" onClick={askForHelp} disabled={busy}>
                      {data.build.teaching.hint_level === "none" ? "Need help?" : "Show me more"}
                    </V2Button>
                  )}
                  <V2Button onClick={submitCheckPlan} disabled={busy}>{busy ? "Saving…" : "Use this check"}</V2Button>
                </div>
              </V2Card>
            )}

            {data.build.build_stage === "understand" && data.build.teaching && (
              <V2Card className="v2-stage-card">
                <p className="v2-card-label">{data.build.teaching.mode}</p>
                <h2>{data.build.teaching.title}</h2>
                {data.build.teaching.explanation && <p>{data.build.teaching.explanation}</p>}
                {data.build.teaching.example && <p className="v2-muted"><strong>Keep it practical:</strong> {data.build.teaching.example}</p>}
                {data.build.teaching.reminder && <p>{data.build.teaching.reminder}</p>}
                <label className="v2-field-label" htmlFor="v2-understanding-response">
                  {data.build.teaching.question ?? "What important cause-and-effect relationship did this change add?"}
                </label>
                <textarea id="v2-understanding-response" rows={4} value={teachingResponse}
                  onChange={(event) => setTeachingResponse(event.target.value)} disabled={busy} />
                {data.build.teaching.hint_text && <V2Notice>{data.build.teaching.hint_text}</V2Notice>}
                <div className="v2-action-row">
                  {data.build.teaching.can_request_help && (
                    <V2Button tone="secondary" onClick={askForHelp} disabled={busy}>
                      {data.build.teaching.hint_level === "none" ? "Need help?" : "Show me more"}
                    </V2Button>
                  )}
                  <V2Button onClick={submitTeachingResponse} disabled={busy}>{busy ? "Saving…" : "Save & continue"}</V2Button>
                </div>
              </V2Card>
            )}

            {data.build.build_stage === "ready_to_complete" && <V2Card className="v2-stage-card v2-complete-card">
              <p className="v2-card-label">Checked</p><h2>{data.build.active_check?.check_plan}</h2>
              <p>{data.build.active_check?.student_observation}</p>
              <V2Button onClick={() => void complete()} disabled={busy}>{busy ? "Finishing…" : "Complete change"}</V2Button>
            </V2Card>}

            {data.build.build_stage === "check_failed" && <V2Card className="v2-stage-card">
              <h2>This change isn’t complete yet</h2><p>Codize won’t mark a failed or uncertain result as done. Return to the Project; your evidence remains saved.</p>
              <Link className="v2-button v2-button-secondary" href={`/app/project/${id}`}>Back to Project</Link>
            </V2Card>}
          </div>
        </>
      )}
    </div>
  );
}
