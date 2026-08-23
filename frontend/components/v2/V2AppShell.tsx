"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getV2Project } from "@/lib/v2-api";

const primaryItems = [
  { label: "Project", suffix: "" },
  { label: "Build", suffix: "/build" },
  { label: "Learning", suffix: "/learning" },
  { label: "History", suffix: "/history" },
] as const;

function projectIdFromPath(pathname: string): string | null {
  return pathname.match(/^\/app\/project\/([^/]+)/)?.[1] ?? null;
}

export default function V2AppShell({
  children,
  email,
  onSignOut,
}: {
  children: React.ReactNode;
  email: string | null;
  onSignOut: () => void;
}) {
  const pathname = usePathname();
  const pathProjectId = useMemo(() => projectIdFromPath(pathname), [pathname]);
  const [secondaryProjectId, setSecondaryProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("Your projects");

  useEffect(() => {
    if (pathProjectId) {
      setSecondaryProjectId(pathProjectId);
      return;
    }
    const projectFromQuery = new URLSearchParams(window.location.search).get("project");
    setSecondaryProjectId(projectFromQuery || null);
  }, [pathProjectId, pathname]);

  const projectId = pathProjectId ?? secondaryProjectId;

  useEffect(() => {
    let cancelled = false;
    if (!projectId) {
      setProjectName("Your projects");
      return;
    }
    getV2Project(projectId)
      .then((project) => {
        if (!cancelled) setProjectName(project.display_name);
      })
      .catch(() => {
        if (!cancelled) setProjectName("Current project");
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const projectBase = projectId ? `/app/project/${projectId}` : "/app/projects";
  const projectContext = projectId ? `?project=${encodeURIComponent(projectId)}` : "";
  const characterHref = `/app/character${projectContext}`;
  const settingsHref = `/app/settings${projectContext}`;
  const characterActive = pathname === "/app/character";
  const settingsActive = pathname === "/app/settings";

  const isActive = (suffix: string) => {
    if (!projectId) return suffix === "" && pathname === "/app/projects";
    const href = `${projectBase}${suffix}`;
    return suffix === "" ? pathname === href : pathname.startsWith(href);
  };

  const nav = (
    <>
      <nav className="v2-nav" aria-label="Project navigation">
        {primaryItems.map((item) => {
          const href = projectId ? `${projectBase}${item.suffix}` : "/app/projects";
          return (
            <Link
              key={item.label}
              href={href}
              className={isActive(item.suffix) ? "v2-nav-link is-active" : "v2-nav-link"}
              aria-current={isActive(item.suffix) ? "page" : undefined}
            >
              <span className="v2-nav-dot" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <nav className="v2-nav v2-nav-secondary" aria-label="Account navigation">
        <Link
          href={characterHref}
          className={characterActive ? "v2-nav-link is-active" : "v2-nav-link"}
          aria-current={characterActive ? "page" : undefined}
        >
          <span className="v2-nav-dot" aria-hidden="true" />
          Character
        </Link>
        <Link
          href={settingsHref}
          className={settingsActive ? "v2-nav-link is-active" : "v2-nav-link"}
          aria-current={settingsActive ? "page" : undefined}
        >
          <span className="v2-nav-dot" aria-hidden="true" />
          Settings
        </Link>
      </nav>
    </>
  );

  return (
    <div className="v2-shell">
      <aside className="v2-sidebar">
        <Link href="/app/projects" className="v2-brand" aria-label="Codize projects">
          CODIZE<span>_</span>
        </Link>
        <Link href="/app/projects" className="v2-project-switcher">
          <span>
            <small>Current project</small>
            <strong>{projectName}</strong>
          </span>
          <span aria-hidden="true">⌄</span>
        </Link>
        {nav}
        <div className="v2-account">
          <span title={email ?? undefined}>{email ?? "Signed in"}</span>
          <button type="button" onClick={onSignOut}>Sign out</button>
        </div>
      </aside>

      <header className="v2-mobile-header">
        <Link href="/app/projects" className="v2-brand" aria-label="Codize projects">
          CODIZE<span>_</span>
        </Link>
        <details className="v2-mobile-menu">
          <summary aria-label="Open account menu">{projectName}</summary>
          <div>
            <Link href="/app/projects">Switch project</Link>
            <Link href={characterHref} aria-current={characterActive ? "page" : undefined}>Character</Link>
            <Link href={settingsHref} aria-current={settingsActive ? "page" : undefined}>Settings</Link>
            <button type="button" onClick={onSignOut}>Sign out</button>
          </div>
        </details>
      </header>

      <main
        className={pathname.endsWith("/build") ? "v2-main v2-main-build" : "v2-main"}
        id="main-content"
      >
        {children}
      </main>

      <nav className="v2-bottom-nav" aria-label="Project navigation">
        {primaryItems.map((item) => {
          const href = projectId ? `${projectBase}${item.suffix}` : "/app/projects";
          return (
            <Link
              key={item.label}
              href={href}
              className={isActive(item.suffix) ? "is-active" : ""}
              aria-current={isActive(item.suffix) ? "page" : undefined}
            >
              <span className="v2-nav-dot" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
