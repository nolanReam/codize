"use client";

import Link from "next/link";

import { routeIsActive } from "@/lib/guidedProjectNavigation";
import { useGuidedProjectNavigation } from "./GuidedProjectNavigationProvider";

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
  const activeWorkflow = state === "ready" && navigation.workflow !== null;
  const continueIsCurrent =
    state === "ready" &&
    navigation.continueAction.href != null &&
    !navigation.continueAction.href.includes("#") &&
    routeIsActive(pathname, navigation.continueAction.href);
  const recordContainsCurrent =
    !continueIsCurrent &&
    navigation.projectRecord.some((item) => routeIsActive(pathname, item.href));
  const journeyCurrentId =
    pathname !== "/app" && !continueIsCurrent && !recordContainsCurrent
      ? navigation.journey.find((item) => routeIsActive(pathname, item.href))?.id ?? null
      : null;
  const mobileDisclosureGroup =
    idPrefix === "mobile" ? "mobile-project-navigation-sections" : undefined;

  return (
    <>
      {activeWorkflow && (
        <div className="project-identity" aria-label="Active project">
          <span className="project-identity-label">Active project</span>
          <strong title={navigation.projectLabel}>{navigation.projectLabel}</strong>
        </div>
      )}

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

        {activeWorkflow && (
          <details
            className="guided-journey-disclosure"
            open={journeyCurrentId != null || undefined}
            name={mobileDisclosureGroup}
          >
            <summary>
              <span>Journey</span>
              <span>{navigation.journey.length}</span>
            </summary>
            <ol className="guided-journey">
              {navigation.journey.map((item, index) => (
                <li
                  className={`guided-stage ${item.state}${journeyCurrentId === item.id ? " viewing" : ""}`}
                  aria-current={journeyCurrentId === item.id ? "page" : undefined}
                  key={item.id}
                >
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
          </details>
        )}

        {activeWorkflow && (
          <details
            className="project-record"
            open={recordContainsCurrent || undefined}
            name={mobileDisclosureGroup}
          >
            <summary>
              <span>Project Record</span>
              <span>{navigation.projectRecord.length}</span>
            </summary>
            <p>Saved workflow history. These records are not independent verification.</p>
            {navigation.projectRecord.length > 0 ? (
              <ul>
                {navigation.projectRecord.map((item) => {
                  const current = !continueIsCurrent && routeIsActive(pathname, item.href);
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
              <p className="guided-nav-muted">Saved workflow records will appear here.</p>
            )}
          </details>
        )}

        <section className="guided-nav-section guided-utilities" aria-labelledby={`${idPrefix}-help`}>
          <h2 id={`${idPrefix}-help`}>Help</h2>
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
