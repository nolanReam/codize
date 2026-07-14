// Pure presentation rules for the metadata-only M16C.1 Defense summary.
// The browser receives source state, label, and truncation only. It never
// reconstructs workflow content or decides whether Defense is allowed.

import type {
  DefenseContextSummary,
  DefenseWorkflowSource,
  DefenseWorkflowSourceId,
  WorkflowArtifactState,
} from "./types";

export const DEFENSE_WORKFLOW_SOURCE_ORDER: readonly DefenseWorkflowSourceId[] = [
  "change_map",
  "review",
  "verification",
  "evidence",
];

export type SourceStateSeverity = "neutral" | "positive" | "attention" | "unavailable";

interface SourceStatePresentation {
  label: string;
  description: string;
  severity: SourceStateSeverity;
}

const SOURCE_STATE_PRESENTATION: Record<WorkflowArtifactState, SourceStatePresentation> = {
  current: {
    label: "Current",
    description: "This saved record is available as context for Project Defense.",
    severity: "positive",
  },
  missing: {
    label: "Not available",
    description: "No saved record is available for this source.",
    severity: "neutral",
  },
  incomplete: {
    label: "Incomplete",
    description: "This record exists but is not fully completed.",
    severity: "attention",
  },
  stale: {
    label: "Needs updating",
    description: "An upstream workflow step changed after this record was created.",
    severity: "attention",
  },
  manual: {
    label: "Manual record",
    description: "This record uses the earlier manual workflow format.",
    severity: "neutral",
  },
  malformed: {
    label: "Unavailable",
    description: "Codize could not safely use this optional record.",
    severity: "unavailable",
  },
};

export function sourceStatePresentation(state: WorkflowArtifactState): SourceStatePresentation {
  return SOURCE_STATE_PRESENTATION[state];
}

export function orderedWorkflowSources(summary: DefenseContextSummary): DefenseWorkflowSource[] {
  return [...summary.workflow_sources].sort(
    (left, right) =>
      DEFENSE_WORKFLOW_SOURCE_ORDER.indexOf(left.source_id) -
      DEFENSE_WORKFLOW_SOURCE_ORDER.indexOf(right.source_id)
  );
}

export function sourcePillClass(state: WorkflowArtifactState): string {
  const severity = sourceStatePresentation(state).severity;
  if (severity === "positive") return "ok";
  if (severity === "attention") return "warn";
  if (severity === "unavailable") return "danger";
  return "";
}

export const DEFENSE_TRUNCATION_EXPLANATION =
  "Some long details were shortened before being used as Defense context. Your saved project record was not changed.";
