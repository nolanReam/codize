"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import AdaptiveStepGuide from "@/components/AdaptiveStepGuide";
import DefenseContextSummaryBlock, {
  type DefenseContextSummaryState,
} from "@/components/DefenseContextSummary";
import GuideCard from "@/components/GuideCard";
import NotReady from "@/components/NotReady";
import { useGuidedProjectNavigation } from "@/components/GuidedProjectNavigationProvider";
import {
  ApiError,
  evaluateGate,
  getCurrentGate,
  getCurrentPhase,
  getDefenseContextSummary,
  startGate,
  submitGateAnchor,
  submitGateAnswer,
} from "@/lib/api";
import { useDraft } from "@/lib/drafts";
import type {
  DefenseContextSummary,
  GateCurrent,
  GateEvaluationResult,
  PhaseView,
} from "@/lib/types";

// Cooldown is amber, not red — a study break, not an error (M13E.4).
const STATE_PILL: Record<GateCurrent["state"], { label: string; cls: string }> = {
  not_started: { label: "PROJECT DEFENSE", cls: "accent" },
  in_progress: { label: "DEFENSE IN PROGRESS", cls: "warn" },
  cooldown: { label: "COOLDOWN", cls: "warn" },
  passed: { label: "PASSED", cls: "ok" },
};

// The question number the student is currently answering (1–3), from the last
// (unanswered) turn. Anchor step (next_action turn1, no turns yet) returns 0.
function pendingTurnNumber(gate: GateCurrent): number {
  const turns = gate.turns ?? [];
  return turns.length ? turns[turns.length - 1].turn : 0;
}

// Live Interrogation Gate (M13C.2) — a real defense flow over the M9 backend:
// anchor statement → three implementation-specific turns → a separate
// evaluation. Raw scores, evaluator reasoning, and internal prompts never reach
// this UI by backend design; this page only shows what the backend returns.
export default function GatePage() {
  const guided = useGuidedProjectNavigation();
  const [gate, setGate] = useState<GateCurrent | null>(null);
  const [phase, setPhase] = useState<PhaseView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notReady, setNotReady] = useState(false);

  // Active-flow state.
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [flowError, setFlowError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<GateEvaluationResult | null>(null);

  // Context summary (M14C): metadata-only "what can questions draw on" —
  // loaded separately so a slow or failing summary NEVER blocks the gate.
  // Fetched fresh on every mount, so artifacts saved on other pages are
  // reflected the next time the student lands here (no polling needed).
  const [summary, setSummary] = useState<DefenseContextSummary | null>(null);
  const [summaryState, setSummaryState] = useState<DefenseContextSummaryState>("loading");
  const loadSummary = useCallback(async () => {
    setSummaryState("loading");
    try {
      setSummary(await getDefenseContextSummary());
      setSummaryState("ready");
    } catch {
      setSummaryState("error");
    }
  }, []);
  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  // Unsaved-draft persistence (M13E.2): the typed answer survives switching
  // tabs mid-defense. Scoped per session AND per step, so a restored draft can
  // never appear under the wrong question; cleared when the step submits.
  const draftSurface =
    gate?.state === "in_progress" && gate.gate_session_id && gate.next_action
      ? `gate:${gate.gate_session_id}:${gate.next_action}`
      : null;
  const draft = useDraft<string>(draftSurface);
  const restoredDraft = draft.ready ? draft.restored : null;
  useEffect(() => {
    if (restoredDraft) setInput((prev) => (prev === "" ? restoredDraft : prev));
  }, [restoredDraft]);
  const saveDraft = draft.save;
  useEffect(() => {
    saveDraft(input);
  }, [input, saveDraft]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotReady(false);
    setOutcome(null);
    setFlowError(null);
    try {
      const [g, p] = await Promise.allSettled([getCurrentGate(), getCurrentPhase()]);
      if (g.status === "rejected") throw g.reason;
      setGate(g.value);
      setPhase(p.status === "fulfilled" ? p.value : null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) setNotReady(true);
      else setError(err instanceof ApiError ? err.message : "Couldn't load the gate.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runStep(fn: () => Promise<void>) {
    setBusy(true);
    setFlowError(null);
    try {
      await fn();
      draft.clear(); // the step submitted — its local draft is now stale
      setInput("");
    } catch (err) {
      // 422 (invalid anchor) and 502 (generation failed) both leave the session
      // exactly where it was — the same step is safely retryable, so keep the
      // typed input and show the safe message.
      setFlowError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const handleBegin = () =>
    runStep(async () => {
      const started = await startGate();
      setGate({
        phase: started.phase,
        phase_title: started.phase_title,
        state: "in_progress",
        gate_session_id: started.gate_session_id,
        next_action: "turn1",
        anchor_prompt: started.anchor_prompt,
        anchor_statement: null,
        turns: [],
      });
    });

  const handleAnchor = () =>
    runStep(async () => {
      if (!gate?.gate_session_id) return;
      const anchor = input.trim();
      const result = await submitGateAnchor(gate.gate_session_id, anchor);
      setGate((prev) =>
        prev
          ? {
              ...prev,
              anchor_statement: anchor,
              anchor_prompt: undefined,
              next_action: "turn2",
              turns: [{ turn: 1, question: result.question, answer: null }],
            }
          : prev
      );
    });

  const handleAnswer = () =>
    runStep(async () => {
      if (!gate?.gate_session_id || !gate.next_action) return;
      const answer = input.trim();
      const sessionId = gate.gate_session_id;

      if (gate.next_action === "evaluate") {
        const result = await evaluateGate(sessionId, answer);
        setOutcome(result);
        return;
      }

      const turn = gate.next_action === "turn2" ? 2 : 3;
      const result = await submitGateAnswer(sessionId, turn, answer);
      setGate((prev) => {
        if (!prev) return prev;
        const turns = [...(prev.turns ?? [])];
        if (turns.length) turns[turns.length - 1] = { ...turns[turns.length - 1], answer };
        turns.push({ turn: result.turn, question: result.question, answer: null });
        const next = result.turn === 2 ? "turn3" : "evaluate";
        return { ...prev, turns, next_action: next };
      });
    });

  if (notReady) return <NotReady title="Project Defense" />;

  const pill = gate
    ? gate.state === "not_started" && gate.readiness?.formal_ready === false
      ? { label: "NOT READY YET", cls: "warn" }
      : gate.state === "not_started" && gate.readiness?.state === "retry"
        ? { label: "READY TO RETRY", cls: "warn" }
        : gate.state === "not_started"
          ? { label: "READY FOR PROJECT DEFENSE", cls: "accent" }
          : STATE_PILL[gate.state]
    : undefined;

  return (
    <>
      <div className="spread">
        <div>
          <h1 className="page-title">Project Defense</h1>
          <p className="page-sub">
            Three questions about <em>your</em> code, answered in your own words. Not a test of
            intelligence — a check that you understand what you shipped.
          </p>
        </div>
        {pill && !outcome && <span className={`pill ${pill.cls}`}>{pill.label}</span>}
      </div>
      <AdaptiveStepGuide stage="defense" />

      <Async loading={loading} error={error} onRetry={load}>
        <div className="defense-page-body">
          {outcome ? (
            <Outcome outcome={outcome} onReset={load} />
          ) : (
            gate && (
              <div className="workspace">
                <div>
                  {gate.state === "in_progress" ? (
                    <ActiveFlow
                      gate={gate}
                      input={input}
                      setInput={setInput}
                      busy={busy}
                      flowError={flowError}
                      onAnchor={handleAnchor}
                      onAnswer={handleAnswer}
                    />
                  ) : gate.state === "cooldown" ? (
                    <CooldownView gate={gate} />
                  ) : gate.state === "passed" ? (
                    <PassedView gate={gate} />
                  ) : gate.readiness?.formal_ready === false ? (
                    <BlockedView
                      gate={gate}
                      continueAction={guided.navigation.continueAction}
                    />
                  ) : (
                    <ReadyView
                      phase={phase}
                      busy={busy}
                      onBegin={handleBegin}
                      flowError={flowError}
                      summary={summary}
                      summaryState={summaryState}
                      onRetrySummary={loadSummary}
                    />
                  )}
                </div>

                <aside className="ws-rail" aria-label="Guidance">
                  <GateExplainer />
                </aside>
              </div>
            )
          )}
        </div>
      </Async>
    </>
  );
}

function BlockedView({
  gate,
  continueAction,
}: {
  gate: GateCurrent;
  continueAction: {
    label: string;
    href: string | null;
    reason: string;
  };
}) {
  const blockers = gate.readiness?.blockers ?? [];
  return (
    <section className="card primary" aria-labelledby="defense-not-ready-title">
      <div className="notice info" role="status" aria-live="polite">
        <strong id="defense-not-ready-title">Not ready for formal Project Defense yet</strong>
        <p>Finish the current phase record first. Nothing has failed, and your saved work remains available.</p>
      </div>
      <div className="row defense-recovery-actions" aria-describedby="defense-not-ready-title">
        {continueAction.href ? (
          <Link href={continueAction.href} className="btn primary">
            {continueAction.label}
          </Link>
        ) : (
          <Link href="/app" className="btn primary">
            Back to Project Home
          </Link>
        )}
        <Link href="/app#current-work" className="btn">
          Review phase tasks
        </Link>
      </div>
      <p className="muted defense-recovery-reason">{continueAction.reason}</p>
      {blockers.length > 0 && (
        <ol className="defense-prerequisites" aria-label="Project Defense prerequisites">
          {blockers.map((blocker) => (
            <li key={blocker.code}>
              <strong>{blocker.label}</strong>
              <span>{blocker.detail}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

// --- ready to start ----------------------------------------------------------

function ReadyView({
  phase,
  busy,
  onBegin,
  flowError,
  summary,
  summaryState,
  onRetrySummary,
}: {
  phase: PhaseView | null;
  busy: boolean;
  onBegin: () => void;
  flowError: string | null;
  summary: DefenseContextSummary | null;
  summaryState: DefenseContextSummaryState;
  onRetrySummary: () => void;
}) {
  return (
    <div className="card">
      <h2 className="section-title">Ready to defend</h2>
      {phase && (
        <div className="kv">
          <span className="k">Phase</span>
          <span>
            {phase.phase} — {phase.phase_title}
          </span>
        </div>
      )}
      <p style={{ marginTop: 12 }}>
        You&rsquo;ll name one real thing you built, then answer three questions about it.
        No timer, no trick questions — and <strong>you can keep your code open</strong> while
        you answer.
      </p>

      <DefenseContextSummaryBlock summary={summary} state={summaryState} onRetry={onRetrySummary} />

      <details className="help">
        <summary>What exactly will happen?</summary>
        <div className="help-body">
          <ol style={{ margin: "6px 0", paddingLeft: 20 }}>
            <li>
              You write a one-sentence <strong>anchor</strong> — a concrete piece of what you
              built. Like:
              <br />
              <span className="mono" style={{ fontSize: 12 }}>
                &ldquo;I built a likes_score variable and an update_likes_score() function.&rdquo;
              </span>
              <br />
              <span className="mono" style={{ fontSize: 12 }}>
                &ldquo;My POST /tasks route inserts into the tasks table with a user_id
                column.&rdquo;
              </span>
            </li>
            <li>Codize asks three questions specific to that anchor.</li>
            <li>
              A separate evaluation decides pass or fail. Nothing is graded until the final
              answer.
            </li>
          </ol>
        </div>
      </details>
      <details className="help">
        <summary>What makes a good answer?</summary>
        <div className="help-body">
          <ul>
            <li>Be specific about <em>your</em> code.</li>
            <li>Name real variables, files, functions, or fields.</li>
            <li>A generic textbook answer will not pass — even if it&rsquo;s technically right.</li>
            <li>&ldquo;I&rsquo;d have to check X&rdquo; is more honest than bluffing.</li>
          </ul>
          <p className="muted">
            Failing just means &ldquo;review and try again later&rdquo; — a short cooldown, no
            other penalty.
          </p>
        </div>
      </details>
      <div className="attempt-context-note">
        <strong>A stable record for this attempt</strong>
        <p>
          When this attempt begins, Codize keeps a stable server-owned view of the project record
          used for the questions. Later workflow edits do not rewrite this active Defense attempt.
        </p>
      </div>
      {flowError && (
        <div className="notice error" style={{ marginTop: 12 }}>
          {flowError}
        </div>
      )}
      <div className="row" style={{ marginTop: 14 }}>
        <button className="btn primary" onClick={onBegin} disabled={busy}>
          {busy ? "Starting…" : "Begin defense"}
        </button>
        <Link href="/app#current-phase" className="btn">
          Review the phase first
        </Link>
      </div>
    </div>
  );
}

// --- the turn-by-turn flow ---------------------------------------------------

function ActiveFlow({
  gate,
  input,
  setInput,
  busy,
  flowError,
  onAnchor,
  onAnswer,
}: {
  gate: GateCurrent;
  input: string;
  setInput: (v: string) => void;
  busy: boolean;
  flowError: string | null;
  onAnchor: () => void;
  onAnswer: () => void;
}) {
  const isAnchor = gate.next_action === "turn1";
  const isEvaluate = gate.next_action === "evaluate";
  const turnNo = pendingTurnNumber(gate);
  const answered = (gate.turns ?? []).filter((t) => t.answer != null);
  const pending = (gate.turns ?? []).find((t) => t.answer == null) ?? null;
  const maxLen = isAnchor ? 2000 : 8000;

  return (
    <>
      {/* Transcript so far — answered turns are read-only history. */}
      {gate.anchor_statement && (
        <div className="card">
          <h3>Your anchor</h3>
          <p className="mono" style={{ overflowWrap: "anywhere" }}>
            {gate.anchor_statement}
          </p>
        </div>
      )}
      {answered.map((t) => (
        <div className="card" key={t.turn}>
          <h3>Question {t.turn} of 3</h3>
          <p style={{ marginBottom: 10 }}>{t.question}</p>
          <div className="kv">
            <span className="k">Your answer</span>
            <span className="muted" style={{ overflowWrap: "anywhere" }}>
              {t.answer}
            </span>
          </div>
        </div>
      ))}

      {/* The step the student is on right now. */}
      <div className="card primary">
        {isAnchor ? (
          <>
            <h3>Step 1 — Anchor statement</h3>
            <p style={{ marginBottom: 10 }}>{gate.anchor_prompt}</p>
            <p className="muted" style={{ marginBottom: 10 }}>
              Name one exact thing from your code — like <code>likes_score</code>,{" "}
              <code>update_likes_score()</code>, <code>tasks.user_id</code>, or{" "}
              <code>app/models.py</code>. Plain phrasing is fine: &ldquo;the variable is called
              likes_score&rdquo; works.
            </p>
          </>
        ) : (
          <>
            {/* Subtle grounding label (M14C): questions draw on the project and
                any recorded work — per-question source attribution is never
                inferred client-side. The question stays the visual focus. */}
            <p
              className="muted"
              style={{
                fontSize: 11,
                margin: "0 0 6px",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Grounded in your project
            </p>
            <h3>Question {turnNo} of 3</h3>
            <p style={{ marginBottom: 10 }}>{pending?.question}</p>
            {isEvaluate && (
              <p className="muted" style={{ marginBottom: 10 }}>
                Last question. After you submit this, Codize evaluates your defense.
              </p>
            )}
          </>
        )}

        <label className="field-label" htmlFor="defense-response">
          {isAnchor ? "Your anchor" : "Your response"}
        </label>
        <p className="muted" id="defense-response-guidance">
          {isAnchor
            ? "Name one concrete implementation element."
            : "Explain the implementation in your own words."}
        </p>
        <textarea
          id="defense-response"
          rows={isAnchor ? 3 : 6}
          maxLength={maxLen}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            isAnchor
              ? "e.g. I built a POST /tasks route that inserts into the tasks table with a user_id ownership column."
              : "Answer in your own words, about your own code. Be specific."
          }
          disabled={busy}
          aria-invalid={flowError ? true : undefined}
          aria-describedby={`defense-response-guidance defense-response-limit${
            flowError ? " defense-response-error" : ""
          }`}
        />

        <p className="field-limit" id="defense-response-limit">
          {input.length.toLocaleString()} / {maxLen.toLocaleString()} characters
        </p>

        {flowError && (
          <div className="notice error" id="defense-response-error" role="alert" style={{ marginTop: 10 }}>
            {flowError}
          </div>
        )}

        {busy && (
          <p className="muted" role="status" aria-live="polite">
            {isEvaluate
              ? "Evaluating your Defense…"
              : isAnchor
                ? "Preparing your first question…"
                : "Preparing the next question…"}
          </p>
        )}

        <div className="row" style={{ marginTop: 12 }}>
          <button
            className="btn primary"
            disabled={busy || !input.trim()}
            onClick={isAnchor ? onAnchor : onAnswer}
          >
            {busy
              ? "Working…"
              : isAnchor
                ? "Submit anchor"
                : isEvaluate
                  ? "Submit final answer"
                  : "Submit answer"}
          </button>
          <span className="muted">Nothing is graded until the final answer.</span>
        </div>
      </div>
    </>
  );
}

// --- outcome (pass / fail) ---------------------------------------------------

function Outcome({ outcome, onReset }: { outcome: GateEvaluationResult; onReset: () => void }) {
  if (outcome.verdict === "PASS") {
    return (
      <>
        <div className="card">
          <div className="notice ok" role="status">
            <strong>Defense passed</strong>
          </div>
          <p>You completed Project Defense under Codize&rsquo;s current evaluation criteria.</p>
          <p style={{ marginTop: 12 }}>{outcome.reason}</p>
          {outcome.new_unlocks && outcome.new_unlocks.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <h3>Unlocked</h3>
              {outcome.new_unlocks.map((u) => (
                <div className="kv" key={u.id}>
                  <span className="k">Phase {u.phase}</span>
                  <span>{u.description}</span>
                </div>
              ))}
            </div>
          )}
          <div className="row" style={{ marginTop: 16 }}>
            <Link href={`/app/report?phase=${outcome.phase}`} className="btn primary">
              View Defense Report
            </Link>
            <Link href="/app" className="btn">
              Back to Project Home
            </Link>
            <Link href="/app#current-phase" className="btn">
              Open Phase {outcome.current_phase}
            </Link>
          </div>
        </div>
      </>
    );
  }

  const cooldownMin = outcome.cooldown_seconds
    ? Math.max(1, Math.ceil(outcome.cooldown_seconds / 60))
    : null;

  return (
    <div className="card">
      <div className="notice info" role="status">
        <strong>Defense needs another attempt</strong>
        <br />
        Review the feedback and your implementation, then try again after the cooldown.
      </div>
      <p style={{ marginTop: 12 }}>{outcome.reason}</p>
      {cooldownMin != null && (
        <p className="muted" style={{ marginTop: 10 }}>
          You can retry in about {cooldownMin} minute{cooldownMin === 1 ? "" : "s"} — a built-in
          study break. Open your own code and walk the part you were asked about; specifics are
          what pass.
        </p>
      )}
      <div className="row" style={{ marginTop: 16 }}>
        <Link href={`/app/report?phase=${outcome.phase}`} className="btn primary">
          View Defense Report
        </Link>
        <Link href="/app/phase/review" className="btn">
          Revisit Review
        </Link>
        <Link href="/app/phase/evidence" className="btn">
          Evidence
        </Link>
        <Link href="/app/phase/verify" className="btn">
          Verification
        </Link>
        <button className="btn" onClick={onReset}>
          Back to Project Defense
        </button>
      </div>
    </div>
  );
}

// --- cooldown / passed (from GET on load) ------------------------------------

function CooldownView({ gate }: { gate: GateCurrent }) {
  const cooldownMin =
    gate.cooldown_seconds_remaining != null
      ? Math.max(1, Math.ceil(gate.cooldown_seconds_remaining / 60))
      : null;
  return (
    <div className="card">
      <h3>Cooldown</h3>
      <div className="kv">
        <span className="k">Phase</span>
        <span>
          {gate.phase} — {gate.phase_title}
        </span>
      </div>
      <p className="notice info" style={{ marginTop: 12 }}>
        Last attempt didn&rsquo;t pass — normal part of the loop.
        {cooldownMin != null && (
          <>
            {" "}
            Retry opens in about {cooldownMin} minute{cooldownMin === 1 ? "" : "s"}.
          </>
        )}{" "}
        Good use of the break: open your code and re-walk the part you were asked about.
      </p>
      {gate.reason && (
        <div className="kv" style={{ marginTop: 8 }}>
          <span className="k">Last feedback</span>
          <span className="muted">{gate.reason}</span>
        </div>
      )}
      <div className="row" style={{ marginTop: 14 }}>
        <Link href={`/app/report?phase=${gate.phase}`} className="btn">
          View last Defense Report
        </Link>
        <Link href="/app/phase/review" className="btn">
          Revisit your work
        </Link>
        <Link href="/app" className="btn">
          Project Home
        </Link>
      </div>
    </div>
  );
}

function PassedView({ gate }: { gate: GateCurrent }) {
  return (
    <div className="card">
      <div className="notice ok">You&rsquo;ve passed this phase&rsquo;s defense.</div>
      <p style={{ marginTop: 12 }}>
        This is the final phase&rsquo;s Project Defense — there&rsquo;s nothing left to defend here. Pull
        everything together in your Project Defense Report.
      </p>
      <div className="row" style={{ marginTop: 14 }}>
        <Link href={`/app/report?phase=${gate.phase}`} className="btn primary">
          Open Defense Report
        </Link>
        <Link href="/app" className="btn">
          Project Home
        </Link>
      </div>
    </div>
  );
}

// --- shared explainer --------------------------------------------------------

function GateExplainer() {
  return (
    <>
      <div className="guide" style={{ borderColor: "var(--border-strong)" }}>
        <div style={{ padding: "12px 16px" }}>
          <p style={{ margin: 0 }}>
            <strong>While you answer:</strong> keep your code open, name real variables / files /
            functions, and be specific about <em>your</em> implementation. Generic textbook
            answers don&rsquo;t pass. Your typing survives tab switches.
          </p>
        </div>
      </div>
      <GuideCard title="How it works">
        <ol style={{ margin: "6px 0", paddingLeft: 18 }}>
          <li>Anchor: one concrete piece of what you built.</li>
          <li>Three questions about it.</li>
          <li>A separate evaluation decides pass / fail.</li>
          <li>Pass → next phase. Fail → short cooldown, then retry.</li>
        </ol>
        <p>
          Passing this is the only thing that advances a phase. Questions can draw on the work
          you recorded this phase — but pass / fail is decided only by how well{" "}
          <em>you</em> explain your own implementation.
        </p>
      </GuideCard>
    </>
  );
}
