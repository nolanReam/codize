"use client";

// Shared state machine for the four Build Loop artifact pages: load the
// current phase + its stored section, then save with PUT (full-section
// replace, per the backend contract). 409 = workspace not ready (no active
// roadmap yet) — surfaced as `notReady` so pages can point at intake.

import { useCallback, useEffect, useState } from "react";

import { ApiError, getCurrentPhase, getWorkflow, saveWorkflowSection } from "./api";
import type { PhaseView, StoredChangeMap, WorkflowSectionName, WorkflowSections } from "./types";

export function useWorkflowSection<S extends WorkflowSectionName>(section: S) {
  const [phase, setPhase] = useState<PhaseView | null>(null);
  const [stored, setStored] = useState<WorkflowSections[S] | null>(null);
  const [changeMap, setChangeMap] = useState<StoredChangeMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notReady, setNotReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotReady(false);
    try {
      const current = await getCurrentPhase();
      const workflow = await getWorkflow(current.phase);
      setPhase(current);
      setStored(workflow.sections[section]);
      setChangeMap(workflow.change_map);
      setSavedAt((workflow.sections[section] as { saved_at?: string } | null)?.saved_at ?? null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setNotReady(true);
      } else {
        setError(err instanceof ApiError ? err.message : "Couldn't load this workspace.");
      }
    } finally {
      setLoading(false);
    }
  }, [section]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(
    async (payload: Parameters<typeof saveWorkflowSection<S>>[2]) => {
      if (!phase) return false;
      setSaving(true);
      setSaveError(null);
      try {
        const result = await saveWorkflowSection(phase.phase, section, payload);
        setStored(result.artifact as WorkflowSections[S]);
        setSavedAt(result.artifact.saved_at);
        return true;
      } catch (err) {
        setSaveError(err instanceof ApiError ? err.message : "Couldn't save. Try again.");
        return false;
      } finally {
        setSaving(false);
      }
    },
    [phase, section]
  );

  return {
    phase,
    stored,
    changeMap,
    loading,
    error,
    notReady,
    reload: load,
    save,
    saving,
    saveError,
    savedAt,
  };
}
