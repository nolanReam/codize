"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { getV2Project } from "@/lib/v2-api";

const primaryItems = [
  { label: "Project", suffix: "", icon: "project" },
  { label: "Build", suffix: "/build", icon: "build" },
  { label: "Learning", suffix: "/learning", icon: "learning" },
  { label: "History", suffix: "/history", icon: "history" },
] as const;

type NavIconName = (typeof primaryItems)[number]["icon"] | "character" | "settings";

function V2NavIcon({ name }: { name: NavIconName }) {
  const paths: Record<NavIconName, React.ReactNode> = {
    project: <><path d="M3.5 9.5 10 4l6.5 5.5" /><path d="M5.5 8.5v7h9v-7M8.5 15.5v-4h3v4" /></>,
    build: <><path d="m7.5 5-4 5 4 5M12.5 5l4 5-4 5" /><path d="m11 3-2 14" /></>,
    learning: <><path d="M3.5 4.5h4A2.5 2.5 0 0 1 10 7v9a2.5 2.5 0 0 0-2.5-2.5h-4Z" /><path d="M16.5 4.5h-4A2.5 2.5 0 0 0 10 7v9a2.5 2.5 0 0 1 2.5-2.5h4Z" /></>,
    history: <><circle cx="10" cy="10" r="6.5" /><path d="M10 6.5V10l2.5 1.5M3.5 4.5v3h3" /></>,
    character: <><circle cx="10" cy="8" r="3" /><path d="M4.5 16c.7-2.8 2.5-4.2 5.5-4.2s4.8 1.4 5.5 4.2" /><path d="m15.7 3.5.4 1.1 1.1.4-1.1.4-.4 1.1-.4-1.1-1.1-.4 1.1-.4Z" /></>,
    settings: <><circle cx="10" cy="10" r="2.5" /><path d="M10 2.8v1.4M10 15.8v1.4M17.2 10h-1.4M4.2 10H2.8M15.1 4.9l-1 1M5.9 14.1l-1 1M15.1 15.1l-1-1M5.9 5.9l-1-1" /></>,
  };

  return (
    <svg className="v2-nav-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true" focusable="false">
      <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        {paths[name]}
      </g>
    </svg>
  );
}

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
              <V2NavIcon name={item.icon} />
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
          <V2NavIcon name="character" />
          Character
        </Link>
        <Link
          href={settingsHref}
          className={settingsActive ? "v2-nav-link is-active" : "v2-nav-link"}
          aria-current={settingsActive ? "page" : undefined}
        >
          <V2NavIcon name="settings" />
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
            <Link href="/app/projects" aria-label="Switch project">Switch project</Link>
            <Link href={characterHref} aria-label="Character" aria-current={characterActive ? "page" : undefined}><V2NavIcon name="character" />Character</Link>
            <Link href={settingsHref} aria-label="Settings" aria-current={settingsActive ? "page" : undefined}><V2NavIcon name="settings" />Settings</Link>
            <button type="button" aria-label="Sign out" onClick={onSignOut}>Sign out</button>
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
              <V2NavIcon name={item.icon} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
