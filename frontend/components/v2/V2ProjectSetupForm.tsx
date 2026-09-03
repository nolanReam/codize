"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { V2Button, V2Notice } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { establishManualProject, saveSetupDraft } from "@/lib/v2-api";
import type { V2ProjectView } from "@/lib/v2-types";

export default function V2ProjectSetupForm({
  project,
  onComplete,
}: {
  project: V2ProjectView;
  onComplete: () => Promise<void>;
}) {
  const [busy, setBusy] = useState<"draft" | "finish" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [context, setContext] = useState(project.setup_draft?.project_context ?? "");
  const [change, setChange] = useState(project.setup_draft?.initial_change_label ?? "");
  const [done, setDone] = useState(project.setup_draft?.done_condition ?? "");
  const [invalidFields, setInvalidFields] = useState({
    context: false,
    change: false,
    done: false,
  });
  const contextRef = useRef<HTMLTextAreaElement>(null);
  const changeRef = useRef<HTMLInputElement>(null);
  const doneRef = useRef<HTMLTextAreaElement>(null);
  const finishCommand = useRef<{ setup: string; item: string } | null>(null);
  const draftCommand = useRef<{ signature: string; commandId: string } | null>(null);
  const validationErrorId = "v2-project-setup-validation-error";
  const isIdea = project.setup_resume_step === "idea_capture";
  const signature = JSON.stringify([context.trim(), change.trim(), done.trim()]);
  const savedSignature = JSON.stringify([
    project.setup_draft?.project_context ?? "",
    project.setup_draft?.initial_change_label ?? "",
    project.setup_draft?.done_condition ?? "",
  ]);

  useEffect(() => {
    setContext(project.setup_draft?.project_context ?? "");
    setChange(project.setup_draft?.initial_change_label ?? "");
    setDone(project.setup_draft?.done_condition ?? "");
    setInvalidFields({ context: false, change: false, done: false });
  }, [project.project_id, project.version, project.setup_draft]);

  const saveDraft = async () => {
    if (signature === savedSignature) return;
    if (draftCommand.current?.signature !== signature) {
      draftCommand.current = { signature, commandId: crypto.randomUUID() };
    }
    setBusy("draft");
    setError(null);
    setNotice(null);
    try {
      await saveSetupDraft(
        project.project_id, project.version, draftCommand.current.commandId,
        context.trim(), change.trim(), done.trim()
      );
      setNotice("Setup progress saved.");
      await onComplete();
      draftCommand.current = null;
    } catch (reason) {
      await onComplete().catch(() => undefined);
      setError(
        reason instanceof ApiError && reason.status === 409
          ? "Setup changed somewhere else. The latest saved answers are loaded."
          : reason instanceof ApiError
            ? reason.message
            : "Setup progress couldn’t save. Your answers are still here—try again."
      );
    } finally {
      setBusy(null);
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = { context: context.trim(), change: change.trim(), done: done.trim() };
    const invalid = {
      context: !trimmed.context,
      change: !trimmed.change,
      done: !trimmed.done,
    };
    if (invalid.context || invalid.change || invalid.done) {
      setInvalidFields(invalid);
      setError("Fill in each field so your first change has a clear finish line.");
      const firstInvalidField = invalid.context
        ? contextRef.current
        : invalid.change
          ? changeRef.current
          : doneRef.current;
      firstInvalidField?.focus();
      return;
    }

    finishCommand.current ??= { setup: crypto.randomUUID(), item: crypto.randomUUID() };
    setInvalidFields({ context: false, change: false, done: false });
    setBusy("finish");
    setError(null);
    setNotice(null);
    try {
      await establishManualProject(
        project.project_id,
        project.version,
        finishCommand.current.setup,
        trimmed.context,
        finishCommand.current.item,
        trimmed.change,
        trimmed.done
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
      setBusy(null);
    }
  };

  return (
    <form onSubmit={submit} className="v2-setup-form">
      <p className="v2-card-label">Continue setup</p>
      <h2>{isIdea ? "Shape your first useful change" : "Continue from what exists"}</h2>
      <p className="v2-muted">
        Project ID: <code>{project.project_id}</code>
      </p>
      {error && (
        <div id={validationErrorId}>
          <V2Notice tone="error">{error}</V2Notice>
        </div>
      )}
      {notice && <V2Notice tone="success">{notice}</V2Notice>}
      <label>
        {isIdea ? "What do you want to build?" : "What are you building?"}
        <textarea ref={contextRef} name="context" rows={3} maxLength={8192} autoFocus value={context}
          aria-invalid={invalidFields.context || undefined}
          aria-describedby={invalidFields.context ? validationErrorId : undefined}
          onChange={(event) => {
            setContext(event.target.value);
            if (event.target.value.trim()) {
              setInvalidFields((current) => ({ ...current, context: false }));
            }
          }} />
      </label>
      <label>
        What’s the first change?
        <input ref={changeRef} name="change" maxLength={200} value={change}
          aria-invalid={invalidFields.change || undefined}
          aria-describedby={invalidFields.change ? validationErrorId : undefined}
          onChange={(event) => {
            setChange(event.target.value);
            if (event.target.value.trim()) {
              setInvalidFields((current) => ({ ...current, change: false }));
            }
          }} />
      </label>
      <label>
        How will you know it’s done?
        <textarea ref={doneRef} name="done" rows={3} maxLength={4096} value={done}
          aria-invalid={invalidFields.done || undefined}
          aria-describedby={invalidFields.done ? validationErrorId : undefined}
          onChange={(event) => {
            setDone(event.target.value);
            if (event.target.value.trim()) {
              setInvalidFields((current) => ({ ...current, done: false }));
            }
          }} />
      </label>
      <div className="v2-action-row">
        <V2Button type="button" tone="secondary" disabled={busy !== null || signature === savedSignature}
          onClick={() => void saveDraft()}>
          {busy === "draft" ? "Saving progress…" : "Save progress"}
        </V2Button>
        <V2Button type="submit" disabled={busy !== null}>
          {busy === "finish" ? "Finishing setup…" : "Finish setup"}
        </V2Button>
      </div>
    </form>
  );
}
