import { describe, expect, it } from "vitest";

import {
  buildReportMarkdown,
  changeMapProvenanceLabel,
  defenseOutcomeLabel,
  evidenceStatusPresentation,
  reportIsReady,
  reportSourceSummaries,
  reviewDecisionPresentation,
  safeEvidenceHref,
  verificationResultPresentation,
  workflowContextSourcePresentation,
} from "./report";
import type { DefenseReport, WorkflowArtifactState } from "./types";

export function reportFixture(overrides: Partial<DefenseReport> = {}): DefenseReport {
  return {
    schema_version: "1.0",
    phase_number: 2,
    phase_title: "Data Model",
    workflow_context_source: "defense_attempt",
    workflow_context: {
      schema_version: "1.0",
      phase_number: 2,
      state: "incomplete",
      change_map: {
        state: "current",
        truncated: false,
        items: [
          {
            category: "implementation_decision",
            origin: "ai_inferred",
            student_decision: "confirmed",
            text: "<img src=x onerror=example()> uses user_id ownership.",
            provenance: "Student-confirmed AI-inferred Change Map item",
            ai_uncertainty: "supported",
            uncertainty_reason: null,
            student_note: "I checked the route.",
          },
          {
            category: "unresolved_risk",
            origin: "ai_inferred",
            student_decision: "rejected",
            text: "Rejected claim",
            provenance: "AI-inferred Change Map item rejected by the student",
            ai_uncertainty: "ambiguous",
            uncertainty_reason: "The import was incomplete.",
            student_note: null,
          },
        ],
      },
      review: {
        state: "current",
        truncated: false,
        manual: null,
        items: [
          {
            category: "implementation_decision",
            source_origin: "ai_inferred",
            source_student_decision: "confirmed",
            source_resolution: "confirmed",
            reviewed_text: "Use user_id per row.",
            review_decision: "needs_verification",
            student_rationale: "Ownership must be tested <script>example()</script>.",
            student_revision: null,
          },
        ],
      },
      verification: {
        state: "incomplete",
        truncated: false,
        student_explanation: "I ran the checks myself.",
        checks: [
          {
            check: "Create a record as user A.",
            result: "pass",
            result_notes: "A received 201.",
            category: "security_sensitive_area",
            provenance: "student_recorded",
          },
          {
            check: "Read it as user B.",
            result: "fail",
            result_notes: "B could still read it.",
            category: "security_sensitive_area",
            provenance: "student_recorded",
          },
          {
            check: "Browser flow",
            result: "skipped",
            result_notes: null,
            category: null,
            provenance: "student_recorded",
          },
          {
            check: "Mobile app",
            result: "not_applicable",
            result_notes: null,
            category: null,
            provenance: "student_recorded",
          },
          {
            check: "Failure case",
            result: "unrecorded",
            result_notes: null,
            category: null,
            provenance: "student_unrecorded",
          },
        ],
      },
      evidence: {
        state: "current",
        truncated: true,
        manual_entries: [],
        manual_summary: null,
        records: [
          {
            category: "security_sensitive_area",
            check_context: "Create a record as user A.",
            verification_result: "pass",
            verification_notes: "A received 201.",
            evidence_status: "evidence_recorded",
            entries: [
              { kind: "test_output", content: "3 passed <iframe src=x></iframe>" },
              { kind: "app_url", content: "https://example.test/result" },
            ],
            student_explanation: "This shows the tested happy path only.",
            unavailable_reason: null,
            stale_support_omitted: false,
          },
          {
            category: "security_sensitive_area",
            check_context: "Read it as user B.",
            verification_result: "fail",
            verification_notes: "B could still read it.",
            evidence_status: "evidence_unavailable",
            entries: [],
            student_explanation: null,
            unavailable_reason: "The hosted environment was offline <object>example</object>.",
            stale_support_omitted: false,
          },
        ],
      },
      content_truncated: true,
      content_redacted: false,
    },
    defense: {
      state: "failed",
      evaluator_outcome: "FAIL",
      evaluator_reason: "The ownership failure was not fully explained.",
      turns: [
        {
          turn: 1,
          question: "Why store user_id? <embed src=x>",
          answer: "To scope rows to a user. **not rendered**",
        },
      ],
    },
    truth_notice:
      "Workflow records are student-recorded or student-confirmed; Verification is not independent proof; Evidence is student-provided; PASS/FAIL is the evaluator's outcome. <img src=x>",
    ...overrides,
  };
}

describe("Defense Report presentation rules", () => {
  it("distinguishes attempt snapshots from the legacy current-workflow fallback", () => {
    expect(workflowContextSourcePresentation("defense_attempt").label).toContain("captured");
    const legacy = workflowContextSourcePresentation("current_workflow");
    expect(legacy.label).toContain("legacy attempt");
    expect(legacy.description).toContain("may differ");
    expect(legacy.label.toLowerCase()).not.toContain("snapshot");
  });

  it.each<[WorkflowArtifactState, string]>([
    ["current", "Current"],
    ["missing", "Not available"],
    ["incomplete", "Incomplete"],
    ["stale", "Needs updating"],
    ["manual", "Manual record"],
    ["malformed", "Unavailable"],
  ])("preserves the %s source state", (state, label) => {
    const report = reportFixture();
    report.workflow_context.change_map.state = state;
    expect(reportSourceSummaries(report.workflow_context)[0]).toMatchObject({ state, stateLabel: label });
  });

  it("preserves Change Map provenance and Review semantics", () => {
    expect(changeMapProvenanceLabel("ai_inferred", "confirmed")).toBe(
      "Student-confirmed AI inference"
    );
    expect(changeMapProvenanceLabel("ai_inferred", "rejected")).toContain("Rejected");
    expect(changeMapProvenanceLabel("ai_inferred", "needs_inspection")).toBe("Needs inspection");
    expect(reviewDecisionPresentation("needs_verification").label).toBe("Needs testing");
    expect(reviewDecisionPresentation("keep").description).toContain("student chose");
  });

  it("preserves every Verification result without calling pass verified", () => {
    expect(verificationResultPresentation("pass").label).toBe("Passed");
    expect(verificationResultPresentation("pass").label).not.toBe("Verified");
    expect(verificationResultPresentation("fail").label).toBe("Failed");
    expect(verificationResultPresentation("skipped").label).toBe("Skipped");
    expect(verificationResultPresentation("not_applicable").label).toBe("Not applicable");
    expect(verificationResultPresentation("unrecorded").label).toBe("Not recorded");
  });

  it("keeps actual Evidence, unavailable, and not addressed separate", () => {
    expect(evidenceStatusPresentation("evidence_recorded").label).toBe(
      "Student-provided Evidence"
    );
    expect(evidenceStatusPresentation("evidence_unavailable").label).toBe(
      "Evidence unavailable"
    );
    expect(evidenceStatusPresentation("not_addressed").label).toBe(
      "Evidence not addressed"
    );
  });

  it("allows only validated URL Evidence kinds to become links", () => {
    expect(safeEvidenceHref({ kind: "app_url", content: "https://example.test/a" })).toBe(
      "https://example.test/a"
    );
    expect(safeEvidenceHref({ kind: "note", content: "https://example.test/a" })).toBeNull();
    expect(safeEvidenceHref({ kind: "app_url", content: "javascript:example()" })).toBeNull();
  });

  it("treats only completed PASS or FAIL attempts as report-ready", () => {
    expect(reportIsReady(reportFixture())).toBe(true);
    expect(reportIsReady(reportFixture({ defense: { state: "passed", evaluator_outcome: "PASS", evaluator_reason: null, turns: [] } }))).toBe(true);
    expect(reportIsReady(reportFixture({ defense: { state: "in_progress", evaluator_outcome: null, evaluator_reason: null, turns: [] } }))).toBe(false);
    expect(reportIsReady(reportFixture({ defense: { state: "not_started", evaluator_outcome: null, evaluator_reason: null, turns: [] } }))).toBe(false);
  });

  it("uses exact student-safe outcome language without scores or certainty estimates", () => {
    expect(defenseOutcomeLabel("passed")).toBe("Defense passed");
    expect(defenseOutcomeLabel("failed")).toBe("Defense needs another attempt");
    const markdown = buildReportMarkdown(reportFixture());
    expect(markdown).toContain("FAIL");
    expect(markdown).not.toMatch(/score|threshold|confidence\s*:/i);
  });
});

describe("authoritative Report Markdown export", () => {
  it("includes provenance, mixed results, Evidence distinctions, transcript, and truth notice", () => {
    const markdown = buildReportMarkdown(reportFixture());
    expect(markdown).toContain("Project record captured for this Defense");
    expect(markdown).toContain("Student-confirmed AI inference");
    expect(markdown).toContain("Rejected AI-inferred change");
    expect(markdown).toContain("Needs testing");
    expect(markdown).toContain("Passed");
    expect(markdown).toContain("Failed");
    expect(markdown).toContain("Skipped");
    expect(markdown).toContain("Not applicable");
    expect(markdown).toContain("Not recorded");
    expect(markdown).toContain("Student-provided Evidence");
    expect(markdown).toContain("Evidence unavailable");
    expect(markdown).toContain("Your response");
    expect(markdown).toContain("not independent proof");
  });

  it("escapes HTML-like and Markdown-like student text in the export", () => {
    const markdown = buildReportMarkdown(reportFixture());
    expect(markdown).not.toContain("<img");
    expect(markdown).not.toContain("<script>");
    expect(markdown).not.toContain("<iframe");
    expect(markdown).not.toContain("<embed");
    expect(markdown).toContain("&lt;img");
    expect(markdown).toContain("\\*\\*not rendered\\*\\*");
  });
});
