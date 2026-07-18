// "Bring Back What Changed" (M15B) — pure helpers for the implementation
// import page. Everything here is deterministic and unit-tested: source-kind
// labels, form ↔ backend payload shaping, and the save-blocking rules. The
// page stays a thin consumer.
//
// Two rules are load-bearing:
// - Formatting IS the material: content and summary are sent verbatim (the
//   backend normalizes edges only) — never trimmed, rewritten, or truncated
//   here. Over-limit input blocks the save with a message naming the field.
// - Imported material is self-reported, never verified — no copy in this
//   module may claim Codize checked or trusts it.

import type {
  ImplementationImportArtifact,
  ImplementationImportSourceKind,
} from "./types";

// Backend caps (schemas/workflow.py IMPORT_*_MAX) — mirrored, not enforced by
// clipping: the UI blocks the save and says which field is over.
export const CONTENT_MAX = 40_000;
export const SUMMARY_MAX = 4_000;
export const TOOL_NAME_MAX = 100;
export const CHANGED_FILES_MAX = 100;
export const CHANGED_FILE_ENTRY_MAX = 300;

// The page's load-bearing copy, exported so tests can hold it to the product
// rules (beginner-friendly title, "you do not need every item" reassurance,
// no internal enum names anywhere a student can read).
export const PAGE_TITLE = "Bring Back What Changed";
export const PAGE_INTRO =
  "After you use AI, bring back whatever you have so you can keep track of what changed before moving on.";
export const PAGE_REASSURANCE = "You do not need every item — add the material you have.";
export const GIT_DIFF_EXPLANATION =
  "A git diff shows which lines were added, removed, or changed. Many coding tools can display or copy one. You can skip this option and paste the AI response, changed code, or your own description instead.";
export const SECRET_REMINDER =
  "Remove API keys, access tokens, passwords, and private keys before saving.";

export interface ImportSourceOption {
  value: ImplementationImportSourceKind;
  label: string;
  description: string;
  // Label for the main pasted-material textarea. null = this kind's main
  // field is not the textarea (changed files / own summary get emphasized
  // instead), and the textarea moves to the optional card with a generic label.
  contentLabel: string | null;
}

export const SOURCE_OPTIONS: ImportSourceOption[] = [
  {
    value: "ai_response",
    label: "AI response",
    description: "Paste what ChatGPT, Claude, Cursor, Gemini, Copilot, or another AI tool returned.",
    contentLabel: "Paste the AI response",
  },
  {
    value: "git_diff",
    label: "Git diff",
    description: "Paste the added, removed, or changed lines from Git.",
    contentLabel: "Paste the diff",
  },
  {
    value: "code_snippet",
    label: "Selected code",
    description: "Paste the part of the implementation that changed.",
    contentLabel: "Paste the changed code",
  },
  {
    value: "changed_files",
    label: "Changed files",
    description: "List the files AI created or modified.",
    contentLabel: null,
  },
  {
    value: "manual_summary",
    label: "My own summary",
    description: "Describe what changed in your own words.",
    contentLabel: null,
  },
  {
    value: "other",
    label: "Something else",
    description: "Add another kind of implementation note or output.",
    contentLabel: "Paste the implementation material",
  },
];

export function sourceOption(kind: ImplementationImportSourceKind): ImportSourceOption {
  return SOURCE_OPTIONS.find((o) => o.value === kind) ?? SOURCE_OPTIONS[0];
}

// The page's whole form state — also the local-draft shape.
export interface ImportForm {
  sourceKind: ImplementationImportSourceKind;
  content: string;
  changedFilesText: string;
  summary: string;
  toolName: string;
}

export const EMPTY_FORM: ImportForm = {
  sourceKind: "ai_response",
  content: "",
  changedFilesText: "",
  summary: "",
  toolName: "",
};

// One file per line: trim each line, drop empties, preserve order. The
// backend's deduplication stays authoritative — none happens here.
export function parseChangedFiles(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

// The backend rule the UI reflects: at least one of imported content /
// changed files / summary must carry something. Optional fields never block.
export function hasMeaningfulMaterial(form: ImportForm): boolean {
  return (
    form.content.trim().length > 0 ||
    parseChangedFiles(form.changedFilesText).length > 0 ||
    form.summary.trim().length > 0
  );
}

// Why Save is disabled right now, or null. Names the field, never echoes or
// clips the content — the backend remains the authoritative validator.
export function saveBlocker(form: ImportForm): string | null {
  if (!hasMeaningfulMaterial(form)) {
    return "Add at least one thing first: the material itself, a file list, or a short summary.";
  }
  if (form.content.length > CONTENT_MAX) {
    return `The pasted material is over the ${CONTENT_MAX.toLocaleString()}-character limit — bring back the most relevant part.`;
  }
  if (form.summary.length > SUMMARY_MAX) {
    return `The summary is over the ${SUMMARY_MAX.toLocaleString()}-character limit — a few sentences is plenty.`;
  }
  if (form.toolName.length > TOOL_NAME_MAX) {
    return `The tool name is over ${TOOL_NAME_MAX} characters — a short name like “Claude” or “Cursor” works.`;
  }
  const files = parseChangedFiles(form.changedFilesText);
  if (files.length > CHANGED_FILES_MAX) {
    return `That's ${files.length} file entries — the list is capped at ${CHANGED_FILES_MAX}. Keep the most relevant ones.`;
  }
  if (files.some((f) => f.length > CHANGED_FILE_ENTRY_MAX)) {
    return `One line in the file list is over ${CHANGED_FILE_ENTRY_MAX} characters — file paths are short, so check for pasted content in the wrong box.`;
  }
  return null;
}

// The exact PUT body. Content and summary go verbatim when non-blank (the
// backend trims edges and preserves everything inside); blank optionals → null.
export function buildImportPayload(
  form: ImportForm
): Omit<ImplementationImportArtifact, "saved_at"> {
  return {
    source_kind: form.sourceKind,
    content: form.content.trim() ? form.content : null,
    changed_files: parseChangedFiles(form.changedFilesText),
    student_summary: form.summary.trim() ? form.summary : null,
    tool_name: form.toolName.trim() ? form.toolName.trim() : null,
  };
}

// Prefill the form from a stored artifact (existing-import editing).
export function formFromStored(stored: ImplementationImportArtifact): ImportForm {
  return {
    sourceKind: stored.source_kind,
    content: stored.content ?? "",
    changedFilesText: (stored.changed_files ?? []).join("\n"),
    summary: stored.student_summary ?? "",
    toolName: stored.tool_name ?? "",
  };
}
