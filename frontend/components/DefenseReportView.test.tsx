import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import DefenseReportView from "./DefenseReportView";
import type { DefenseReport } from "@/lib/types";

function report(): DefenseReport {
  return {
    schema_version: "1.0",
    phase_number: 1,
    phase_title: "Foundation <img src=x>",
    workflow_context_source: "defense_attempt",
    workflow_context: {
      schema_version: "1.0",
      phase_number: 1,
      state: "stale",
      content_truncated: true,
      content_redacted: false,
      change_map: {
        state: "current",
        truncated: false,
        items: [
          {
            category: "implementation_decision",
            origin: "ai_inferred",
            student_decision: "rejected",
            text: "Rejected <script>example()</script>",
            provenance: "AI-inferred Change Map item rejected by the student",
            ai_uncertainty: "ambiguous",
            uncertainty_reason: "Needs inspection",
            student_note: null,
          },
        ],
      },
      review: {
        state: "manual",
        truncated: false,
        items: [],
        manual: {
          files_changed: ["src/very/long/path.ts"],
          ai_generated: "A route <b>bold</b>",
          accepted: null,
          rejected: null,
          edited_manually: null,
          ai_assumptions: null,
          least_confident: null,
          out_of_scope_changes: null,
        },
      },
      verification: {
        state: "incomplete",
        truncated: false,
        student_explanation: null,
        checks: [
          {
            check: "Wrong-user request <iframe src=x>",
            result: "fail",
            result_notes: "Returned 200.",
            category: "security_sensitive_area",
            provenance: "student_recorded",
          },
          {
            check: "Browser flow",
            result: "unrecorded",
            result_notes: null,
            category: null,
            provenance: "student_unrecorded",
          },
        ],
      },
      evidence: {
        state: "stale",
        truncated: true,
        manual_entries: [{ kind: "note", content: "Manual note" }],
        manual_summary: "Earlier manual summary.",
        records: [
          {
            category: "security_sensitive_area",
            check_context: "Wrong-user request",
            verification_result: "fail",
            verification_notes: "Returned 200.",
            evidence_status: "evidence_unavailable",
            entries: [],
            student_explanation: null,
            unavailable_reason: null,
            stale_support_omitted: true,
          },
          {
            category: "behavior_change",
            check_context: "App route",
            verification_result: "pass",
            verification_notes: "Returned 201.",
            evidence_status: "evidence_recorded",
            entries: [
              { kind: "app_url", content: "https://example.test/evidence" },
              { kind: "note", content: "https://example.test/not-auto-linked" },
            ],
            student_explanation: "Supports this one observed result.",
            unavailable_reason: null,
            stale_support_omitted: false,
          },
          {
            category: "implementation_decision",
            check_context: "No Evidence was added for this check.",
            verification_result: "pass",
            verification_notes: null,
            evidence_status: "not_addressed",
            entries: [],
            student_explanation: null,
            unavailable_reason: null,
            stale_support_omitted: false,
          },
        ],
      },
    },
    defense: {
      state: "failed",
      evaluator_outcome: "FAIL",
      evaluator_reason: "The failure mode was not explained.",
      turns: [
        {
          turn: 1,
          question: "Why user_id? <embed src=x>",
          answer: "It scopes rows. **plain text**",
        },
      ],
    },
    truth_notice: "Student-recorded, not proof. <object>plain</object>",
  };
}

describe("DefenseReportView", () => {
  it("renders trust layers, failure states, manual compatibility, and transcript", () => {
    const html = renderToStaticMarkup(<DefenseReportView report={report()} />);
    for (const text of [
      "Project record captured for this Defense",
      "How to read this report",
      "Rejected AI-inferred change",
      "Manual record",
      "Failed",
      "Not recorded",
      "Evidence needs updating",
      "Evidence not addressed",
      "Earlier manual Evidence record",
      "Question 1",
      "Your response",
      "Defense needs another attempt",
    ]) {
      expect(html).toContain(text);
    }
    expect(html).not.toMatch(/score|threshold|expected concept|fingerprint|binding/i);
  });

  it("escapes all project text and creates only validated Evidence links", () => {
    const html = renderToStaticMarkup(<DefenseReportView report={report()} />);
    expect(html).toContain("&lt;img src=x&gt;");
    expect(html).toContain("&lt;script&gt;example()&lt;/script&gt;");
    expect(html).toContain("&lt;iframe src=x&gt;");
    expect(html).toContain("&lt;embed src=x&gt;");
    expect(html).toContain("&lt;object&gt;plain&lt;/object&gt;");
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<iframe");
    expect(html).not.toContain("<embed");
    expect(html).not.toContain("<object>");
    expect(html).not.toContain("<img");
    expect(html).toContain('href="https://example.test/evidence"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).not.toContain('href="https://example.test/not-auto-linked"');
    expect(html).not.toContain("dangerouslySetInnerHTML");
  });

  it("labels legacy current workflow explicitly and never calls it a snapshot", () => {
    const legacy = report();
    legacy.workflow_context_source = "current_workflow";
    const html = renderToStaticMarkup(<DefenseReportView report={legacy} />);
    expect(html).toContain("Current project record used for this legacy attempt");
    expect(html).toContain("may differ from what existed when the Defense occurred");
    expect(html).not.toContain("Defense snapshot");
  });
});
