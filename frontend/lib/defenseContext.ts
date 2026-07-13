// Defense context summary helpers (M14C) — pure and deterministic, like
// promptBuilder/report/phaseGuide. The backend's /gate/context-summary is
// metadata-only (source labels + presence + truncation, never content); these
// helpers turn it into the calm ready-state UI: grouped chips, one honest
// missing-source line, and deterministic preparation tips. No LLM anywhere,
// and no per-question source attribution is ever inferred here.

import type {
  ContextSummaryMissingSource,
  ContextSummarySource,
  DefenseContextSummary,
} from "./types";

// The student's four workflow sources, in Build Loop order — the display
// priority. System sources are grouped, never shown as individual chips.
export const WORKFLOW_SOURCE_ORDER = [
  "workflow.prompt_builder",
  "workflow.review_board",
  "workflow.evidence",
  "workflow.verification",
] as const;

// Where to add a missing artifact — the existing workflow pages.
export const WORKFLOW_PAGE_LINKS: Record<string, string> = {
  "workflow.prompt_builder": "/app/phase/prompt",
  "workflow.review_board": "/app/phase/review",
  "workflow.evidence": "/app/phase/evidence",
  "workflow.verification": "/app/phase/verify",
};

export interface GroupedSummary {
  /** Present workflow sources, Build Loop order. */
  workflow: ContextSummarySource[];
  /** Missing workflow sources, Build Loop order — optional, never an error. */
  missingWorkflow: ContextSummaryMissingSource[];
  /** Any system source (project / phase / progress / intake) is present. */
  hasSystemContext: boolean;
  hasWorkflowContext: boolean;
}

function workflowIndex(sourceId: string): number {
  const i = (WORKFLOW_SOURCE_ORDER as readonly string[]).indexOf(sourceId);
  return i === -1 ? WORKFLOW_SOURCE_ORDER.length : i;
}

export function groupSummary(summary: DefenseContextSummary): GroupedSummary {
  const workflow = summary.included_sources
    .filter((s) => s.source_id.startsWith("workflow."))
    .sort((a, b) => workflowIndex(a.source_id) - workflowIndex(b.source_id));
  const missingWorkflow = summary.missing_sources
    .filter((m) => m.source_id.startsWith("workflow."))
    .sort((a, b) => workflowIndex(a.source_id) - workflowIndex(b.source_id));
  return {
    workflow,
    missingWorkflow,
    hasSystemContext: summary.included_sources.some(
      (s) => !s.source_id.startsWith("workflow.")
    ),
    hasWorkflowContext: workflow.length > 0,
  };
}

// One deterministic preparation tip per recorded source; the sparse fallback
// keeps missing artifacts from ever feeling like a blocker.
const PREPARATION_TIPS: Record<string, string> = {
  "workflow.prompt_builder":
    "Be ready to explain why you asked AI for this implementation.",
  "workflow.review_board":
    "Be ready to explain what changed and what you reviewed.",
  "workflow.evidence":
    "Be ready to explain what your evidence shows — and what it does not prove.",
  "workflow.verification": "Be ready to explain how you checked behavior.",
};

export const SPARSE_PREPARATION_TIP =
  "Your anchor and phase context are enough to begin.";

export function preparationTips(summary: DefenseContextSummary): string[] {
  const tips = groupSummary(summary)
    .workflow.map((s) => PREPARATION_TIPS[s.source_id])
    .filter((tip): tip is string => Boolean(tip));
  return tips.length ? tips : [SPARSE_PREPARATION_TIP];
}

// "Evidence and Verification not added yet — optional, you can still continue."
export function missingNote(missing: ContextSummaryMissingSource[]): string | null {
  if (!missing.length) return null;
  const labels = missing.map((m) => m.label);
  const joined =
    labels.length === 1
      ? labels[0]
      : `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}`;
  return `${joined} not added yet — optional, you can still continue.`;
}
