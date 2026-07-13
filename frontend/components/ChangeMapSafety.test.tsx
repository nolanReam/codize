import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { ChangeMapItem } from "../lib/types";
import { ChangeMapErrorNotice, SourceReferences } from "./ChangeMapSafety";

const item: ChangeMapItem = {
  item_id: "cm-source",
  origin: "ai_inferred",
  category: "behavior_change",
  draft_text: "The route appears to have changed.",
  ai_uncertainty: "supported",
  uncertainty_reason: null,
  source_references: [
    {
      source_field: "content",
      source_kind: "code_snippet",
      file_path: "<img src=x onerror=alert(1)>",
      supporting_excerpt: "<script>window.stolen = true</script>",
    },
  ],
  student_decision: "pending_review",
  student_text: null,
  student_note: null,
};

describe("Change Map safe rendering", () => {
  it("renders source references as escaped plain text inside a collapsed disclosure", () => {
    const html = renderToStaticMarkup(<SourceReferences item={item} />);
    expect(html).toContain("<details");
    expect(html).not.toContain("<details open");
    expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;");
    expect(html).toContain("&lt;script&gt;window.stolen = true&lt;/script&gt;");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<script>");
  });

  it("announces a server or network error without interpreting markup", () => {
    const html = renderToStaticMarkup(
      <ChangeMapErrorNotice message={'Could not regenerate. <img src=x onerror="steal()">'} />
    );
    expect(html).toContain('role="alert"');
    expect(html).toContain("&lt;img src=x onerror=&quot;steal()&quot;&gt;");
    expect(html).not.toContain("<img");
  });
});
