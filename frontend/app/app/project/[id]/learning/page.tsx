"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { getLearning } from "@/lib/v2-api";
import type { LearnerStatus, LearningResponse } from "@/lib/v2-types";

const statusLabels: Record<LearnerStatus, string> = {
  new: "New", guided: "Guided", practiced: "Practiced",
  recently_independent: "Recently independent",
};

const dateLabel = (value: string) => new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
}).format(new Date(value));

export default function LearningPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<LearningResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try { setData(await getLearning(id)); }
    catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Couldn't load your learning view.");
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  if (!data && !error) {
    return <div className="v2-page"><V2Card><V2Skeleton lines={6} /></V2Card></div>;
  }

  return (
    <div className="v2-page v2-reflection-page">
      {error && (
        <V2Notice tone="error">
          {error} <button type="button" className="v2-inline-button" onClick={() => void load()}>Try again</button>
        </V2Notice>
      )}
      {data && (
        <>
          <header className="v2-page-header">
            <p className="v2-eyebrow">Learning</p>
            <h1>What you’re getting better at</h1>
            <p>See the habits Codize has actual evidence for—without turning your work into a report card.</p>
          </header>
          {data.competencies.length === 0 ? (
            <V2Card className="v2-reflection-empty">
              <span className="v2-empty-mark" aria-hidden="true" />
              <h2>Your learning map will grow as your project does.</h2>
              <p>Codize will start showing what you’re practicing as you build. Nothing appears here just because you opened the page.</p>
              <Link className="v2-button v2-button-primary" href={`/app/project/${id}/build`}>Start building</Link>
            </V2Card>
          ) : (
            <>
              <p className="v2-support-note">These are current support signals, not permanent badges. Codize can offer more help again whenever it is useful.</p>
              <div className="v2-learning-grid">
                {data.competencies.map((competency) => (
                  <article className="v2-learning-card" key={competency.key}>
                    <header>
                      <h2>{competency.name}</h2>
                      <span className={`v2-status v2-status-${competency.status}`}>{statusLabels[competency.status]}</span>
                    </header>
                    <p>{competency.description}</p>
                    <p className="v2-learning-summary">{competency.status_explanation}</p>
                    <p className="v2-support-direction">Codize is currently giving <strong>{competency.support_direction}</strong> help here.</p>
                    <details className="v2-evidence-details">
                      <summary>Why this status</summary>
                      <ol>
                        {competency.recent_evidence.map((evidence, index) => (
                          <li key={`${competency.key}:${evidence.observed_at}:${index}`}>
                            <strong>{evidence.observed_behavior}</strong>
                            <span>{evidence.support_explanation}</span>
                            <small>{[evidence.project_name, evidence.current_change_goal, dateLabel(evidence.observed_at)].filter(Boolean).join(" · ")}</small>
                          </li>
                        ))}
                      </ol>
                    </details>
                  </article>
                ))}
              </div>
              <Link className="v2-reflection-back" href={`/app/project/${id}/build`}>Continue building <span aria-hidden="true">›</span></Link>
            </>
          )}
        </>
      )}
    </div>
  );
}
