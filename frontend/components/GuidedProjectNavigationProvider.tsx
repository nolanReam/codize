"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError, getCurrentGate, getEvaluation, getIntakeStatus, getWorkflow } from "@/lib/api";
import {
  buildGuidedProjectNavigation,
  GUIDED_NAVIGATION_REFRESH_EVENT,
  type GuidedProjectNavigation,
} from "@/lib/guidedProjectNavigation";
import type { Evaluation, GateCurrent, WorkflowPhaseState } from "@/lib/types";

type NavigationLoadState = "loading" | "ready" | "error";

interface GuidedNavigationContextValue {
  state: NavigationLoadState;
  error: string | null;
  navigation: GuidedProjectNavigation;
  evaluation: Evaluation | null;
  workflow: WorkflowPhaseState | null;
  gate: GateCurrent | null;
  refresh: () => Promise<void>;
}

const EMPTY_NAVIGATION = buildGuidedProjectNavigation({
  evaluation: null,
  workflow: null,
  gate: null,
});

const GuidedNavigationContext = createContext<GuidedNavigationContextValue | null>(null);

export default function GuidedProjectNavigationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = useState<NavigationLoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowPhaseState | null>(null);
  const [gate, setGate] = useState<GateCurrent | null>(null);
  const [projectLabel, setProjectLabel] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(async () => {
    const activeRequest = ++requestId.current;
    setState((current) => (current === "ready" ? current : "loading"));
    setError(null);
    try {
      const nextEvaluation = await getEvaluation();
      if (activeRequest !== requestId.current) return;
      setEvaluation(nextEvaluation);

      if (
        nextEvaluation.state === "not_started" ||
        nextEvaluation.state === "intake_needed" ||
        nextEvaluation.state === "roadmap_needed" ||
        nextEvaluation.current_phase == null
      ) {
        const intake = await getIntakeStatus().catch(() => null);
        if (activeRequest !== requestId.current) return;
        setWorkflow(null);
        setGate(null);
        setProjectLabel(intake?.answers?.purpose ?? null);
        setState("ready");
        return;
      }

      const [nextWorkflow, nextGate, intake] = await Promise.all([
        getWorkflow(nextEvaluation.current_phase),
        getCurrentGate(),
        getIntakeStatus().catch(() => null),
      ]);
      if (activeRequest !== requestId.current) return;
      setWorkflow(nextWorkflow);
      setGate(nextGate);
      setProjectLabel(intake?.answers?.purpose ?? null);
      setState("ready");
    } catch (caught) {
      if (activeRequest !== requestId.current) return;
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Project progress is temporarily unavailable."
      );
      setState("error");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const handleRefresh = () => void refresh();
    window.addEventListener(GUIDED_NAVIGATION_REFRESH_EVENT, handleRefresh);
    window.addEventListener("focus", handleRefresh);
    return () => {
      requestId.current += 1;
      window.removeEventListener(GUIDED_NAVIGATION_REFRESH_EVENT, handleRefresh);
      window.removeEventListener("focus", handleRefresh);
    };
  }, [refresh]);

  const navigation = useMemo(
    () =>
      state === "ready"
        ? buildGuidedProjectNavigation({ evaluation, workflow, gate, projectLabel })
        : {
            ...EMPTY_NAVIGATION,
            projectLabel: projectLabel?.trim() || "Your project",
            evaluation,
            workflow,
          },
    [evaluation, gate, projectLabel, state, workflow]
  );

  const value = useMemo<GuidedNavigationContextValue>(
    () => ({ state, error, navigation, evaluation, workflow, gate, refresh }),
    [error, evaluation, gate, navigation, refresh, state, workflow]
  );

  return (
    <GuidedNavigationContext.Provider value={value}>
      {children}
    </GuidedNavigationContext.Provider>
  );
}

export function useGuidedProjectNavigation(): GuidedNavigationContextValue {
  const value = useContext(GuidedNavigationContext);
  if (!value) {
    throw new Error("useGuidedProjectNavigation must be used inside its provider.");
  }
  return value;
}
