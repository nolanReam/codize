import { describe, expect, it } from "vitest";

import { draftKey, writeDraft } from "./drafts";
import {
  buildImportPayload,
  CHANGED_FILE_ENTRY_MAX,
  CHANGED_FILES_MAX,
  CONTENT_MAX,
  EMPTY_FORM,
  formFromStored,
  GIT_DIFF_EXPLANATION,
  hasMeaningfulMaterial,
  type ImportForm,
  PAGE_INTRO,
  PAGE_REASSURANCE,
  PAGE_TITLE,
  parseChangedFiles,
  saveBlocker,
  SOURCE_OPTIONS,
  sourceOption,
} from "./implementationImport";
import type { ImplementationImportArtifact } from "./types";

const form = (overrides: Partial<ImportForm>): ImportForm => ({ ...EMPTY_FORM, ...overrides });

const GIT_DIFF = [
  "diff --git a/app/routes/tasks.py b/app/routes/tasks.py",
  "@@ -4,3 +4,6 @@",
  " def get_task(task_id, user_id):",
  "-    return db.get(task_id)",
  "+    row = db.get(task_id)",
  "+    if row.user_id != user_id:",
  "+        raise PermissionError",
].join("\n");

describe("source-kind mapping", () => {
  it.each([
    ["AI response", "ai_response"],
    ["Git diff", "git_diff"],
    ["Selected code", "code_snippet"],
    ["Changed files", "changed_files"],
    ["My own summary", "manual_summary"],
    ["Something else", "other"],
  ] as const)("maps the “%s” choice to backend value %s", (label, value) => {
    const option = SOURCE_OPTIONS.find((o) => o.label === label);
    expect(option?.value).toBe(value);
  });

  it("covers exactly the six backend kinds, once each", () => {
    expect(SOURCE_OPTIONS).toHaveLength(6);
    expect(new Set(SOURCE_OPTIONS.map((o) => o.value)).size).toBe(6);
  });

  it("never shows the internal enum to the student", () => {
    for (const o of SOURCE_OPTIONS) {
      expect(o.label).not.toMatch(/implementation_import|_/);
      expect(o.description).not.toMatch(/implementation_import|source_kind/);
      if (o.contentLabel) expect(o.contentLabel).not.toMatch(/implementation_import|_/);
    }
  });

  it("falls back safely for an unknown stored kind", () => {
    expect(sourceOption("ai_response").label).toBe("AI response");
    expect(sourceOption("nonsense" as never).value).toBe("ai_response");
  });
});

describe("changed-files parsing", () => {
  it("splits one entry per line, trims, drops empties, preserves order", () => {
    const text = "  app/routes/tasks.py  \n\napp/models/task.py\n   \nfrontend/components/TaskCard.tsx\n";
    expect(parseChangedFiles(text)).toEqual([
      "app/routes/tasks.py",
      "app/models/task.py",
      "frontend/components/TaskCard.tsx",
    ]);
  });

  it("does not deduplicate — the backend stays authoritative", () => {
    expect(parseChangedFiles("a.py\na.py")).toEqual(["a.py", "a.py"]);
  });

  it("handles Windows line endings", () => {
    expect(parseChangedFiles("a.py\r\nb.py")).toEqual(["a.py", "b.py"]);
  });
});

describe("payload shaping", () => {
  it("builds a content-only payload", () => {
    const p = buildImportPayload(form({ sourceKind: "ai_response", content: "The AI rewrote the route." }));
    expect(p).toEqual({
      source_kind: "ai_response",
      content: "The AI rewrote the route.",
      changed_files: [],
      student_summary: null,
      tool_name: null,
    });
  });

  it("builds a changed-files-only payload", () => {
    const p = buildImportPayload(form({ sourceKind: "changed_files", changedFilesText: "a.py\nb.py" }));
    expect(p.source_kind).toBe("changed_files");
    expect(p.content).toBeNull();
    expect(p.changed_files).toEqual(["a.py", "b.py"]);
  });

  it("builds a summary-only payload", () => {
    const p = buildImportPayload(
      form({ sourceKind: "manual_summary", summary: "The login flow works differently, but I have not reviewed all of it yet." })
    );
    expect(p.student_summary).toContain("login flow");
    expect(p.content).toBeNull();
    expect(p.changed_files).toEqual([]);
  });

  it("builds a mixed payload with the optional tool name", () => {
    const p = buildImportPayload(
      form({
        sourceKind: "git_diff",
        content: GIT_DIFF,
        changedFilesText: "app/routes/tasks.py",
        summary: "AI added task ownership checks.",
        toolName: "  Claude  ",
      })
    );
    expect(p.source_kind).toBe("git_diff");
    expect(p.content).toBe(GIT_DIFF);
    expect(p.changed_files).toEqual(["app/routes/tasks.py"]);
    expect(p.student_summary).toBe("AI added task ownership checks.");
    expect(p.tool_name).toBe("Claude");
  });

  it("preserves formatting byte-for-byte: indentation, diff markers, blank lines, Markdown", () => {
    const material = "```python\n    def indented():\n        pass\n```\n\n+    added line\n-    removed line";
    const p = buildImportPayload(form({ content: material }));
    expect(p.content).toBe(material);
  });

  it("never silently truncates — an over-limit paste passes through unchanged", () => {
    const huge = "x".repeat(CONTENT_MAX + 500);
    expect(buildImportPayload(form({ content: huge })).content).toHaveLength(CONTENT_MAX + 500);
  });

  it("sends null, not empty strings, for blank optionals", () => {
    const p = buildImportPayload(form({ content: "material", summary: "   ", toolName: "" }));
    expect(p.student_summary).toBeNull();
    expect(p.tool_name).toBeNull();
  });
});

describe("meaningful-content rule", () => {
  it("is false when every meaningful field is empty or whitespace", () => {
    expect(hasMeaningfulMaterial(EMPTY_FORM)).toBe(false);
    expect(hasMeaningfulMaterial(form({ content: "  \n  ", changedFilesText: " \n ", summary: "\t" }))).toBe(false);
  });

  it("any one of content / files / summary is enough", () => {
    expect(hasMeaningfulMaterial(form({ content: "code" }))).toBe(true);
    expect(hasMeaningfulMaterial(form({ changedFilesText: "a.py" }))).toBe(true);
    expect(hasMeaningfulMaterial(form({ summary: "it changed" }))).toBe(true);
  });

  it("optional fields never become required — a tool name alone is not material", () => {
    expect(hasMeaningfulMaterial(form({ toolName: "Claude" }))).toBe(false);
  });
});

describe("saveBlocker", () => {
  it("blocks an empty form with a plain-language explanation", () => {
    expect(saveBlocker(EMPTY_FORM)).toMatch(/add at least one thing/i);
  });

  it("allows each single-field save", () => {
    expect(saveBlocker(form({ content: GIT_DIFF }))).toBeNull();
    expect(saveBlocker(form({ changedFilesText: "a.py" }))).toBeNull();
    expect(saveBlocker(form({ summary: "notes" }))).toBeNull();
  });

  it("names the over-limit field without echoing the content", () => {
    const blocked = saveBlocker(form({ content: "SECRETMARKERTEXT".repeat(3000) }));
    expect(blocked).toMatch(/character-limit|limit/i);
    expect(blocked).not.toContain("SECRETMARKERTEXT");
  });

  it("blocks too many file entries and over-long entries, naming the field", () => {
    const many = Array.from({ length: CHANGED_FILES_MAX + 1 }, (_, i) => `f${i}.py`).join("\n");
    expect(saveBlocker(form({ changedFilesText: many }))).toMatch(/file entries/i);
    const long = "x".repeat(CHANGED_FILE_ENTRY_MAX + 1);
    expect(saveBlocker(form({ changedFilesText: long }))).toMatch(/file list/i);
    expect(saveBlocker(form({ changedFilesText: long }))).not.toContain(long);
  });
});

describe("existing saved import → form", () => {
  const stored: ImplementationImportArtifact = {
    source_kind: "git_diff",
    content: GIT_DIFF,
    changed_files: ["app/routes/tasks.py", "app/models/task.py"],
    student_summary: "AI added ownership checks.",
    tool_name: "Cursor",
    saved_at: "2026-07-13T10:00:00Z",
  };

  it("restores every field, multiline content intact", () => {
    const f = formFromStored(stored);
    expect(f.sourceKind).toBe("git_diff");
    expect(f.content).toBe(GIT_DIFF);
    expect(f.changedFilesText).toBe("app/routes/tasks.py\napp/models/task.py");
    expect(f.summary).toBe("AI added ownership checks.");
    expect(f.toolName).toBe("Cursor");
  });

  it("round-trips: editing nothing produces the same replacement payload", () => {
    const p = buildImportPayload(formFromStored(stored));
    expect(p).toEqual({
      source_kind: "git_diff",
      content: GIT_DIFF,
      changed_files: ["app/routes/tasks.py", "app/models/task.py"],
      student_summary: "AI added ownership checks.",
      tool_name: "Cursor",
    });
  });

  it("treats missing optionals as empty fields", () => {
    const f = formFromStored({ source_kind: "manual_summary", changed_files: [], student_summary: "s" });
    expect(f.content).toBe("");
    expect(f.changedFilesText).toBe("");
    expect(f.toolName).toBe("");
  });
});

describe("local draft safety (existing drafts utilities)", () => {
  function fakeStorage() {
    const map = new Map<string, string>();
    return {
      getItem: (k: string) => map.get(k) ?? null,
      setItem: (k: string, v: string) => void map.set(k, v),
      removeItem: (k: string) => void map.delete(k),
      map,
    };
  }

  it("scopes the draft by user and phase", () => {
    expect(draftKey("user-a", "implementation_import:2")).toBe(
      "codize:draft:user-a:implementation_import:2"
    );
    expect(draftKey("user-a", "implementation_import:2")).not.toBe(
      draftKey("user-a", "implementation_import:3")
    );
    expect(draftKey("user-a", "implementation_import:2")).not.toBe(
      draftKey("user-b", "implementation_import:2")
    );
  });

  it("refuses to persist an import draft carrying secret-marker content", () => {
    const s = fakeStorage();
    const withSecret = form({ content: "set SUPABASE_KEY=sb_secret_fakefake123 in .env" });
    expect(writeDraft(s, "k", withSecret)).toBe(false);
    expect(s.map.size).toBe(0);
  });

  it("persists an ordinary import draft round-trip", () => {
    const s = fakeStorage();
    const draft = form({ sourceKind: "code_snippet", content: "    indented = True" });
    expect(writeDraft(s, "k", draft)).toBe(true);
    expect(JSON.parse(s.map.get("k")!)).toEqual(draft);
  });
});

describe("page copy honors the product rules", () => {
  it("uses the beginner-friendly title, not the internal name", () => {
    expect(PAGE_TITLE).toBe("Bring Back What Changed");
    expect(PAGE_TITLE).not.toMatch(/implementation import/i);
  });

  it("reassures that not every item is needed", () => {
    expect(PAGE_REASSURANCE).toMatch(/do not need every item/i);
  });

  it("frames the intro around keeping track, not failure or verification claims", () => {
    expect(PAGE_INTRO).toMatch(/keep track of what changed/i);
    expect(PAGE_INTRO).not.toMatch(/broken|failed|verified|proof/i);
  });

  it("explains a git diff in a few sentences and offers a way out", () => {
    expect(GIT_DIFF_EXPLANATION).toMatch(/added, removed, or changed/i);
    expect(GIT_DIFF_EXPLANATION).toMatch(/skip this option/i);
    expect(GIT_DIFF_EXPLANATION.split(". ").length).toBeLessThanOrEqual(4);
  });
});
