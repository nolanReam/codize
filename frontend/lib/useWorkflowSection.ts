"use client";

// Shared state machine for the four Build Loop artifact pages: load the
// current phase + its stored section, then save with PUT (full-section
// replace, per the backend contract). 409 = workspace not ready (no active
// roadmap yet) — surfaced as `notReady` so pages can point at intake.

import { useCallback, useEffect, useState } from "react";

import { ApiError, getCurrentPhase, getWorkflow, saveWorkflowSection } from "./api";
import type {
  PhaseView,
  PromptBuilderArtifact,
  StoredChangeMap,
  WorkflowSectionName,
  WorkflowSections,
} from "./types";

export function useWorkflowSection<S extends WorkflowSectionName>(section: S) {
  const [phase, setPhase] = useState<PhaseView | null>(null);
  const [stored, setStored] = useState<WorkflowSections[S] | null>(null);
  const [sections, setSections] = useState<WorkflowSections | null>(null);
  const [changeMap, setChangeMap] = useState<StoredChangeMap | null>(null);
  const [promptHistory, setPromptHistory] = useState<PromptBuilderArtifact[]>([]);
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
      setSections(workflow.sections);
      setChangeMap(workflow.change_map);
      setPromptHistory(workflow.prompt_history ?? []);
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
      if (!phase) return null;
      setSaving(true);
      setSaveError(null);
      try {
        const result = await saveWorkflowSection(phase.phase, section, payload);
        setStored(result.artifact as WorkflowSections[S]);
        setSections((current) => current ? { ...current, [section]: result.artifact } : current);
        setSavedAt(result.artifact.saved_at ?? null);
        if (result.prompt_history) setPromptHistory(result.prompt_history);
        return result.artifact as WorkflowSections[S];
      } catch (err) {
        setSaveError(err instanceof ApiError ? err.message : "Couldn't save. Try again.");
        return null;
      } finally {
        setSaving(false);
      }
    },
    [phase, section]
  );

  // Dedicated lifecycle routes (Change Map-linked Review initialization) still
  // return the same section artifact. Apply that response to this one shared
  // state machine instead of creating a second workflow fetch/store system.
  const applyArtifact = useCallback((artifact: WorkflowSections[S]) => {
    setStored(artifact);
    setSections((current) => current ? { ...current, [section]: artifact } : current);
    setSavedAt((artifact as { saved_at?: string }).saved_at ?? null);
    setSaveError(null);
  }, [section]);

  return {
    phase,
    stored,
    sections,
    changeMap,
    promptHistory,
    loading,
    error,
    notReady,
    reload: load,
    save,
    applyArtifact,
    saving,
    saveError,
    savedAt,
  };
}
