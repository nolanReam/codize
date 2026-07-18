"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import Async from "@/components/Async";
import AdaptiveEntry from "@/components/AdaptiveEntry";
import GuideCard from "@/components/GuideCard";
import {
  ApiError,
  completeIntake,
  generateRoadmap,
  getEntryProfile,
  getIntakeQuestions,
  getIntakeStatus,
  submitIntakeAnswer,
  updateEntryProfile,
} from "@/lib/api";
import { useDraft } from "@/lib/drafts";
import { normalizeEntryProfile, recommendationFor } from "@/lib/entryProfile";
import type { EntryProfile, EntryProfileUpdate, IntakeQuestion, IntakeStatus } from "@/lib/types";

// Per-question beginner guidance (M13E.1): helper text, an example
// placeholder, and optional tap-to-fill starter chips. The question TEXT is
// spec-fixed and comes from the backend — this only explains how to answer.
const QUESTION_HELP: Record<
  number,
  { helper: React.ReactNode; placeholder: string; chips?: string[] }
> = {
  1: {
    helper: (
      <>
        Think of a real annoyance in your life or someone else&rsquo;s — small is fine. If
        you&rsquo;re not sure who it helps, name the one person you&rsquo;d show it to first.
      </>
    ),
    placeholder:
      "e.g. My club loses track of who paid dues — this helps our treasurer (me) stop chasing people.",
  },
  2: {
    helper: (
      <>
        Plain language, like texting a friend. No technical words needed — what does someone
        actually do with it?
      </>
    ),
    placeholder:
      "e.g. You add what you paid, it splits the cost and shows who owes who.",
  },
  3: {
    helper: (
      <>
        <p style={{ margin: "0 0 6px" }}>
          &ldquo;Languages or frameworks&rdquo; just means <strong>whatever you already know</strong>,
          at any level:
        </p>
        <ul style={{ margin: "0 0 6px", paddingLeft: 18 }}>
          <li>a coding language — Java, Python, JavaScript</li>
          <li>a framework or library — FastAPI, Flask, React, Next.js</li>
          <li>a database or tool — Supabase, SQLite</li>
          <li>or none of these yet</li>
        </ul>
        <p style={{ margin: 0 }}>
          <strong>&ldquo;Not sure yet&rdquo; is a valid answer.</strong> Use the tools you know —
          Codize plans around them.
        </p>
      </>
    ),
    placeholder: "e.g. AP CSA Java, no framework yet",
    chips: [
      "AP CSA Java, no framework yet",
      "Python, maybe Flask or FastAPI",
      "Next.js + Supabase",
      "I only know basic Python and Java right now",
    ],
  },
  4: {
    helper: <>Honest answers make your roadmap fit better. Nobody grades this.</>,
    placeholder: "",
  },
  5: {
    helper: (
      <>
        This means a <strong>first working version you can demo</strong> — not the final polished
        product. Rough is fine; &ldquo;no deadline&rdquo; is fine too.
      </>
    ),
    placeholder: "e.g. before my hackathon demo in two weeks",
    chips: [
      "tonight",
      "this weekend",
      "in 2 weeks",
      "before my hackathon demo",
      "no deadline, just learning",
    ],
  },
};

// Conversational intake — the spec's five mandatory, sequential questions.
// Question 1 is verbatim and unskippable; the backend enforces first-answer
// order. Until you finish, any answered question can be edited (M13E.1) —
// which is also why completion is an explicit review step, never automatic.
export default function IntakePage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<IntakeQuestion[]>([]);
  const [status, setStatus] = useState<IntakeStatus | null>(null);
  const [answer, setAnswer] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [archetypeName, setArchetypeName] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [entryProfile, setEntryProfile] = useState<EntryProfile | null>(null);
  const [entryMode, setEntryMode] = useState(false);
  const [preferencesOnly, setPreferencesOnly] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [q, s, entry] = await Promise.all([
        getIntakeQuestions(),
        getIntakeStatus(),
        getEntryProfile(),
      ]);
      const safeProfile = normalizeEntryProfile(entry.profile);
      setQuestions(q.questions);
      setStatus(s);
      setEntryProfile(safeProfile);
      const preferenceRequest = new URLSearchParams(window.location.search).get("preferences") === "1";
      setPreferencesOnly(preferenceRequest);
      setEntryMode(
        !preferenceRequest &&
        s.answered_questions.length === 0 &&
        !s.completed &&
        !safeProfile?.completed
      );
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

  // Unsaved-draft persistence (M13E.2): a half-typed answer survives switching
  // tabs. Scoped per question; cleared when that question's answer submits.
  const answerDraft = useDraft<string>(current ? `intake:q${current.number}` : null);
  const answerDraftApplied = useRef<string | null>(null);
  useEffect(() => {
    const surface = current ? `intake:q${current.number}` : null;
    if (!surface || !answerDraft.ready || answerDraftApplied.current === surface) return;
    answerDraftApplied.current = surface;
    if (answerDraft.restored) setAnswer((prev) => (prev === "" ? answerDraft.restored ?? "" : prev));
  }, [current, answerDraft.ready, answerDraft.restored]);
  const saveAnswerDraft = answerDraft.save;
  useEffect(() => {
    saveAnswerDraft(answer);
  }, [answer, saveAnswerDraft]);

  const editDraft = useDraft<string>(editing != null ? `intake:edit:q${editing}` : null);
  const editDraftApplied = useRef<number | null>(null);
  useEffect(() => {
    if (editing == null || !editDraft.ready || editDraftApplied.current === editing) return;
    editDraftApplied.current = editing;
    if (editDraft.restored) setEditText(editDraft.restored);
  }, [editing, editDraft.ready, editDraft.restored]);
  const saveEditDraft = editDraft.save;
  useEffect(() => {
    if (editing != null) saveEditDraft(editText);
  }, [editing, editText, saveEditDraft]);

  async function submit(questionNumber: number, text: string) {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const next = await submitIntakeAnswer(questionNumber, text.trim());
      answerDraft.clear();
      editDraft.clear();
      editDraftApplied.current = null;
      setStatus(next);
      setAnswer("");
      setEditing(null);
      setEditText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save that answer.");
    } finally {
      setBusy(false);
    }
  }

  async function finishIntake() {
    setBusy(true);
    setError(null);
    try {
      const done = await completeIntake();
      setArchetypeName(done.archetype_name);
      setStatus((prev) =>
        prev ? { ...prev, completed: true, archetype_id: done.archetype_id } : prev
      );
      setEditing(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't finish intake.");
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    setGenerating(true);
    setGenerateError(null);
    try {
      await generateRoadmap();
      const recommendation = recommendationFor(entryProfile);
      router.replace(recommendation?.href ?? "/app/phase/prompt");
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
  const readyToFinish =
    status != null && !status.completed && status.next_question === null && answeredCount === 5;

  async function saveEntry(updates: EntryProfileUpdate): Promise<EntryProfile> {
    const result = await updateEntryProfile(updates);
    const saved = normalizeEntryProfile(result.profile);
    if (!saved) throw new Error("Your saved guidance choices could not be read safely.");
    setEntryProfile(saved);
    return saved;
  }

  if (!loading && status && (entryMode || preferencesOnly)) {
    return (
      <>
        <h1 className="page-title">
          {preferencesOnly ? "Guidance Preferences" : "Find Your Starting Point"}
        </h1>
        <p className="page-sub">
          {preferencesOnly
            ? "Choose how much explanation Codize shows. Your saved project work will not change."
            : "A few short choices help Codize recommend one sensible place to begin."}
        </p>
        <div className="entry-layout">
          <AdaptiveEntry
            profile={entryProfile}
            preferencesOnly={preferencesOnly}
            onSave={saveEntry}
            onContinue={() => setEntryMode(false)}
          />
        </div>
      </>
    );
  }

  return (
    <>
      <h1 className="page-title">Project Intake</h1>
      <p className="page-sub">
        Five questions, one at a time — this is how you start your project. Plain language beats
        jargon, and you can edit any answer until you finish.
      </p>

      <Async loading={loading} error={error && !status ? error : null} onRetry={load}>
        <div className="workspace">
          <div>
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

            {/* transcript of answered questions — editable until completion */}
            {questions
              .filter((q) => status?.answered_questions.includes(q.number))
              .map((q) => {
                const help = QUESTION_HELP[q.number];
                const stored = status?.answers?.[q.key] ?? "";
                const isEditing = editing === q.number;
                return (
                  <div className="card" key={q.number}>
                    <div className="spread">
                      <h3>Question {q.number}</h3>
                      {!status?.completed && !isEditing && (
                        <button
                          className="btn small"
                          disabled={busy}
                          onClick={() => {
                            setEditing(q.number);
                            setEditText(stored);
                            setError(null);
                          }}
                        >
                          Edit
                        </button>
                      )}
                    </div>
                    <p style={{ marginBottom: 8 }}>{q.text}</p>
                    {isEditing ? (
                      <>
                        {error && <div className="notice error">{error}</div>}
                        {q.options ? (
                          <div className="row">
                            {q.options.map((opt) => (
                              <button
                                key={opt}
                                className={`btn${opt === stored ? " primary" : ""}`}
                                disabled={busy}
                                onClick={() => submit(q.number, opt)}
                              >
                                {opt}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <>
                            {help?.chips && (
                              <div className="chips">
                                {help.chips.map((c) => (
                                  <button
                                    key={c}
                                    type="button"
                                    className="chip"
                                    onClick={() => setEditText(c)}
                                  >
                                    {c}
                                  </button>
                                ))}
                              </div>
                            )}
                            <textarea
                              rows={3}
                              maxLength={2000}
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                            />
                            <div className="row" style={{ marginTop: 10 }}>
                              <button
                                className="btn primary"
                                disabled={busy || !editText.trim()}
                                onClick={() => submit(q.number, editText)}
                              >
                                {busy ? "Saving…" : "Save change"}
                              </button>
                              <button
                                className="btn"
                                disabled={busy}
                                onClick={() => {
                                  editDraft.clear(); // cancel = explicit discard
                                  editDraftApplied.current = null;
                                  setEditing(null);
                                  setEditText("");
                                  setError(null);
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          </>
                        )}
                      </>
                    ) : (
                      <p className="mono" style={{ color: "var(--ink-2)" }}>
                        {stored || "(answered)"}
                      </p>
                    )}
                  </div>
                );
              })}

            {current && (
              <div className="card primary">
                <h3>Question {current.number} of 5</h3>
                <p style={{ fontSize: 17, marginBottom: 10 }}>{current.text}</p>
                {QUESTION_HELP[current.number] && (
                  <div className="muted" style={{ marginBottom: 12, fontSize: 13.5 }}>
                    {QUESTION_HELP[current.number].helper}
                  </div>
                )}
                {error && !editing && <div className="notice error">{error}</div>}
                {current.options ? (
                  <div className="row">
                    {current.options.map((opt) => (
                      <button
                        key={opt}
                        className="btn"
                        disabled={busy}
                        onClick={() => submit(current.number, opt)}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                ) : (
                  <>
                    {QUESTION_HELP[current.number]?.chips && (
                      <div className="chips">
                        {QUESTION_HELP[current.number].chips!.map((c) => (
                          <button
                            key={c}
                            type="button"
                            className="chip"
                            onClick={() => setAnswer(c)}
                          >
                            {c}
                          </button>
                        ))}
                      </div>
                    )}
                    <textarea
                      rows={4}
                      maxLength={2000}
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      placeholder={
                        QUESTION_HELP[current.number]?.placeholder ||
                        "Answer in your own words — plain language beats jargon."
                      }
                    />
                    <div className="row" style={{ marginTop: 10 }}>
                      <button
                        className="btn primary"
                        disabled={busy || !answer.trim()}
                        onClick={() => submit(current.number, answer)}
                      >
                        {busy ? "Saving…" : "Answer"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* all five answered: explicit review step before classification */}
            {readyToFinish && (
              <div className="card primary">
                <h3>All five answered — review before you finish</h3>
                <p>
                  Read your answers above once more. Anything off? Use <strong>Edit</strong> —
                  after you finish, answers are locked in and Codize classifies your project.
                </p>
                {error && editing === null && <div className="notice error">{error}</div>}
                <div className="row" style={{ marginTop: 12 }}>
                  <button className="btn primary" disabled={busy} onClick={finishIntake}>
                    {busy ? "Classifying…" : "Finish intake"}
                  </button>
                </div>
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
          </div>

          <aside className="ws-rail" aria-label="Guidance">
            <GuideCard title="How intake works">
              <p>
                Your project answers tell Codize what you&rsquo;re building and choose the roadmap
                shape. Your experience answer only adjusts how concepts are explained; it never
                turns your project into an AI-powered app.
              </p>
              <p>
                <strong>You can edit any answer</strong> until you press Finish — nothing is
                locked while you&rsquo;re answering.
              </p>
            </GuideCard>
            <GuideCard title="If you're stuck">
              <ul>
                <li>Short, honest answers beat impressive ones.</li>
                <li>&ldquo;Not sure yet&rdquo; is a valid answer.</li>
                <li>The examples under each question are tap-to-use — edit them after.</li>
              </ul>
            </GuideCard>
            <GuideCard title="What happens after">
              <details className="help">
                <summary>What&rsquo;s a &ldquo;project type&rdquo;?</summary>
                <div className="help-body">
                  <p>
                    Codize uses the closest of three stored roadmap structures, then keeps the
                    student-facing label accurate to the capabilities you described. A local
                    browser project can be labeled simply &ldquo;Browser App.&rdquo;
                  </p>
                </div>
              </details>
              <details className="help">
                <summary>What&rsquo;s a roadmap?</summary>
                <div className="help-body">
                  <p>
                    Your project broken into phases (like &ldquo;database&rdquo; or
                    &ldquo;login&rdquo;), each with tasks that are fine to hand to AI and tasks
                    that are yours. You work one phase at a time.
                  </p>
                </div>
              </details>
            </GuideCard>
          </aside>
        </div>
      </Async>
    </>
  );
}
