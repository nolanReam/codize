"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import V2Character from "@/components/v2/V2Character";
import { V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { getCurrentChange, getV2Plan, getV2Project } from "@/lib/v2-api";
import type { CurrentChangeView, PlanItemView, V2ProjectView } from "@/lib/v2-types";

interface ProjectHomeState {
  project: V2ProjectView;
  currentChange: CurrentChangeView | null;
  planItems: PlanItemView[];
}

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<ProjectHomeState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [project, plan, current] = await Promise.all([
        getV2Project(id),
        getV2Plan(id),
        getCurrentChange(id),
      ]);
      setState({ project, planItems: plan.items, currentChange: current.current_change });
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Couldn't load this project.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const upNext = useMemo(() => {
    if (!state) return null;
    if (state.currentChange) {
      return {
        title: state.currentChange.goal_snapshot,
        detail: state.currentChange.done_condition_snapshot,
        active: true,
      };
    }
    const item = state.planItems.find((candidate) =>
      candidate.status === "ready" || candidate.status === "proposed"
    );
    return item ? { title: item.label, detail: item.intended_outcome, active: false } : null;
  }, [state]);

  const recent = state?.planItems
    .filter((item) => item.status === "done")
    .sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? ""))
    .slice(0, 3);

  if (!state && !error) {
    return <div className="v2-page"><V2Card><V2Skeleton lines={6} /></V2Card></div>;
  }

  return (
    <div className="v2-page v2-project-page">
      {error && (
        <V2Notice tone="error">
          {error} <button type="button" className="v2-inline-button" onClick={() => void load()}>Try again</button>
        </V2Notice>
      )}
      {state && (
        <>
          <header className="v2-page-header v2-project-heading">
            <V2Character size="small" />
            <div>
              <p className="v2-eyebrow">Project</p>
              <h1>{state.project.display_name}</h1>
              <p>{state.currentChange ? "Ready to keep going?" : "Ready for the next piece?"}</p>
            </div>
          </header>

          <V2Card className="v2-up-next-card">
            <p className="v2-card-label">Up next</p>
            {upNext ? (
              <>
                <h2>{upNext.title}</h2>
                {upNext.detail && <p>{upNext.detail}</p>}
                {upNext.active ? (
                  <Link className="v2-button v2-button-primary" href={`/app/project/${id}/build`}>
                    Continue current change
                  </Link>
                ) : (
                  <p className="v2-muted">
                    This plan item is ready. Starting a new current change arrives in the setup slice.
                  </p>
                )}
              </>
            ) : (
              <>
                <h2>No current change yet</h2>
                <p>Nothing is active. Your next plan item will appear here when setup is complete.</p>
              </>
            )}
          </V2Card>

          <div className="v2-project-links">
            <Link href={`/app/project/${id}/plan`}>Build plan <span aria-hidden="true">›</span></Link>
            <Link href={`/app/project/${id}/history`}>Recent changes <span aria-hidden="true">›</span></Link>
          </div>

          <section className="v2-recent" aria-labelledby="recent-heading">
            <h2 id="recent-heading">Recent progress</h2>
            {recent && recent.length > 0 ? (
              <ul>
                {recent.map((item) => (
                  <li key={item.id}>
                    <span aria-hidden="true">✓</span>
                    <span><strong>{item.label}</strong><small>Completed plan item</small></span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="v2-muted">Completed changes will appear here after your first build loop.</p>
            )}
          </section>

          <V2Card className="v2-recovery-link">
            <div>
              <h2>Something not working?</h2>
              <p>Recovery is coming in a later slice. Your current work stays safe.</p>
            </div>
            <button type="button" className="v2-button v2-button-ghost" disabled>Something broke</button>
          </V2Card>
        </>
      )}
    </div>
  );
}
