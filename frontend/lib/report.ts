// Pure presentation and export rules for the authoritative M16C.1 Defense
// Report response. Nothing here parses raw workflow JSON or derives authority.

import { evidenceKindLabel as linkedEvidenceKindLabel } from "./evidence";
import { sourceStatePresentation } from "./defenseContext";
import type {
  ChangeMapCategory,
  ChangeMapStudentDecision,
  CuratedWorkflowContext,
  DefenseReport,
  DefenseWorkflowSourceId,
  EvidenceKind,
  EvidenceStatus,
  ReportDefenseState,
  ReportEvidenceEntry,
  ReportVerificationResult,
  ReviewDecision,
  WorkflowArtifactState,
  WorkflowContextSource,
} from "./types";

export const REPORT_SOURCE_ORDER: readonly DefenseWorkflowSourceId[] = [
  "change_map",
  "review",
  "verification",
  "evidence",
];

export const REPORT_SOURCE_LABELS: Record<DefenseWorkflowSourceId, string> = {
  change_map: "Change Map",
  review: "Review",
  verification: "Verification",
  evidence: "Evidence",
};

export interface LabelDescription {
  label: string;
  description: string;
}

const CONTEXT_SOURCE_PRESENTATION: Record<WorkflowContextSource, LabelDescription> = {
  defense_attempt: {
    label: "Project record captured for this Defense",
    description:
      "The workflow sections in this report use the server-owned project record captured for this Defense attempt.",
  },
  current_workflow: {
    label: "Current project record used for this legacy attempt",
    description:
      "This older Defense attempt did not store a workflow snapshot. The workflow sections below reflect the project’s current saved record and may differ from what existed when the Defense occurred.",
  },
};

export function workflowContextSourcePresentation(
  source: WorkflowContextSource
): LabelDescription {
  return CONTEXT_SOURCE_PRESENTATION[source];
}

const CATEGORY_LABELS: Record<ChangeMapCategory, string> = {
  changed_file: "Changed file",
  behavior_change: "Behavior change",
  implementation_decision: "Implementation decision",
  out_of_scope_change: "Out-of-scope change",
  security_sensitive_area: "Security-sensitive area",
  unresolved_risk: "Unresolved risk",
  unverified_behavior: "Unverified behavior",
  question_to_understand: "Question to understand",
};

export function reportCategoryLabel(category: ChangeMapCategory): string {
  return CATEGORY_LABELS[category];
}

const CHANGE_MAP_PROVENANCE: Record<ChangeMapStudentDecision, string> = {
  pending_review: "Awaiting student review",
  confirmed: "Student-confirmed AI inference",
  edited: "Student-edited change",
  rejected: "Rejected AI-inferred change",
  uncertain: "Uncertain",
  needs_inspection: "Needs inspection",
};

export function changeMapProvenanceLabel(
  origin: "ai_inferred" | "student_added",
  decision: ChangeMapStudentDecision
): string {
  return origin === "student_added" ? "Student-authored change" : CHANGE_MAP_PROVENANCE[decision];
}

const REVIEW_DECISIONS: Record<ReviewDecision, LabelDescription> = {
  pending: { label: "Not decided", description: "No Review decision was recorded." },
  keep: { label: "Keep", description: "The student chose to keep this change." },
  revise: { label: "Revise", description: "The student chose to revise this change." },
  remove: { label: "Remove", description: "The student chose to remove this change." },
  needs_verification: {
    label: "Needs testing",
    description: "The student marked this change for Verification.",
  },
  uncertain: { label: "Uncertain", description: "The student preserved uncertainty." },
};

export function reviewDecisionPresentation(decision: ReviewDecision): LabelDescription {
  return REVIEW_DECISIONS[decision];
}

const VERIFICATION_RESULTS: Record<ReportVerificationResult, LabelDescription> = {
  pass: { label: "Passed", description: "The student recorded this check as passed." },
  fail: { label: "Failed", description: "The student recorded this check as failed." },
  skipped: { label: "Skipped", description: "The student did not perform this check." },
  not_applicable: {
    label: "Not applicable",
    description: "The student recorded that this check did not apply.",
  },
  unrecorded: { label: "Not recorded", description: "No result was recorded for this check." },
};

export function verificationResultPresentation(
  result: ReportVerificationResult
): LabelDescription {
  return VERIFICATION_RESULTS[result];
}

const EVIDENCE_STATUS: Record<EvidenceStatus, LabelDescription> = {
  evidence_recorded: {
    label: "Student-provided Evidence",
    description: "The student recorded supporting material for this check.",
  },
  evidence_unavailable: {
    label: "Evidence unavailable",
    description: "The student recorded why supporting Evidence was unavailable.",
  },
  not_addressed: {
    label: "Evidence not addressed",
    description: "No Evidence or unavailable explanation was recorded for this check.",
  },
};

export function evidenceStatusPresentation(status: EvidenceStatus): LabelDescription {
  return EVIDENCE_STATUS[status];
}

export function reportEvidenceKindLabel(kind: EvidenceKind): string {
  return linkedEvidenceKindLabel(kind);
}

export function defenseOutcomeLabel(state: ReportDefenseState): string {
  switch (state) {
    case "passed":
      return "Defense passed";
    case "failed":
      return "Defense needs another attempt";
    case "in_progress":
      return "Defense in progress";
    case "not_started":
      return "Defense not started";
  }
}

export function defenseOutcomeTone(state: ReportDefenseState): string {
  if (state === "passed") return "ok";
  if (state === "failed") return "danger";
  if (state === "in_progress") return "warn";
  return "";
}

export function reportIsReady(report: DefenseReport): boolean {
  return report.defense.state === "passed" || report.defense.state === "failed";
}

export interface ReportSourceSummary {
  sourceId: DefenseWorkflowSourceId;
  label: string;
  state: WorkflowArtifactState;
  stateLabel: string;
  stateDescription: string;
  truncated: boolean;
}

export function reportSourceSummaries(context: CuratedWorkflowContext): ReportSourceSummary[] {
  return REPORT_SOURCE_ORDER.map((sourceId) => {
    const source = context[sourceId];
    const presentation = sourceStatePresentation(source.state);
    return {
      sourceId,
      label: REPORT_SOURCE_LABELS[sourceId],
      state: source.state,
      stateLabel: presentation.label,
      stateDescription: presentation.description,
      truncated: source.truncated,
    };
  });
}

export function sourceHasReportContent(
  sourceId: DefenseWorkflowSourceId,
  context: CuratedWorkflowContext
): boolean {
  switch (sourceId) {
    case "change_map":
      return context.change_map.items.length > 0;
    case "review":
      return context.review.items.length > 0 || context.review.manual !== null;
    case "verification":
      return context.verification.checks.length > 0 || context.verification.student_explanation !== null;
    case "evidence":
      return (
        context.evidence.records.length > 0 ||
        context.evidence.manual_entries.length > 0 ||
        context.evidence.manual_summary !== null
      );
  }
}

export function safeEvidenceHref(entry: ReportEvidenceEntry): string | null {
  if (entry.kind !== "repo_url" && entry.kind !== "app_url") return null;
  try {
    const url = new URL(entry.content);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function escapeMarkdown(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/([\\`*_{}\[\]()#+\-.!|])/g, "\\$1")
    .replace(/\r?\n/g, "  \n");
}

function mdLine(label: string, value: string | null | undefined): string {
  return `- **${label}:** ${value ? escapeMarkdown(value) : "_Not recorded_"}`;
}

function mdSection(title: string, lines: string[]): string[] {
  return [`## ${title}`, "", ...lines, ""];
}

export function buildReportMarkdown(report: DefenseReport): string {
  const contextSource = workflowContextSourcePresentation(report.workflow_context_source);
  const context = report.workflow_context;
  const out: string[] = [
    "# Defense Report",
    "",
    mdLine("Phase", `${report.phase_number} — ${report.phase_title}`),
    mdLine("Defense outcome", defenseOutcomeLabel(report.defense.state)),
    mdLine("Workflow context", contextSource.label),
    "",
    escapeMarkdown(contextSource.description),
    "",
    `> ${escapeMarkdown(report.truth_notice)}`,
    "",
  ];

  out.push(
    ...mdSection(
      "Project record",
      reportSourceSummaries(context).map(
        (source) =>
          `- **${source.label}:** ${source.stateLabel}${source.truncated ? " — long details shortened" : ""}`
      )
    )
  );

  const changeLines = context.change_map.items.length
    ? context.change_map.items.flatMap((item) => [
        `- **${changeMapProvenanceLabel(item.origin, item.student_decision)} · ${reportCategoryLabel(item.category)}**`,
        `  - ${escapeMarkdown(item.text)}`,
        ...(item.uncertainty_reason
          ? [`  - Uncertainty: ${escapeMarkdown(item.uncertainty_reason)}`]
          : []),
        ...(item.student_note ? [`  - Student note: ${escapeMarkdown(item.student_note)}`] : []),
      ])
    : [`_${sourceStatePresentation(context.change_map.state).description}_`];
  out.push(...mdSection("Change Map", changeLines));

  const reviewLines: string[] = [];
  for (const item of context.review.items) {
    reviewLines.push(
      `- **${reviewDecisionPresentation(item.review_decision).label} · ${reportCategoryLabel(item.category)}**`,
      `  - Reviewed change: ${escapeMarkdown(item.reviewed_text)}`
    );
    if (item.student_rationale) reviewLines.push(`  - Student rationale: ${escapeMarkdown(item.student_rationale)}`);
    if (item.student_revision) reviewLines.push(`  - Student revision: ${escapeMarkdown(item.student_revision)}`);
  }
  if (context.review.manual) {
    const manual = context.review.manual;
    reviewLines.push("- **Manual Review record**");
    if (manual.files_changed.length) reviewLines.push(`  - Files changed: ${escapeMarkdown(manual.files_changed.join(", "))}`);
    for (const [label, value] of [
      ["AI generated", manual.ai_generated],
      ["Accepted", manual.accepted],
      ["Rejected", manual.rejected],
      ["Edited manually", manual.edited_manually],
      ["AI assumptions", manual.ai_assumptions],
      ["Least confident", manual.least_confident],
      ["Out-of-scope changes", manual.out_of_scope_changes],
    ] as const) {
      if (value) reviewLines.push(`  - ${label}: ${escapeMarkdown(value)}`);
    }
  }
  out.push(
    ...mdSection(
      "Review",
      reviewLines.length ? reviewLines : [`_${sourceStatePresentation(context.review.state).description}_`]
    )
  );

  const verificationLines = context.verification.checks.length
    ? context.verification.checks.flatMap((check) => [
        `- **${verificationResultPresentation(check.result).label}:** ${escapeMarkdown(check.check)}`,
        ...(check.result_notes ? [`  - What happened: ${escapeMarkdown(check.result_notes)}`] : []),
      ])
    : [`_${sourceStatePresentation(context.verification.state).description}_`];
  if (context.verification.student_explanation) {
    verificationLines.push(`- Student explanation: ${escapeMarkdown(context.verification.student_explanation)}`);
  }
  out.push(...mdSection("Verification", verificationLines));

  const evidenceLines: string[] = [];
  for (const record of context.evidence.records) {
    evidenceLines.push(
      `- **${evidenceStatusPresentation(record.evidence_status).label}:** ${escapeMarkdown(record.check_context)}`,
      `  - Recorded Verification result: ${verificationResultPresentation(record.verification_result).label}`
    );
    if (record.verification_notes) evidenceLines.push(`  - Verification notes: ${escapeMarkdown(record.verification_notes)}`);
    for (const entry of record.entries) {
      evidenceLines.push(`  - ${reportEvidenceKindLabel(entry.kind)}: ${escapeMarkdown(entry.content)}`);
    }
    if (record.student_explanation) evidenceLines.push(`  - Student explanation: ${escapeMarkdown(record.student_explanation)}`);
    if (record.unavailable_reason) evidenceLines.push(`  - Unavailable reason: ${escapeMarkdown(record.unavailable_reason)}`);
    if (record.stale_support_omitted) evidenceLines.push("  - Evidence needs updating; prior supporting content is not shown as current.");
  }
  for (const entry of context.evidence.manual_entries) {
    evidenceLines.push(`- **Manual student-provided Evidence · ${reportEvidenceKindLabel(entry.kind)}:** ${escapeMarkdown(entry.content)}`);
  }
  if (context.evidence.manual_summary) evidenceLines.push(`- Manual student summary: ${escapeMarkdown(context.evidence.manual_summary)}`);
  out.push(
    ...mdSection(
      "Evidence",
      evidenceLines.length ? evidenceLines : [`_${sourceStatePresentation(context.evidence.state).description}_`]
    )
  );

  const transcriptLines = report.defense.turns.length
    ? report.defense.turns.flatMap((turn) => [
        `### Question ${turn.turn}`,
        "",
        escapeMarkdown(turn.question),
        "",
        `**Your response:** ${turn.answer ? escapeMarkdown(turn.answer) : "_Not recorded_"}`,
        "",
      ])
    : ["_No student-safe Defense transcript is available._"];
  out.push(...mdSection("Project Defense", transcriptLines));
  out.push(
    ...mdSection("Defense outcome", [
      mdLine("Outcome", report.defense.evaluator_outcome ?? defenseOutcomeLabel(report.defense.state)),
      mdLine("Recorded evaluator feedback", report.defense.evaluator_reason),
    ])
  );

  return out.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
}
