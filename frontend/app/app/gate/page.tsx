"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Async from "@/components/Async";
import NotReady from "@/components/NotReady";
import { ApiError, getCurrentGate } from "@/lib/api";
import type { GateCurrent } from "@/lib/types";

const STATE_PILL: Record<GateCurrent["state"], { label: string; cls: string }> = {
  not_started: { label: "READY TO DEFEND", cls: "accent" },
  in_progress: { label: "IN PROGRESS", cls: "warn" },
  cooldown: { label: "COOLDOWN", cls: "danger" },
  passed: { label: "PASSED", cls: "ok" },
};

// Interrogation Gate — status view (M13C.1). The interactive defense flow
// (anchor statement → three probing turns → evaluation) is wired to the live
// M9 backend in M13C.2; starting a session here would strand the user
// mid-flow, so this page is deliberately read-only for now.
export default function GatePage() {
  const [gate, setGate] = useState<GateCurrent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notReady, setNotReady] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotReady(false);
    try {
      setGate(await getCurrentGate());
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

  if (notReady) return <NotReady title="Interrogation Gate" />;

  const pill = gate ? STATE_PILL[gate.state] : undefined;
  const cooldownMin =
    gate?.cooldown_seconds_remaining != null
      ? Math.max(1, Math.ceil(gate.cooldown_seconds_remaining / 60))
      : null;

  return (
    <>
      <div className="spread">
        <div>
          <h1 className="page-title">Interrogation Gate</h1>
          <p className="page-sub">
            Prove you understand what you built — in your own words, about your own
            implementation. Generic, textbook answers don&rsquo;t pass.
          </p>
        </div>
        {pill && <span className={`pill ${pill.cls}`}>{pill.label}</span>}
      </div>

      <Async loading={loading} error={error} onRetry={load}>
        {gate && (
          <>
            <div className="card">
              <h3>Current phase</h3>
              <div className="kv">
                <span className="k">Phase</span>
                <span>
                  {gate.phase} — {gate.phase_title}
                </span>
              </div>
              {gate.state === "cooldown" && cooldownMin != null && (
                <p className="notice info" style={{ marginTop: 12 }}>
                  A recent attempt didn&rsquo;t pass. You can try again in about{" "}
                  {cooldownMin} minute{cooldownMin === 1 ? "" : "s"}. Use the time to
                  re-read the phase concept and walk your own code — the gate asks about
                  what <em>you</em> built.
                </p>
              )}
              {gate.state === "passed" && (
                <p className="notice ok" style={{ marginTop: 12 }}>
                  You&rsquo;ve passed this phase&rsquo;s gate.
                </p>
              )}
              {gate.state === "in_progress" && (
                <p className="notice info" style={{ marginTop: 12 }}>
                  You have a gate session in progress. The interactive defense flow lands
                  in M13C.2 — for now, continue from your API client or the backend.
                </p>
              )}
              {gate.reason && (
                <div className="kv" style={{ marginTop: 8 }}>
                  <span className="k">Last verdict</span>
                  <span className="muted">{gate.reason}</span>
                </div>
              )}
            </div>

            <div className="card">
              <h3>How the gate works</h3>
              <ol className="trap-steps" style={{ marginTop: 0 }}>
                <li>
                  You give an <strong>anchor statement</strong> — a concrete piece of your
                  implementation you&rsquo;re ready to defend.
                </li>
                <li>Codize asks three probing questions specific to what you built.</li>
                <li>
                  A separate evaluation decides pass or fail on structural understanding,
                  ripple effects, and implementation specificity.
                </li>
                <li>Pass to advance a phase. Fail, and there&rsquo;s a short cooldown before retrying.</li>
              </ol>
              <p className="muted" style={{ marginTop: 12 }}>
                Ticking tasks never advances a phase — only passing this gate does.
              </p>
            </div>

            <div className="card" style={{ borderColor: "var(--border-strong)" }}>
              <h3>Interactive defense — M13C.2</h3>
              <p className="muted">
                The live, turn-by-turn interrogation flow (anchor → three turns →
                evaluation) is the headline of the next milestone. This page is the honest
                entry point: it reflects real gate state from the backend, but the
                interactive session isn&rsquo;t wired into the UI yet.
              </p>
              <div className="row" style={{ marginTop: 12 }}>
                <Link href="/app/phase" className="btn">
                  Back to phase workspace
                </Link>
              </div>
            </div>
          </>
        )}
      </Async>
    </>
  );
}
