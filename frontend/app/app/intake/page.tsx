"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import {
  ApiError,
  completeIntake,
  generateRoadmap,
  getIntakeQuestions,
  getIntakeStatus,
  submitIntakeAnswer,
} from "@/lib/api";
import type { IntakeQuestion, IntakeStatus } from "@/lib/types";

// Conversational intake — the spec's five mandatory, sequential questions.
// Question 1 is verbatim and unskippable; the backend enforces the order.
export default function IntakePage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<IntakeQuestion[]>([]);
  const [status, setStatus] = useState<IntakeStatus | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [archetypeName, setArchetypeName] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [q, s] = await Promise.all([getIntakeQuestions(), getIntakeStatus()]);
      setQuestions(q.questions);
      setStatus(s);
      setLoading(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load intake.");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const current = status?.next_question
    ? questions.find((q) => q.number === status.next_question)
    : null;

  async function submit(text: string) {
    if (!status?.next_question || !text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const next = await submitIntakeAnswer(status.next_question, text.trim());
      setStatus(next);
      setAnswer("");
      if (next.next_question === null && !next.completed) {
        const done = await completeIntake();
        setArchetypeName(done.archetype_name);
        setStatus({ ...next, completed: true, archetype_id: done.archetype_id });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save that answer.");
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    setGenerating(true);
    setGenerateError(null);
    try {
      await generateRoadmap();
      router.replace("/app/phase");
    } catch (err) {
      // 502 = LLM output discarded by the fail-closed validator — a normal,
      // retryable outcome; nothing was stored.
      setGenerateError(
        err instanceof ApiError && err.status === 502
          ? "The roadmap generator produced output that didn't pass validation, so it was discarded. Nothing was saved — try again."
          : err instanceof ApiError
            ? err.message
            : "Roadmap generation failed. Try again."
      );
      setGenerating(false);
    }
  }

  const answeredCount = status?.answered_questions.length ?? 0;

  return (
    <>
      <h1 className="page-title">Project Intake</h1>
      <p className="page-sub">
        Five questions, one at a time. Your answers shape the whole roadmap — especially the
        first one.
      </p>

      <Async loading={loading} error={error && !status ? error : null} onRetry={load}>
        <div className="row" style={{ marginBottom: 18 }}>
          {[1, 2, 3, 4, 5].map((n) => (
            <span
              key={n}
              className={`pill ${
                status?.answered_questions.includes(n)
                  ? "ok"
                  : status?.next_question === n
                    ? "accent"
                    : ""
              }`}
            >
              Q{n}
            </span>
          ))}
        </div>

        {/* transcript of answered questions */}
        {questions
          .filter((q) => status?.answered_questions.includes(q.number))
          .map((q) => (
            <div className="card" key={q.number}>
              <h3>Question {q.number}</h3>
              <p style={{ marginBottom: 8 }}>{q.text}</p>
              <p className="mono" style={{ color: "var(--ink-2)" }}>
                {status?.answers?.[q.key] ?? "(answered)"}
              </p>
            </div>
          ))}

        {current && (
          <div className="card" style={{ borderColor: "var(--accent)" }}>
            <h3>Question {current.number} of 5</h3>
            <p style={{ fontSize: 17, marginBottom: 14 }}>{current.text}</p>
            {error && <div className="notice error">{error}</div>}
            {current.options ? (
              <div className="row">
                {current.options.map((opt) => (
                  <button key={opt} className="btn" disabled={busy} onClick={() => submit(opt)}>
                    {opt}
                  </button>
                ))}
              </div>
            ) : (
              <>
                <textarea
                  rows={4}
                  maxLength={2000}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Answer in your own words — plain language beats jargon."
                />
                <div className="row" style={{ marginTop: 10 }}>
                  <button
                    className="btn primary"
                    disabled={busy || !answer.trim()}
                    onClick={() => submit(answer)}
                  >
                    {busy ? "Saving…" : "Answer"}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* all five answered but classification not run yet (e.g. reload mid-flow) */}
        {status && !status.completed && status.next_question === null && answeredCount === 5 && (
          <div className="card">
            <h3>All five answered</h3>
            {error && <div className="notice error">{error}</div>}
            <button
              className="btn primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError(null);
                try {
                  const done = await completeIntake();
                  setArchetypeName(done.archetype_name);
                  setStatus({ ...status, completed: true, archetype_id: done.archetype_id });
                } catch (err) {
                  setError(err instanceof ApiError ? err.message : "Couldn't finish intake.");
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "Classifying…" : "Finish intake"}
            </button>
          </div>
        )}

        {status?.completed && (
          <div className="card" style={{ borderColor: "var(--ok)" }}>
            <h3>Intake complete</h3>
            <p>
              {archetypeName
                ? `Your project classified as: ${archetypeName}.`
                : "Your project is classified."}{" "}
              Next, Codize generates your personalized roadmap — the fixed phase structure for
              your archetype, worded around your project.
            </p>
            {generateError && <div className="notice error">{generateError}</div>}
            <div className="row" style={{ marginTop: 12 }}>
              <button className="btn primary" disabled={generating} onClick={generate}>
                {generating ? "Generating roadmap… (can take ~30s)" : "Generate my roadmap"}
              </button>
            </div>
          </div>
        )}

        {answeredCount === 0 && !current && !status?.completed && !loading && (
          <p className="empty">Intake state unavailable — try reloading.</p>
        )}
      </Async>
    </>
  );
}
