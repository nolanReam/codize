"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import V2Character from "@/components/v2/V2Character";
import V2Dialogue from "@/components/v2/V2Dialogue";
import { V2Button, V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { resolveLoadedBuildStatus, type BuildPageLoadStatus } from "@/lib/v2-build-view";
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
  recordRecoveryCheck,
  recordRecoveryCorrectionReturn,
  recordRecoveryInvestigationReturn,
  recordRecoverySymptom,
  recordReturn,
  acceptRecoveryPrompt,
  handoffRecoveryPrompt,
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
  const [loadStatus, setLoadStatus] = useState<BuildPageLoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [promptText, setPromptText] = useState("");
  const [effort, setEffort] = useState<EffortCategory | "">("");
  const [editingReview, setEditingReview] = useState(false);
  const [showWhy, setShowWhy] = useState(false);
  const [agentHelp, setAgentHelp] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const [observation, setObservation] = useState("");
  const [recoverySymptom, setRecoverySymptom] = useState("");
  const [lastKnownWorking, setLastKnownWorking] = useState("");
  const [lastKnownCertainty, setLastKnownCertainty] = useState<"yes" | "no" | "unsure">("unsure");
  const [investigationFinding, setInvestigationFinding] = useState("");
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
    setLoadStatus("loading");
    setData(null);
    setError(null);
    try {
      const [project, current, plan, preferences, recent] = await Promise.all([
        getV2Project(id), getCurrentChange(id), getV2Plan(id), getPreferences(), getRecentChanges(id)
      ]);
      setSoundEnabled(preferences.dialogue_sound_enabled);
      if (!current.current_change) {
        const latest = recent.recent_changes[0];
        setCompleted(latest ? { observation: latest.observation, goal: latest.goal } : null);
        setLoadStatus(resolveLoadedBuildStatus(false, Boolean(latest)));
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
      setCompleted(null);
      setLoadStatus(resolveLoadedBuildStatus(true, false));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Couldn't load this build.");
      setLoadStatus("error");
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
        if (successMessage) setAnnouncement(successMessage);
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

  const submitRecoverySymptom = () => {
    if (!data || !recoverySymptom.trim()) {
      setError("Describe the first thing you actually observed."); return;
    }
    const identity = commandFor(
      "recovery-symptom",
      `${data.change.id}:${data.build.current_change_version}:${recoverySymptom.trim()}:${lastKnownCertainty}`,
      true
    );
    void runMutation(() => recordRecoverySymptom(
      id, data.change.id, data.build.current_change_version,
      identity.relatedId!, identity.commandId, recoverySymptom.trim(),
      lastKnownWorking.trim() || null, lastKnownCertainty
    ).then((result) => {
      resolveCommand("recovery-symptom", identity.commandId);
      setRecoverySymptom(""); setLastKnownWorking(""); return result;
    }), "Observation saved. Investigation is ready.");
  };

  const approveRecovery = () => {
    if (!data?.build.recovery_case) return;
    const identity = commandFor(
      "recovery-accept",
      `${data.change.id}:${data.build.current_change_version}:${data.build.prompt_draft_version}:${data.build.recovery_case.id}`
    );
    void runMutation(() => acceptRecoveryPrompt(
      id, data.change.id, data.build.current_change_version,
      data.build.prompt_draft_version, data.build.recovery_case!.id,
      data.build.build_stage === "recovery_investigate" ? "diagnostic" : "correction",
      identity.commandId
    ).then((result) => {
      resolveCommand("recovery-accept", identity.commandId); return result;
    }), "Recovery prompt approved.");
  };

  const copyRecoveryAndHandoff = async () => {
    const recovery = data?.build.recovery_case;
    const prompt = data?.build.accepted_prompt_version;
    if (!data || !recovery || !prompt || !data.build.exact_handoff_prompt) return;
    try { await navigator.clipboard.writeText(data.build.exact_handoff_prompt); }
    catch { setError("Clipboard access is unavailable. Select and copy the prompt manually; it has not been handed off yet."); return; }
    const identity = commandFor(
      "recovery-handoff",
      `${data.change.id}:${data.build.current_change_version}:${recovery.id}:${prompt.id}:${prompt.version}`
    );
    await runMutation(() => handoffRecoveryPrompt(
      id, data.change.id, data.build.current_change_version, recovery.id,
      prompt.id, prompt.version, identity.commandId
    ).then((result) => {
      resolveCommand("recovery-handoff", identity.commandId); return result;
    }), "Prompt copied and marked as handed off.");
  };

  const submitInvestigationFinding = () => {
    if (!data?.build.recovery_case || !investigationFinding.trim()) {
      setError("Record the useful code or behavior finding—not whether the AI said it fixed it."); return;
    }
    const identity = commandFor(
      "recovery-finding",
      `${data.change.id}:${data.build.current_change_version}:${data.build.recovery_case.id}:${investigationFinding.trim()}`
    );
    void runMutation(() => recordRecoveryInvestigationReturn(
      id, data.change.id, data.build.current_change_version,
      data.build.recovery_case!.id, investigationFinding.trim(), identity.commandId
    ).then((result) => {
      resolveCommand("recovery-finding", identity.commandId);
      setInvestigationFinding(""); return result;
    }), "Investigation finding saved as a coding-agent claim.");
  };

  const returnFromCorrection = () => {
    if (!data?.build.recovery_case) return;
    const identity = commandFor(
      "recovery-correction-return",
      `${data.change.id}:${data.build.current_change_version}:${data.build.recovery_case.id}`,
      true
    );
    void runMutation(() => recordRecoveryCorrectionReturn(
      id, data.change.id, data.build.current_change_version,
      data.build.recovery_case!.id, identity.relatedId!, identity.commandId
    ).then((result) => {
      resolveCommand("recovery-correction-return", identity.commandId); return result;
    }), "Correction return saved. Now recheck it yourself.");
  };

  const submitRecoveryRecheck = (result: "worked" | "did_not_work" | "unsure") => {
    const recovery = data?.build.recovery_case;
    const check = data?.build.active_check;
    if (!data || !recovery || !check || !observation.trim()) {
      setError("Describe exactly what you observed when you personally tried the recheck."); return;
    }
    const identity = commandFor(
      "recovery-recheck",
      `${data.change.id}:${data.build.current_change_version}:${check.id}:${check.version}:${result}:${observation.trim()}`,
      result === "unsure"
    );
    void runMutation(() => recordRecoveryCheck(
      id, data.change.id, check.id, data.build.current_change_version,
      check.version, recovery.id, result, observation.trim(),
      result === "unsure" ? identity.relatedId! : null, identity.commandId
    ).then((response) => {
      resolveCommand("recovery-recheck", identity.commandId);
      setObservation(""); return response;
    }), result === "worked" ? "Successful recheck saved." :
      result === "unsure" ? "Uncertainty saved. The recheck remains open." :
      "Failed recheck saved. Recovery returned to investigation.");
  };

  const complete = async () => {
    if (!data || !planItem || !data.build.active_check?.student_observation) return;
    setBusy(true); setError(null);
    try {
      const result = await completeCurrentChange(id, data.change.id,
        data.build.current_change_version, data.project.plan_version, planItem.version);
      setCompleted({ observation: result.check.student_observation ?? "Check completed.",
        goal: data.change.goal_snapshot });
      setData(null);
      setLoadStatus("completed");
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
    if (!data || !interaction
        || !["prebuild", "understanding"].includes(interaction.context)) return;
    const context = interaction.context as "prebuild" | "understanding";
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
      setAnnouncement("Prompt copied.");
    } catch {
      setError("Clipboard access is unavailable. You can select the prompt and copy it manually.");
    }
  };

  if (loadStatus === "loading") {
    return <div className="v2-page v2-build-page"><V2Card><V2Skeleton lines={7} /></V2Card></div>;
  }

  if (loadStatus === "error") {
    return (
      <div className="v2-page v2-page-narrow">
        <V2Card>
          <h1>Build couldn’t load</h1>
          <V2Notice tone="error">{error ?? "Couldn't load this build."}</V2Notice>
          <div className="v2-action-row">
            <V2Button type="button" onClick={() => void load()}>Try again</V2Button>
            <Link className="v2-button v2-button-secondary" href={`/app/project/${id}`}>Back to Project</Link>
          </div>
        </V2Card>
      </div>
    );
  }

  if (loadStatus === "empty") {
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

  if (loadStatus === "completed" && completed) return <div className="v2-page v2-page-narrow"><V2Card className="v2-complete-card">
    <p className="v2-card-label">Done</p><h1>{completed.goal}</h1>
    <p><span aria-hidden="true">✓</span> Checked: {completed.observation}</p>
    <div className="v2-action-row"><Link className="v2-button v2-button-primary" href={`/app/project/${id}`}>Back to Project</Link>
      <Link className="v2-button v2-button-secondary" href={`/app/project/${id}`}>Keep building</Link></div>
  </V2Card></div>;

  const recoveryActive = Boolean(
    data?.build.recovery_case || data?.change.lifecycle_state === "recovering"
  );

  return (
    <div className="v2-page v2-build-page">
      {data && (
        <>
          <header className={`v2-build-header${recoveryActive ? " is-recovery" : ""}`}>
            <div>
              <p className="v2-eyebrow">{recoveryActive ? "Recovery" : data.project.display_name}</p>
              <h1>{data.change.goal_snapshot}</h1>
              {recoveryActive && <p>Let’s figure out what happened before we change more code.</p>}
            </div>
            {data.build.selected_agent && <span className="v2-agent-badge">{data.build.selected_agent.display_name}</span>}
          </header>

          {conflict && <V2Notice>{conflict}</V2Notice>}
          {error && <V2Notice tone="error">{error}</V2Notice>}
          {effortMessage && data.build.build_stage !== "choose_effort" && (
            <V2Notice>{effortMessage}</V2Notice>
          )}
          <p className="sr-only" role="status" aria-live="polite">{announcement}</p>

          <div className="v2-conversation">
            {recoveryActive && (
              <ol className="v2-recovery-progress" aria-label="Recovery progress">
                {[
                  ["Observe", "recovery_symptom"],
                  ["Investigate", "recovery_investigate"],
                  ["Correct", "recovery_correct"],
                  ["Recheck", "recovery_recheck"],
                ].map(([label, step]) => (
                  <li key={step} aria-current={data.change.resume_step === step ? "step" : undefined}>
                    {label}
                  </li>
                ))}
              </ol>
            )}
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
                {data.build.build_stage === "check_failed" && <V2Dialogue soundEnabled={soundEnabled} text="That result doesn’t support completion yet. Your work is saved; Recovery will continue from what you observed." />}
                {data.build.build_stage === "recovery_symptom" && <V2Dialogue soundEnabled={soundEnabled} text="Something went wrong. Tell me what actually happened—without guessing at the cause yet." />}
                {data.build.build_stage === "recovery_investigate" && <V2Dialogue soundEnabled={soundEnabled} text="Investigate first. This prompt asks your coding AI to inspect without changing anything." />}
                {data.build.build_stage === "recovery_investigation_handoff" && <V2Dialogue soundEnabled={soundEnabled} text="Your investigation prompt is ready. It tells your coding AI not to edit yet." />}
                {data.build.build_stage === "recovery_investigation_return" && <V2Dialogue soundEnabled={soundEnabled} text="What did it find? Record the useful code or behavior evidence, not a claim that it fixed the bug." />}
                {data.build.build_stage === "recovery_correct" && <V2Dialogue soundEnabled={soundEnabled} text="Now make one targeted correction supported by the investigation." />}
                {data.build.build_stage === "recovery_correction_handoff" && <V2Dialogue soundEnabled={soundEnabled} text="The correction prompt is ready. It keeps the change narrow and preserves unrelated behavior." />}
                {data.build.build_stage === "recovery_correction_return" && <V2Dialogue soundEnabled={soundEnabled} text="Welcome back. The coding AI’s claim is not the check—try the behavior yourself next." />}
                {data.build.build_stage === "recovery_recheck" && <V2Dialogue soundEnabled={soundEnabled} text="Try it again yourself and record only what you actually observe." />}
              </div>
            </div>

            {data.build.recovery_case && (
              <V2Card className="v2-recovery-evidence" aria-label="Recovery evidence summary">
                <p className="v2-card-label">What we know</p>
                <p><strong>Student observed:</strong> {data.build.recovery_case.observed_symptom}</p>
                {data.build.recovery_case.last_known_working_statement && (
                  <p><strong>Student remembers:</strong> {data.build.recovery_case.last_known_working_statement}</p>
                )}
                {data.build.recovery_case.investigation_finding && (
                  <p><strong>Coding AI suggested:</strong> {data.build.recovery_case.investigation_finding}</p>
                )}
                <p className="v2-muted">Coding-agent findings remain hypotheses until a personal recheck supports them.</p>
              </V2Card>
            )}

            {data.build.build_stage === "recovery_symptom" && (
              <V2Card className="v2-stage-card v2-recovery-card">
                <p className="v2-card-label">Something went wrong</p>
                <h2>What actually happened?</h2>
                <label className="v2-field-label" htmlFor="v2-recovery-symptom">
                  What did you try, and what happened instead?
                </label>
                <textarea id="v2-recovery-symptom" rows={5} value={recoverySymptom}
                  onChange={(event) => setRecoverySymptom(event.target.value)} disabled={busy}
                  placeholder="When I click Sign In, the button spins and then shows ‘Unauthorized.’" />
                <label className="v2-field-label" htmlFor="v2-last-working">
                  What, if anything, was working before? <span className="v2-muted">Optional</span>
                </label>
                <textarea id="v2-last-working" rows={3} value={lastKnownWorking}
                  onChange={(event) => setLastKnownWorking(event.target.value)} disabled={busy} />
                <fieldset className="v2-inline-fieldset">
                  <legend>Was it working before the latest change?</legend>
                  {(["yes", "no", "unsure"] as const).map((value) => (
                    <label key={value}><input type="radio" name="last-working"
                      checked={lastKnownCertainty === value}
                      onChange={() => setLastKnownCertainty(value)} />
                      <span>{value === "unsure" ? "I’m not sure" : value === "yes" ? "Yes" : "No"}</span>
                    </label>
                  ))}
                </fieldset>
                {data.build.teaching?.hint_text && <V2Notice>{data.build.teaching.hint_text}</V2Notice>}
                <div className="v2-action-row">
                  {data.build.teaching?.can_request_help && (
                    <V2Button tone="secondary" onClick={askForHelp} disabled={busy}>
                      {data.build.teaching.hint_level === "none" ? "Need help?" : "Show me more"}
                    </V2Button>
                  )}
                  <V2Button onClick={submitRecoverySymptom} disabled={busy}>
                    {busy ? "Saving…" : "Save observation"}
                  </V2Button>
                </div>
              </V2Card>
            )}

            {(data.build.build_stage === "recovery_investigate" ||
              data.build.build_stage === "recovery_correct") && data.build.recovery_case && (
              <V2Card className="v2-stage-card v2-prompt-card v2-recovery-card">
                <p className="v2-card-label">
                  {data.build.build_stage === "recovery_investigate" ? "Investigation prompt" : "Targeted correction"}
                </p>
                <h2>{data.build.build_stage === "recovery_investigate" ? "Inspect before editing" : "Make one narrow correction"}</h2>
                {data.change.risk === "slowdown" && (
                  <V2Notice>This prompt touches a consequential boundary. Recovery keeps the required slowdown and personal recheck.</V2Notice>
                )}
                <pre tabIndex={0}>{data.build.prompt_draft}</pre>
                {data.build.build_stage === "recovery_investigate" && (
                  <details className="v2-why-panel"><summary>Why investigate first?</summary>
                    <p>A patch without evidence can change more code while hiding the actual problem. Investigation gives the correction a reason.</p>
                  </details>
                )}
                {data.build.teaching?.hint_text && <V2Notice>{data.build.teaching.hint_text}</V2Notice>}
                <div className="v2-action-row">
                  {data.build.teaching?.can_request_help && (
                    <V2Button tone="secondary" onClick={askForHelp} disabled={busy}>
                      {data.build.teaching.hint_level === "none" ? "Need help?" : "Show me more"}
                    </V2Button>
                  )}
                  <V2Button onClick={approveRecovery} disabled={busy}>
                    {busy ? "Saving…" : "Use this prompt"}
                  </V2Button>
                </div>
              </V2Card>
            )}

            {(data.build.build_stage === "recovery_investigation_handoff" ||
              data.build.build_stage === "recovery_correction_handoff") && (
              <V2Card className="v2-stage-card v2-handoff-card v2-recovery-card">
                <p className="v2-card-label">Ready for {data.build.selected_agent?.display_name ?? "your coding AI"}</p>
                <h2>{data.build.build_stage === "recovery_investigation_handoff" ? "Investigate—do not edit" : "One targeted correction"}</h2>
                <pre tabIndex={0}>{data.build.exact_handoff_prompt}</pre>
                <p>Codize prepares the prompt. Your coding AI inspects or edits the project.</p>
                <V2Button onClick={() => void copyRecoveryAndHandoff()} disabled={busy}>
                  {busy ? "Handing off…" : "Copy prompt & hand off"}
                </V2Button>
              </V2Card>
            )}

            {data.build.build_stage === "recovery_investigation_return" && (
              <V2Card className="v2-stage-card v2-recovery-card">
                <p className="v2-card-label">Investigation handoff</p>
                <h2>What did it find?</h2>
                {!returnReady ? (
                  <div className="v2-action-row">
                    <V2Button onClick={() => setReturnReady(true)}>I’m back</V2Button>
                    <V2Button tone="secondary" onClick={() => void copyAgain()}>Copy prompt again</V2Button>
                  </div>
                ) : (
                  <>
                    <label className="v2-field-label" htmlFor="v2-investigation-finding">
                      Useful code or behavior finding
                    </label>
                    <textarea id="v2-investigation-finding" rows={5}
                      value={investigationFinding}
                      onChange={(event) => setInvestigationFinding(event.target.value)}
                      placeholder="The agent found that the request appears to omit the Authorization header in api.ts."
                      disabled={busy} />
                    <p className="v2-muted">This is saved as a coding-agent suggestion, not a verified root cause.</p>
                    <V2Button onClick={submitInvestigationFinding} disabled={busy}>
                      {busy ? "Saving…" : "Save finding"}
                    </V2Button>
                  </>
                )}
              </V2Card>
            )}

            {data.build.build_stage === "recovery_correction_return" && (
              <V2Card className="v2-stage-card v2-recovery-card">
                <p className="v2-card-label">Correction handoff</p>
                <h2>Ready to try it yourself?</h2>
                <p>Return after your coding AI finishes. Its claim does not decide whether the correction worked.</p>
                <div className="v2-action-row">
                  <V2Button onClick={returnFromCorrection} disabled={busy}>
                    {busy ? "Saving…" : "I’m back — recheck"}
                  </V2Button>
                  <V2Button tone="secondary" onClick={() => void copyAgain()}>Copy prompt again</V2Button>
                </div>
              </V2Card>
            )}

            {data.build.build_stage === "recovery_recheck" && data.build.active_check && (
              <V2Card className="v2-stage-card v2-check-card v2-recovery-card">
                <p className="v2-card-label">Try it again</p>
                <h2>{data.build.active_check.check_plan}</h2>
                {data.build.last_check_result === "unsure" && (
                  <V2Notice>UNSURE stays incomplete. Try the check again and record the next real observation.</V2Notice>
                )}
                <label className="v2-field-label" htmlFor="v2-recovery-observation">What did you personally observe?</label>
                <textarea id="v2-recovery-observation" rows={4} value={observation}
                  onChange={(event) => setObservation(event.target.value)} disabled={busy} />
                {data.build.teaching?.hint_text && <V2Notice>{data.build.teaching.hint_text}</V2Notice>}
                <p className="v2-muted">The coding AI saying “it works” is not a recheck.</p>
                <div className="v2-return-choices">
                  <V2Button onClick={() => submitRecoveryRecheck("worked")} disabled={busy}>Pass — worked</V2Button>
                  <V2Button tone="secondary" onClick={() => submitRecoveryRecheck("did_not_work")} disabled={busy}>Fail — didn’t work</V2Button>
                  <V2Button tone="ghost" onClick={() => submitRecoveryRecheck("unsure")} disabled={busy}>Unsure</V2Button>
                </div>
                {data.build.teaching?.can_request_help && (
                  <V2Button tone="ghost" onClick={askForHelp} disabled={busy}>
                    {data.build.teaching.hint_level === "none" ? "Need help?" : "Show me more"}
                  </V2Button>
                )}
              </V2Card>
            )}

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
