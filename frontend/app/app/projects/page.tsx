"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";

import { V2Button, V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { createV2Project, getProjectRefs } from "@/lib/v2-api";
import type { ProjectRefView } from "@/lib/v2-types";

type Intent = "new_idea" | "already_building";

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectRefView[] | null>(null);
  const [intent, setIntent] = useState<Intent | null>(null);
  const [showSetup, setShowSetup] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const createCommand = useRef<string | null>(null);

  useEffect(() => {
    getProjectRefs().then((response) => {
      setProjects(response.projects);
      if (response.projects.length === 0) setShowSetup(true);
    }).catch((reason) => setError(reason instanceof ApiError ? reason.message : "Couldn't load your projects."));
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!intent) return;
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    if (!name) {
      setError("Give this project a name so you can find it again.");
      return;
    }
    createCommand.current ??= crypto.randomUUID();
    setBusy(true); setError(null);
    try {
      const created = await createV2Project(name, intent, createCommand.current);
      router.push(`/app/project/${created.project.project_id}`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Setup couldn't finish. Your answers are still here—try again.");
    } finally { setBusy(false); }
  };

  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header"><p className="v2-eyebrow">Projects</p><h1>Your projects</h1>
        <p>One project, one current change, one clear check.</p></header>
      {error && <V2Notice tone="error">{error}</V2Notice>}
      {!projects && !error && <V2Card><V2Skeleton lines={4} /></V2Card>}
      {showSetup && <V2Card className="v2-setup-card">
        {!intent ? <><p className="v2-card-label">Start here</p><h2>What are you bringing to Codize?</h2>
          <div className="v2-setup-choices">
            <button type="button" onClick={() => setIntent("new_idea")}><strong>I have an idea</strong><small>Shape the first useful change.</small></button>
            <button type="button" onClick={() => setIntent("already_building")}><strong>I’m already building</strong><small>Continue from what exists.</small></button>
            <button type="button" disabled><strong>Something broke</strong><small>Recovery-first setup is deferred. Active changes recover inside Build.</small></button>
          </div></> : <form onSubmit={submit} className="v2-setup-form">
          <p className="v2-card-label">{intent === "new_idea" ? "New project" : "Existing project"}</p>
          <label>Project name<input name="name" maxLength={120} autoFocus /></label>
          <div className="v2-action-row"><V2Button type="button" tone="ghost" onClick={() => setIntent(null)}>Back</V2Button>
            <V2Button type="submit" disabled={busy}>{busy ? "Creating…" : "Create draft"}</V2Button></div>
        </form>}
      </V2Card>}
      {projects && projects.length > 0 && <>
        <V2Button tone="secondary" onClick={() => { setShowSetup(true); setIntent(null); }}>Start a project</V2Button>
        <div className="v2-project-list">{projects.map((project) => (
          <Link key={`${project.workflow_version}-${project.project_id}`}
            href={project.workflow_version === "v2" ? `/app/project/${project.project_id}` : "/app"}
            className="v2-project-row"><span className="v2-project-mark" aria-hidden="true" />
            <span><strong>{project.display_name}</strong><small>{project.workflow_version === "v2" && project.lifecycle_state === "draft" ? "Continue setup" : project.workflow_version === "v2" ? "V2 project" : "Legacy project"}</small></span>
            <span aria-hidden="true">→</span></Link>))}</div>
      </>}
    </div>
  );
}
