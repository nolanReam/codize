import React from "react";

import { sourceFieldLabel } from "../lib/changeMap";
import type { ChangeMapItem } from "../lib/types";

// Small pure fragments keep source/error rendering testable with React's real
// renderer in the existing node-only Vitest setup.
export function SourceReferences({ item }: { item: ChangeMapItem }) {
  return (
    <details className="help source-disclosure">
      <summary>Why did Codize suggest this?</summary>
      <div className="help-body">
        {item.source_references.map((reference, index) => (
          <div className="source-reference" key={`${reference.source_field}-${index}`}>
            <strong>{sourceFieldLabel(reference.source_field)}</strong>
            {reference.file_path && (
              <p>
                File: <code>{reference.file_path}</code>
              </p>
            )}
            {reference.supporting_excerpt && (
              <pre className="source-excerpt" aria-label="Supporting source excerpt">
                {reference.supporting_excerpt}
              </pre>
            )}
          </div>
        ))}
        <p className="source-honesty">
          This source supported the draft. It does not prove the draft is correct.
        </p>
      </div>
    </details>
  );
}

export function ChangeMapErrorNotice({ message }: { message: string }) {
  return (
    <div className="notice error" role="alert">
      {message}
    </div>
  );
}
