"use client";

import { FormEvent, useRef, useState } from "react";

import { V2Button, V2Notice } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { establishManualProject } from "@/lib/v2-api";
import type { V2ProjectView } from "@/lib/v2-types";

export default function V2ProjectSetupForm({
  project,
  onComplete,
}: {
  project: V2ProjectView;
  onComplete: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const command = useRef<{ setup: string; item: string } | null>(null);
  const isIdea = project.setup_resume_step === "idea_capture";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const context = String(form.get("context") ?? "").trim();
    const change = String(form.get("change") ?? "").trim();
    const done = String(form.get("done") ?? "").trim();
    if (!context || !change || !done) {
      setError("Fill in each field so your first change has a clear finish line.");
      return;
    }

    command.current ??= { setup: crypto.randomUUID(), item: crypto.randomUUID() };
    setBusy(true);
    setError(null);
    try {
      await establishManualProject(
        project.project_id,
        project.version,
        command.current.setup,
        context,
        command.current.item,
        change,
        done
      );
      await onComplete();
    } catch (reason) {
      // A conflict or transport failure can mean the atomic setup committed but
      // its response was lost. Refresh canonical Project state before inviting
      // another mutation; the server also recognizes matching fresh-ID replays.
      await onComplete().catch(() => undefined);
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Setup couldn’t finish. Your answers are still here—try again."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="v2-setup-form">
      <p className="v2-card-label">Continue setup</p>
      <h2>{isIdea ? "Shape your first useful change" : "Continue from what exists"}</h2>
      <p className="v2-muted">
        Project ID: <code>{project.project_id}</code>
      </p>
      {error && <V2Notice tone="error">{error}</V2Notice>}
      <label>
        {isIdea ? "What do you want to build?" : "What are you building?"}
        <textarea name="context" rows={3} maxLength={8192} autoFocus />
      </label>
      <label>
        What’s the first change?
        <input name="change" maxLength={200} />
      </label>
      <label>
        How will you know it’s done?
        <textarea name="done" rows={3} maxLength={4096} />
      </label>
      <div className="v2-action-row">
        <V2Button type="submit" disabled={busy}>
          {busy ? "Saving setup…" : "Finish setup"}
        </V2Button>
      </div>
    </form>
  );
}
