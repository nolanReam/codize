import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import LinkedVerificationTargetRow, {
  SuggestedVerificationCheck,
  VerificationSourceSnapshot,
} from "./LinkedVerificationTarget";
import type { LinkedVerificationTarget } from "../lib/types";

function target(sourceText = "The route filters tasks by owner."): LinkedVerificationTarget {
  return {
    verification_target_id: "vt-0123456789ab",
    review_target_id: "rv-0123456789ab",
    change_map_item_id: "cm-0123456789ab",
    category: "behavior_change",
    source_text: sourceText,
    source_rationale: "I need to test the owner boundary.",
    suggested_check: "Sign in as two users and compare the visible tasks.",
    student_check: null,
    result: null,
    result_notes: null,
  };
}

describe("linked Verification rendering safety and semantics", () => {
  it("renders Review source and suggestions only as escaped plain text", () => {
    const source = '<img src=x onerror="example()">';
    const html = renderToStaticMarkup(
      <>
        <VerificationSourceSnapshot target={target(source)} />
        <SuggestedVerificationCheck target={{ ...target(), suggested_check: source }} />
      </>
    );
    expect(html.match(/&lt;img src=x onerror=&quot;example\(\)&quot;&gt;/g)).toHaveLength(2);
    expect(html).not.toContain('<img src="x"');
    expect(html).not.toContain("dangerouslySetInnerHTML");
  });

  it("does not render internal ids, raw imports, source bindings, or provider material", () => {
    const html = renderToStaticMarkup(<VerificationSourceSnapshot target={target()} />);
    expect(html).not.toContain("vt-0123456789ab");
    expect(html).not.toContain("rv-0123456789ab");
    expect(html).not.toContain("cm-0123456789ab");
    expect(html).not.toMatch(/raw import|source_review_binding|provider prompt|initialized_at/i);
  });

  it("uses native result radios, a fieldset, a legend, and exact labels", () => {
    const html = renderToStaticMarkup(
      <LinkedVerificationTargetRow
        target={target()}
        index={0}
        form={{ studentCheck: "", result: null, resultNotes: "" }}
        disabled={false}
        onChange={vi.fn()}
      />
    );
    expect(html).toContain("<fieldset");
    expect(html).toContain("<legend>Your result</legend>");
    expect(html.match(/type="radio"/g)).toHaveLength(5);
    for (const label of [
      "Not recorded yet",
      "Passed",
      "Failed",
      "Skipped",
      "Not applicable",
    ]) {
      expect(html).toContain(label);
    }
  });

  it("does not silently clip the student check with maxLength", () => {
    const html = renderToStaticMarkup(
      <LinkedVerificationTargetRow
        target={target()}
        index={0}
        form={{ studentCheck: "Edit this check", result: "fail", resultNotes: "Mismatch" }}
        disabled={false}
        onChange={vi.fn()}
      />
    );
    expect(html).not.toContain("maxlength=");
    expect(html).toContain("What happened?");
    expect(html).toContain("Mismatch");
  });
});
