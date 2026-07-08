"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import {
  ApiError,
  getCurrentGate,
  getCurrentPhase,
  getEvaluation,
  getIntakeStatus,
  getWorkflow,
} from "@/lib/api";
import {
  ARCHETYPE_NAMES,
  buildReportMarkdown,
  defenseLabel,
  defenseStatus,
  deriveInterviewQuestions,
  deriveSkills,
  deriveWeakSpots,
  VERIFICATION_LABELS,
  type ReportInput,
} from "@/lib/report";
import type { GateCurrent, PhaseView, WorkflowSections } from "@/lib/types";

export default function ReportPage() {
  const [input, setInput] = useState<ReportInput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preActive, setPreActive] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPreActive(false);
    setCopied(false);
    try {
      const evaluation = await getEvaluation();
      if (
        evaluation.state === "not_started" ||
        evaluation.state === "intake_needed" ||
        evaluation.state === "roadmap_needed"
      ) {
        setPreActive(true);
        setLoading(false);
        return;
      }
      const phaseNum = evaluation.current_phase ?? 1;
      const [intake, workflow, phase, gate] = await Promise.allSettled([
        getIntakeStatus(),
        getWorkflow(phaseNum),
        getCurrentPhase(),
        getCurrentGate(),
      ]);
      setInput({
        evaluation,
        answers: intake.status === "fulfilled" ? intake.value.answers : null,
        archetypeId: intake.status === "fulfilled" ? intake.value.archetype_id : null,
        sections: workflow.status === "fulfilled" ? workflow.value.sections : null,
        phase: phase.status === "fulfilled" ? phase.value : null,
        gate: gate.status === "fulfilled" ? gate.value : null,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your report.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function copyMarkdown() {
    if (!input) return;
    try {
      await navigator.clipboard.writeText(buildReportMarkdown(input));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  function downloadMarkdown() {
    if (!input) return;
    const blob = new Blob([buildReportMarkdown(input)], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "codize-project-defense-report.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (preActive) {
    return (
      <>
        <h1 className="page-title">Project Defense Report</h1>
        <div className="notice info">
          Your defense report assembles from your project as you build it. Start by finishing
          intake and generating your roadmap.
        </div>
        <Link href="/app/intake" className="btn primary">
          Go to intake
        </Link>
      </>
    );
  }

  return (
    <>
      <div className="spread">
        <div>
          <h1 className="page-title">Project Defense Report</h1>
          <p className="page-sub">
            Everything you&rsquo;d need to stand behind this project, assembled from your real
            workflow — a record of what you did and can explain (self-reported), not a guarantee
            it works.
          </p>
        </div>
        {input && (
          <div className="row">
            <button className="btn" onClick={copyMarkdown}>
              {copied ? "Copied ✓" : "Copy as Markdown"}
            </button>
            <button className="btn" onClick={downloadMarkdown}>
              Download .md
            </button>
          </div>
        )}
      </div>

      <Async loading={loading} error={error} onRetry={load}>
        {input && <ReportBody input={input} />}
      </Async>
    </>
  );
}

// --- rendered report ---------------------------------------------------------

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function Missing({ children }: { children: React.ReactNode }) {
  return <p className="empty">{children}</p>;
}

function ReportBody({ input }: { input: ReportInput }) {
  const { evaluation, answers, sections, phase } = input;
  const archetype = input.archetypeId ? ARCHETYPE_NAMES[input.archetypeId] : null;
  const status = defenseStatus(input);
  const skills = deriveSkills(input);
  const weak = deriveWeakSpots(input);
  const questions = deriveInterviewQuestions(input);

  return (
    <>
      <Card title="1. Project overview">
        <KV k="Problem solved" v={answers?.purpose} />
        <KV k="Scope" v={answers?.scope} />
        <KV k="Stack" v={answers?.stack} />
        <KV k="Archetype" v={archetype} />
        <KV
          k="Current phase"
          v={
            evaluation.current_phase != null
              ? `Phase ${evaluation.current_phase} of ${evaluation.total_phases} — ${
                  phase?.phase_title ?? evaluation.phase_title ?? ""
                }`
              : null
          }
        />
        <KV k="Core concept" v={phase?.core_concept} />
      </Card>

      <AiWorkflowCard sections={sections} />
      <VerificationCard sections={sections} />

      <Card title="4. Project defense status">
        <div className="row" style={{ marginBottom: 8 }}>
          <span
            className={`pill ${
              status === "passed" ? "ok" : status === "cooldown" ? "danger" : status === "in_progress" ? "warn" : ""
            }`}
          >
            {defenseLabel(status)}
          </span>
        </div>
        {status === "cooldown" && input.gate?.cooldown_seconds_remaining != null && (
          <p className="muted">
            Retry available in ~{Math.max(1, Math.ceil(input.gate.cooldown_seconds_remaining / 60))} min.
          </p>
        )}
        {evaluation.recent_gate?.summary && (
          <KV k="Latest gate note" v={evaluation.recent_gate.summary} />
        )}
        <p className="muted" style={{ marginTop: 8 }}>
          The gate&rsquo;s numeric score and private evaluator reasoning are intentionally not shown
          — here or anywhere.
        </p>
        {status === "not_attempted" && (
          <Link href="/app/gate" className="btn" style={{ marginTop: 10 }}>
            Attempt the defense
          </Link>
        )}
      </Card>

      <Card title="5. Skills demonstrated">
        {skills.map((row) => (
          <div className="task" key={row.skill}>
            <span>{row.demonstrated ? "✅" : "⬜"}</span>
            <span style={{ flex: 1 }}>
              <strong>{row.skill}</strong>
              <span className="muted"> — {row.note}</span>
            </span>
          </div>
        ))}
      </Card>

      <Card title="6. Weak spots / next actions">
        {weak.length ? (
          weak.map((w, i) => (
            <p key={i} style={{ marginBottom: 6, overflowWrap: "anywhere" }}>
              • {w} {linkFor(w)}
            </p>
          ))
        ) : (
          <p>No obvious gaps for this phase — nice.</p>
        )}
        <div className="notice info" style={{ marginTop: 10 }}>
          <strong>Recommended next:</strong> {evaluation.next_action}
        </div>
      </Card>

      <Card title="7. Interview / defense questions">
        <p className="muted" style={{ marginBottom: 8 }}>
          Derived from your project — rehearse these before a demo or interview.
        </p>
        <ol className="trap-steps" style={{ marginTop: 0 }}>
          {questions.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ol>
      </Card>
    </>
  );
}

function AiWorkflowCard({ sections }: { sections: WorkflowSections | null }) {
  const pb = sections?.prompt_builder ?? null;
  const rb = sections?.review_board ?? null;
  return (
    <Card title="2. AI workflow evidence">
      {pb ? (
        <>
          <p className="muted" style={{ marginBottom: 6 }}>Engineered prompt</p>
          <pre className="output">{pb.generated_prompt}</pre>
          {pb.why_stronger && <KV k="Why it's stronger" v={pb.why_stronger} />}
        </>
      ) : (
        <Missing>
          No engineered prompt saved. <Link href="/app/phase/prompt">Open Prompt Builder →</Link>
        </Missing>
      )}
      <hr className="rule" />
      {rb ? (
        <>
          <KV k="Files changed" v={(rb.files_changed ?? []).join(", ") || null} />
          <KV k="AI generated" v={rb.ai_generated} />
          <KV k="Accepted" v={rb.accepted} />
          <KV k="Rejected" v={rb.rejected} />
          <KV k="Edited manually" v={rb.edited_manually} />
          <KV k="AI assumptions" v={rb.ai_assumptions} />
          <KV k="Least confident" v={rb.least_confident} />
          <KV k="Out-of-scope changes" v={rb.out_of_scope_changes} />
        </>
      ) : (
        <Missing>
          AI output not reviewed. <Link href="/app/phase/review">Open Review Board →</Link>
        </Missing>
      )}
    </Card>
  );
}

function VerificationCard({ sections }: { sections: WorkflowSections | null }) {
  const ver = sections?.verification ?? null;
  const ev = sections?.evidence ?? null;
  return (
    <Card title="3. Verification evidence (self-reported)">
      {ver?.checks?.length ? (
        <>
          {ver.checks.map((c) => (
            <div className="task" key={c.check}>
              <span
                className={`pill ${
                  c.result === "pass" ? "ok" : c.result === "fail" ? "danger" : ""
                }`}
              >
                {c.result}
              </span>
              <span style={{ flex: 1 }}>
                {VERIFICATION_LABELS[c.check] ?? c.check}
                {c.note && <span className="muted"> — {c.note}</span>}
              </span>
            </div>
          ))}
          {ver.explanation && <KV k="What it proves" v={ver.explanation} />}
        </>
      ) : (
        <Missing>
          No verification checks recorded. <Link href="/app/phase/verify">Open Verification Lab →</Link>
        </Missing>
      )}
      <hr className="rule" />
      {ev?.entries?.length ? (
        <>
          <p className="muted" style={{ marginBottom: 6 }}>Submitted evidence</p>
          {ev.entries.map((entry, i) => (
            <div className="task" key={i}>
              <span className="tag">{entry.kind}</span>
              <span className="mono" style={{ flex: 1, overflowWrap: "anywhere" }}>
                {entry.content.length > 300 ? `${entry.content.slice(0, 300)}…` : entry.content}
              </span>
            </div>
          ))}
          {ev.summary && <KV k="What it shows" v={ev.summary} />}
        </>
      ) : (
        <Missing>
          No evidence attached. <Link href="/app/phase/evidence">Open Evidence Panel →</Link>
        </Missing>
      )}
    </Card>
  );
}

function KV({ k, v }: { k: string; v: string | null | undefined }) {
  return (
    <div className="kv" style={{ marginTop: 4 }}>
      <span className="k">{k}</span>
      <span style={{ overflowWrap: "anywhere" }}>
        {v && v.trim() ? v : <span className="muted">Not provided</span>}
      </span>
    </div>
  );
}

// Small deep-link so missing-section callouts point back at the right page.
function linkFor(gap: string): React.ReactNode {
  const map: [string, string, string][] = [
    ["Prompt Builder", "/app/phase/prompt", "Prompt Builder →"],
    ["Review Board", "/app/phase/review", "Review Board →"],
    ["Evidence Panel", "/app/phase/evidence", "Evidence Panel →"],
    ["Verification Lab", "/app/phase/verify", "Verification Lab →"],
    ["Interrogation Gate", "/app/gate", "Project Defense →"],
  ];
  const hit = map.find(([needle]) => gap.includes(needle));
  return hit ? (
    <Link href={hit[1]} className="mono" style={{ fontSize: 12 }}>
      {hit[2]}
    </Link>
  ) : null;
}
