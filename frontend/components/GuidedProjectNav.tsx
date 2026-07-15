"use client";

import Link from "next/link";

import { useGuidedProjectNavigation } from "./GuidedProjectNavigationProvider";
import { routeIsActive } from "@/lib/guidedProjectNavigation";

export function GuidedContinueAction({
  className = "guided-continue-link",
}: {
  className?: string;
}) {
  const { navigation, state } = useGuidedProjectNavigation();
  const next = navigation.continueAction;
  if (state === "loading") {
    return (
      <div className="guided-continue-loading" role="status" aria-live="polite">
        Loading project progress…
      </div>
    );
  }
  if (state === "error") return null;
  if (next.href) {
    return (
      <Link href={next.href} className={className}>
        {next.label}
      </Link>
    );
  }
  return (
    <div className="guided-continue-unavailable" role="status">
      <strong>{next.label}</strong>
      <span>{next.reason}</span>
    </div>
  );
}

export default function GuidedProjectNav({
  pathname,
  email,
  idPrefix,
  onNavigate,
  onHelp,
  onSignOut,
}: {
  pathname: string;
  email: string | null;
  idPrefix: string;
  onNavigate?: () => void;
  onHelp: () => void;
  onSignOut: () => void;
}) {
  const { navigation, state, error, refresh } = useGuidedProjectNavigation();
  const continueIsCurrent =
    state === "ready" &&
    navigation.continueAction.href != null &&
    routeIsActive(pathname, navigation.continueAction.href);
  const recordContainsCurrent =
    !continueIsCurrent &&
    navigation.projectRecord.some((item) => routeIsActive(pathname, item.href));

  return (
    <>
      <div className="project-identity" aria-label="Active project">
        <span className="project-identity-label">Active project</span>
        <strong title={navigation.projectLabel}>{navigation.projectLabel}</strong>
        {navigation.phaseLabel && <span>{navigation.phaseLabel}</span>}
      </div>

      <nav aria-label="Project navigation" className="guided-project-nav">
        <Link
          href={navigation.projectHome.href}
          className={`project-home-link${pathname === "/app" ? " active" : ""}`}
          aria-current={pathname === "/app" ? "page" : undefined}
          onClick={onNavigate}
        >
          <span>{navigation.projectHome.label}</span>
          <span aria-hidden="true">⌂</span>
        </Link>

        <section className="guided-nav-section guided-continue" aria-labelledby={`${idPrefix}-continue`}>
          <h2 id={`${idPrefix}-continue`}>Continue</h2>
          {state === "ready" && navigation.continueAction.href ? (
            <Link
              href={navigation.continueAction.href}
              className="guided-continue-link"
              aria-current={continueIsCurrent ? "page" : undefined}
              onClick={onNavigate}
            >
              <span>{navigation.continueAction.label}</span>
              <span aria-hidden="true">→</span>
            </Link>
          ) : state === "ready" ? (
            <div className="guided-continue-unavailable" role="status">
              <strong>{navigation.continueAction.label}</strong>
              <span>{navigation.continueAction.reason}</span>
            </div>
          ) : state === "loading" ? (
            <div className="guided-continue-loading" role="status" aria-live="polite">
              Loading project progress…
            </div>
          ) : (
            <div className="guided-navigation-error" role="alert">
              <span>Project progress is temporarily unavailable.</span>
              <button type="button" onClick={() => void refresh()}>
                Retry
              </button>
            </div>
          )}
          {state === "ready" && navigation.continueAction.href && (
            <p>{navigation.continueAction.reason}</p>
          )}
        </section>

        <section className="guided-nav-section" aria-labelledby={`${idPrefix}-journey`}>
          <h2 id={`${idPrefix}-journey`}>Journey</h2>
          {state === "error" ? (
            <p className="guided-nav-muted">Saved journey state is unavailable. Your current page remains open.</p>
          ) : (
            <ol className="guided-journey" aria-busy={state === "loading"}>
              {state === "loading"
                ? Array.from({ length: 8 }, (_, index) => (
                    <li className="guided-stage loading-stage" key={index}>
                      <span className="guided-stage-index">{String(index + 1).padStart(2, "0")}</span>
                      <span>Loading stage</span>
                    </li>
                  ))
                : navigation.journey.map((item, index) => (
                    <li className={`guided-stage ${item.state}`} key={item.id}>
                      <span className="guided-stage-index" aria-hidden="true">
                        {item.state === "complete" ? "✓" : String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="guided-stage-copy">
                        <span>{item.label}</span>
                        <span className="guided-stage-state">{item.stateLabel}</span>
                      </span>
                      <span className="sr-only">{item.reason}</span>
                    </li>
                  ))}
            </ol>
          )}
        </section>

        <details className="project-record" open={recordContainsCurrent || undefined}>
          <summary>
            <span>Project Record</span>
            {state === "ready" && <span>{navigation.projectRecord.length}</span>}
          </summary>
          <p>Saved workflow history. These records are not independent verification.</p>
          {state === "ready" && navigation.projectRecord.length > 0 ? (
            <ul>
              {navigation.projectRecord.map((item) => {
                const current =
                  !continueIsCurrent && routeIsActive(pathname, item.href);
                return (
                  <li key={item.id} className={item.state}>
                    <Link
                      href={item.href}
                      aria-current={current ? "page" : undefined}
                      onClick={onNavigate}
                    >
                      <span>{item.label}</span>
                      <span>{item.stateLabel}</span>
                    </Link>
                    {item.description && <p>{item.description}</p>}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="guided-nav-muted">
              {state === "loading" ? "Loading saved records…" : "Saved workflow records will appear here."}
            </p>
          )}
        </details>

        <section className="guided-nav-section guided-utilities" aria-labelledby={`${idPrefix}-project-tools`}>
          <h2 id={`${idPrefix}-project-tools`}>Project tools</h2>
          <Link
            href="/app/phase"
            className={pathname === "/app/phase" ? "active" : ""}
            aria-current={pathname === "/app/phase" ? "page" : undefined}
            onClick={onNavigate}
          >
            Phase Workspace
          </Link>
          <button type="button" onClick={onHelp}>
            How Codize works
          </button>
        </section>
      </nav>

      <div className="sidebar-footer">
        <div>{email}</div>
        <button className="btn small" onClick={onSignOut}>
          Sign out
        </button>
      </div>
      {error && <span className="sr-only">{error}</span>}
    </>
  );
}
