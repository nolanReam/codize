"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import NotReady from "@/components/NotReady";
import {
  ApiError,
  evaluateGate,
  getCurrentGate,
  getCurrentPhase,
  startGate,
  submitGateAnchor,
  submitGateAnswer,
} from "@/lib/api";
import type { GateCurrent, GateEvaluationResult, PhaseView } from "@/lib/types";

const STATE_PILL: Record<GateCurrent["state"], { label: string; cls: string }> = {
  not_started: { label: "READY TO DEFEND", cls: "accent" },
  in_progress: { label: "DEFENSE IN PROGRESS", cls: "warn" },
  cooldown: { label: "COOLDOWN", cls: "danger" },
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

  const pill = gate ? STATE_PILL[gate.state] : undefined;

  return (
    <>
      <div className="spread">
        <div>
          <h1 className="page-title">Project Defense</h1>
          <p className="page-sub">
            Defend what you built — in your own words, about your own implementation. The gate
            asks three questions specific to your project. Generic, textbook answers don&rsquo;t
            pass, because they don&rsquo;t prove <em>you</em> understand it.
          </p>
        </div>
        {pill && !outcome && <span className={`pill ${pill.cls}`}>{pill.label}</span>}
      </div>

      <Async loading={loading} error={error} onRetry={load}>
        {outcome ? (
          <Outcome outcome={outcome} onReset={load} />
        ) : (
          gate && (
            <>
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
                <PassedView />
              ) : (
                <ReadyView phase={phase} busy={busy} onBegin={handleBegin} flowError={flowError} />
              )}

              <GateExplainer />
            </>
          )
        )}
      </Async>
    </>
  );
}

// --- ready to start ----------------------------------------------------------

function ReadyView({
  phase,
  busy,
  onBegin,
  flowError,
}: {
  phase: PhaseView | null;
  busy: boolean;
  onBegin: () => void;
  flowError: string | null;
}) {
  return (
    <div className="card">
      <h3>Ready to defend</h3>
      {phase && (
        <div className="kv">
          <span className="k">Phase</span>
          <span>
            {phase.phase} — {phase.phase_title}
          </span>
        </div>
      )}
      {phase?.core_concept && (
        <p className="muted" style={{ marginTop: 8 }}>
          You&rsquo;ll be defending your understanding of: {phase.core_concept}
        </p>
      )}
      <p style={{ marginTop: 12 }}>
        You&rsquo;ll start with a one-sentence <strong>anchor statement</strong> — a concrete
        piece of what you built, naming a real variable, function, or database field. Then Codize
        asks three probing questions about it. Take your time; there&rsquo;s no timer once
        you&rsquo;ve begun.
      </p>
      {flowError && (
        <div className="notice error" style={{ marginTop: 12 }}>
          {flowError}
        </div>
      )}
      <div className="row" style={{ marginTop: 14 }}>
        <button className="btn primary" onClick={onBegin} disabled={busy}>
          {busy ? "Starting…" : "Begin defense"}
        </button>
        <Link href="/app/phase" className="btn">
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
      <div className="card" style={{ borderColor: "var(--accent)" }}>
        {isAnchor ? (
          <>
            <h3>Step 1 — Anchor statement</h3>
            <p style={{ marginBottom: 10 }}>{gate.anchor_prompt}</p>
            <p className="muted" style={{ marginBottom: 10 }}>
              Name at least one real variable, function, or database field from your
              implementation — that&rsquo;s what makes the defense about <em>your</em> project.
            </p>
          </>
        ) : (
          <>
            <h3>Question {turnNo} of 3</h3>
            <p style={{ marginBottom: 10 }}>{pending?.question}</p>
            {isEvaluate && (
              <p className="muted" style={{ marginBottom: 10 }}>
                Last question. After you submit this, Codize evaluates your defense.
              </p>
            )}
          </>
        )}

        <textarea
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
        />

        {flowError && (
          <div className="notice error" style={{ marginTop: 10 }}>
            {flowError}
          </div>
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
          <div className="notice ok">You passed the defense for this phase.</div>
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
            <Link href="/app/report" className="btn primary">
              Add this to your Defense Report
            </Link>
            <Link href="/app" className="btn">
              Back to cockpit
            </Link>
            <Link href="/app/phase" className="btn">
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
      <div className="notice info">This defense didn&rsquo;t pass yet — and that&rsquo;s useful signal.</div>
      <p style={{ marginTop: 12 }}>{outcome.reason}</p>
      {cooldownMin != null && (
        <p className="muted" style={{ marginTop: 10 }}>
          You can try again in about {cooldownMin} minute{cooldownMin === 1 ? "" : "s"}. Use the
          time to walk your own code — the gate rewards specifics about what <em>you</em> built,
          not textbook definitions.
        </p>
      )}
      <div className="row" style={{ marginTop: 16 }}>
        <Link href="/app/phase/review" className="btn">
          Revisit Review Board
        </Link>
        <Link href="/app/phase/evidence" className="btn">
          Evidence Panel
        </Link>
        <Link href="/app/phase/verify" className="btn">
          Verification Lab
        </Link>
        <button className="btn" onClick={onReset}>
          Back to gate
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
        A recent attempt didn&rsquo;t pass.
        {cooldownMin != null && (
          <>
            {" "}
            You can try again in about {cooldownMin} minute{cooldownMin === 1 ? "" : "s"}.
          </>
        )}{" "}
        Use the time to re-read the phase concept and walk your own code.
      </p>
      {gate.reason && (
        <div className="kv" style={{ marginTop: 8 }}>
          <span className="k">Last feedback</span>
          <span className="muted">{gate.reason}</span>
        </div>
      )}
      <div className="row" style={{ marginTop: 14 }}>
        <Link href="/app/phase/review" className="btn">
          Revisit your work
        </Link>
        <Link href="/app/phase" className="btn">
          Phase workspace
        </Link>
      </div>
    </div>
  );
}

function PassedView() {
  return (
    <div className="card">
      <div className="notice ok">You&rsquo;ve passed this phase&rsquo;s defense.</div>
      <p style={{ marginTop: 12 }}>
        This is the final phase&rsquo;s gate — there&rsquo;s nothing left to defend here. Pull
        everything together in your Project Defense Report.
      </p>
      <div className="row" style={{ marginTop: 14 }}>
        <Link href="/app/report" className="btn primary">
          Open Defense Report
        </Link>
        <Link href="/app" className="btn">
          Cockpit
        </Link>
      </div>
    </div>
  );
}

// --- shared explainer --------------------------------------------------------

function GateExplainer() {
  return (
    <div className="card" style={{ borderColor: "var(--border-strong)" }}>
      <h3>How the defense works</h3>
      <ol className="trap-steps" style={{ marginTop: 0 }}>
        <li>
          You give an <strong>anchor statement</strong> — a concrete piece of your implementation
          you&rsquo;re ready to defend.
        </li>
        <li>Codize asks three questions specific to what you built.</li>
        <li>
          A separate evaluation decides pass or fail on structural understanding, ripple effects,
          and implementation specificity.
        </li>
        <li>
          <strong>Pass</strong> and you advance to the next phase. <strong>Fail</strong> and
          there&rsquo;s a short cooldown before you can retry — no penalty beyond the wait.
        </li>
      </ol>
      <p className="muted" style={{ marginTop: 12 }}>
        Ticking tasks never advances a phase — only passing this defense does. The gate uses the
        existing evaluation engine and is not yet aware of your saved workflow artifacts; those are
        for your own reference and your Defense Report.
      </p>
    </div>
  );
}
