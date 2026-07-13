import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import LinkedReviewTargetRow, { ReviewSourceSnapshot } from "./LinkedReviewTarget";
import type { LinkedReviewTarget } from "../lib/types";

function target(changeText = "The route now filters reads by owner."): LinkedReviewTarget {
  return {
    review_target_id: "rv-0123456789ab",
    change_map_item_id: "cm-0123456789ab",
    change_map_category: "behavior_change",
    change_map_origin: "ai_inferred",
    change_map_student_decision: "confirmed",
    change_text: changeText,
    source_resolution: "confirmed",
    review_decision: "pending",
    student_rationale: null,
    student_revision: null,
  };
}

describe("linked Review rendering safety and semantics", () => {
  it("renders HTML-like source content only as escaped plain text", () => {
    const source = '<img src=x onerror="example()">';
    const html = renderToStaticMarkup(<ReviewSourceSnapshot target={target(source)} />);
    expect(html).toContain("&lt;img src=x onerror=&quot;example()&quot;&gt;");
    expect(html).not.toContain('<img src="x"');
    expect(html).not.toContain("dangerouslySetInnerHTML");
  });

  it("does not render server ids or nonexistent raw provenance", () => {
    const html = renderToStaticMarkup(<ReviewSourceSnapshot target={target()} />);
    expect(html).not.toContain("rv-0123456789ab");
    expect(html).not.toContain("cm-0123456789ab");
    expect(html).not.toMatch(/source_references|supporting_excerpt|raw import|provider prompt/i);
  });

  it("uses a fieldset, legend, and real single-choice radio controls", () => {
    const html = renderToStaticMarkup(
      <LinkedReviewTargetRow
        target={target()}
        index={0}
        form={{ reviewDecision: "pending", studentRationale: "", studentRevision: "" }}
        disabled={false}
        onChange={vi.fn()}
      />
    );
    expect(html).toContain("<fieldset");
    expect(html).toContain("<legend>Your decision</legend>");
    expect(html.match(/type="radio"/g)).toHaveLength(6);
    expect(html).toContain("Needs testing");
    expect(html).toContain("I’m not sure");
  });
});
