"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { getProjectRefs } from "@/lib/v2-api";
import type { ProjectRefView } from "@/lib/v2-types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRefView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProjectRefs()
      .then((response) => setProjects(response.projects))
      .catch((reason) =>
        setError(reason instanceof ApiError ? reason.message : "Couldn't load your projects.")
      );
  }, []);

  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header">
        <p className="v2-eyebrow">Projects</p>
        <h1>Your projects</h1>
        <p>Pick up one project and its current change.</p>
      </header>
      {error && <V2Notice tone="error">{error}</V2Notice>}
      {!projects && !error && <V2Card><V2Skeleton lines={4} /></V2Card>}
      {projects?.length === 0 && (
        <V2Card>
          <h2>No projects yet</h2>
          <p>Your first V2 project will appear here after setup.</p>
        </V2Card>
      )}
      <div className="v2-project-list">
        {projects?.map((project) => (
          <Link
            key={`${project.workflow_version}-${project.project_id}`}
            href={
              project.workflow_version === "v2"
                ? `/app/project/${project.project_id}`
                : "/app"
            }
            className="v2-project-row"
          >
            <span className="v2-project-mark" aria-hidden="true" />
            <span>
              <strong>{project.display_name}</strong>
              <small>{project.workflow_version === "v2" ? "V2 project" : "Legacy project"}</small>
            </span>
            <span aria-hidden="true">→</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
