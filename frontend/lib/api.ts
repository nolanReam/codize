// Codize API client. Every call attaches the Supabase Bearer JWT; the backend
// is the source of truth for auth and ownership. Backend errors arrive as
// {"error": {"status", "message"}} — 4xx messages are safe client strings by
// backend design and are shown as-is; 5xx bodies are never surfaced.

import { getAccessToken } from "./supabase";
import type {
  Evaluation,
  EvidenceArtifact,
  GateCurrent,
  IntakeCompleteResult,
  IntakeQuestion,
  IntakeStatus,
  PhaseList,
  PhaseView,
  PromptBuilderArtifact,
  ReconnectionState,
  ReviewBoardArtifact,
  VerificationArtifact,
  WorkflowPhaseState,
  WorkflowSectionName,
} from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const GENERIC: Record<number, string> = {
  401: "Your session has expired. Sign in again.",
  403: "That isn't yours to see.",
  404: "Not found.",
  409: "That action isn't available right now.",
  422: "That input couldn't be accepted.",
};

function baseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) throw new ApiError(0, "The API is not configured (NEXT_PUBLIC_API_BASE_URL).");
  return base.replace(/\/+$/, "");
}

async function request<T>(
  path: string,
  init: { method?: string; body?: unknown } = {}
): Promise<T> {
  const token = await getAccessToken();
  if (!token) throw new ApiError(401, "You need to sign in first.");

  let res: Response;
  try {
    res = await fetch(`${baseUrl()}${path}`, {
      method: init.method ?? "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Couldn't reach the Codize backend. Is it running?");
  }

  if (res.ok) return (await res.json()) as T;

  let message =
    res.status >= 500
      ? "Something went wrong on the server. Try again."
      : (GENERIC[res.status] ?? "Request failed.");
  if (res.status < 500) {
    try {
      const body = (await res.json()) as { error?: { message?: unknown } };
      if (typeof body?.error?.message === "string" && body.error.message) {
        message = body.error.message;
      }
    } catch {
      // keep the generic message
    }
  }
  throw new ApiError(res.status, message);
}

// --- intake ------------------------------------------------------------------

export const getIntakeQuestions = () =>
  request<{ questions: IntakeQuestion[] }>("/intake/questions");
export const getIntakeStatus = () => request<IntakeStatus>("/intake/status");
export const submitIntakeAnswer = (question: number, answer: string) =>
  request<IntakeStatus>("/intake/answers", { method: "POST", body: { question, answer } });
export const completeIntake = () =>
  request<IntakeCompleteResult>("/intake/complete", { method: "POST" });

// --- roadmap / phases ----------------------------------------------------------

export const generateRoadmap = () =>
  request<{ roadmap: unknown }>("/roadmap/generate", { method: "POST" });
export const getPhases = () => request<PhaseList>("/phases");
export const getCurrentPhase = () => request<PhaseView>("/phases/current");
export const getPhase = (n: number) => request<PhaseView>(`/phases/${n}`);
export const setTaskCompletion = (phase: number, taskId: string, completed: boolean) =>
  request<PhaseView>(`/phases/${phase}/tasks/${taskId}`, {
    method: "PATCH",
    body: { completed },
  });

// --- workflow artifacts (M13B) --------------------------------------------------

export const getWorkflow = (phase: number) =>
  request<WorkflowPhaseState>(`/workflow/${phase}`);

type SectionPayloadMap = {
  prompt_builder: Omit<PromptBuilderArtifact, "saved_at">;
  review_board: Omit<ReviewBoardArtifact, "saved_at">;
  evidence: Omit<EvidenceArtifact, "saved_at">;
  verification: Omit<VerificationArtifact, "saved_at">;
};

export const saveWorkflowSection = <S extends WorkflowSectionName>(
  phase: number,
  section: S,
  payload: SectionPayloadMap[S]
) =>
  request<{ phase: number; section: S; artifact: SectionPayloadMap[S] & { saved_at: string } }>(
    `/workflow/${phase}/${section}`,
    { method: "PUT", body: payload }
  );

// --- reconnection / evaluation / gate --------------------------------------------

export const getReconnection = () => request<ReconnectionState>("/reconnection");
export const acknowledgeReconnection = () =>
  request<{ acknowledged: boolean }>("/reconnection/acknowledge", { method: "POST" });
export const getEvaluation = () => request<Evaluation>("/evaluation");
export const getCurrentGate = () => request<GateCurrent>("/gate/current");
